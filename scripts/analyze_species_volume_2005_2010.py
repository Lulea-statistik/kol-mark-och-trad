#!/usr/bin/env python3
"""Compare historical pine/spruce/birch/deciduous volumes 2005 vs 2010.

Real SLU kNN GeoTIFF sources are opened and municipal source-CRS clips made
before full raster reprojection to EPSG:3006. Same five-epoch common support
as website is the baseline; each species pair gets its own valid mask.
Do not assume species variables are additive or identify live forest growth.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from contextlib import ExitStack
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from rasterio.transform import Affine
from shapely.geometry import mapping,shape
from shapely.ops import transform as geom_transform
from pyproj import Transformer
from fetch_and_compare_biomass_native import crop_source,matches_expected_crs,EXPECTED
from analyze_historic_volume import validate_archive
from analyze_forest_age_2010 import check_age
from model_age_adjusted_biomass import validate_historical_age
from verify_biomass_release import run as verify_biomass

SPECIES={"pine":"PINEVOL","spruce":"SPRUCEVOL","birch":"BIRCHVOL",
         "deciduous":"DECIDUOUSVOL"}
AGE_BINS=(0,20,40,60,80,100,120,150,200,500,float("inf"))
DOMINANT_CLASSES=("pine","spruce","birch","other_deciduous","mixed","unclassified")
DOMINANT_THRESHOLD=0.60
MINIMUM_VOLUME_RAW=20.0
MAX_COMPONENT_CLOSURE_GAP=0.20

def new_stability_bucket(name):
 return {"name":name,"cells":0,"eligible_both_years":0,
         "transitions":np.zeros((6,6),dtype="int64"),
         "conifer_share_2005_sum":0.0,"conifer_share_2010_sum":0.0,
         "pine_share_2005_sum":0.0,"pine_share_2010_sum":0.0}

def cell_dominance(components,total):
 """Dominant estimated volume type, not observed tree coverage."""
 amounts=np.vstack(components).astype("float64")
 subtotal=amounts.sum(axis=0)
 legal=(total>=MINIMUM_VOLUME_RAW) & (subtotal>=MINIMUM_VOLUME_RAW)
 legal &= (np.abs(subtotal-total)<=MAX_COMPONENT_CLOSURE_GAP*np.maximum(total,1.0))
 safe=np.where(subtotal>0,subtotal,1.0)
 shares=amounts/safe
 winner=shares.argmax(axis=0)
 max_share=shares.max(axis=0)
 cls=np.where(max_share>=DOMINANT_THRESHOLD,winner,4).astype("uint8")
 cls[~legal]=5
 return cls,(amounts[0]+amounts[1])/safe,amounts[0]/safe

def record_stability(bucket,classes05,classes10,con05,con10,pine05,pine10,mask):
 bucket["cells"]+=int(mask.sum())
 if not np.any(mask):return
 c05=classes05[mask];c10=classes10[mask]
 count=np.bincount(c05.astype("int64")*6+c10.astype("int64"),minlength=36).reshape(6,6)
 bucket["transitions"]+=count
 eligible=(c05!=5)&(c10!=5)
 n=int(eligible.sum())
 bucket["eligible_both_years"]+=n
 if not n:return
 bucket["conifer_share_2005_sum"]+=float(con05[mask][eligible].sum())
 bucket["conifer_share_2010_sum"]+=float(con10[mask][eligible].sum())
 bucket["pine_share_2005_sum"]+=float(pine05[mask][eligible].sum())
 bucket["pine_share_2010_sum"]+=float(pine10[mask][eligible].sum())

def finish_stability(bucket):
 n=bucket["eligible_both_years"]
 matrix=bucket["transitions"]
 assert int(matrix.sum())==bucket["cells"]
 known=matrix[:5,:5]
 denominator=int(known.sum())
 assert denominator==n
 return {"population":bucket["name"],"cells":bucket["cells"],
  "area_ha":bucket["cells"]*.0625,
  "eligible_cells":n,"eligible_area_ha":n*.0625,
  "eligible_share":n/bucket["cells"] if bucket["cells"] else None,
  "species_labels":list(DOMINANT_CLASSES),
  "transition_counts":matrix.tolist(),
  "same_dominant_class_fraction":float(np.trace(known)/denominator) if denominator else None,
  "dominant_pine_stays_pine_fraction":float(known[0,0]/known[0].sum()) if known[0].sum()>0 else None,
  "dominant_spruce_stays_spruce_fraction":float(known[1,1]/known[1].sum()) if known[1].sum()>0 else None,
  "mean_conifer_volume_share_2005":bucket["conifer_share_2005_sum"]/n if n else None,
  "mean_conifer_volume_share_2010":bucket["conifer_share_2010_sum"]/n if n else None,
  "mean_pine_volume_share_2005":bucket["pine_share_2005_sum"]/n if n else None,
  "mean_pine_volume_share_2010":bucket["pine_share_2010_sum"]/n if n else None}

def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()

def run(a):
 validate_archive(a.volume_dir,a.boundary)
 validate_historical_age(a.age_history_dir,a.boundary)
 check_age(a.age_2010_dir,a.boundary)
 verify_biomass(argparse.Namespace(directory=a.biomass_dir,output=a.qa_output))
 doc=json.loads(a.boundary.read_text(encoding="utf-8"))
 if doc.get("type")!="FeatureCollection" or len(doc.get("features",[]))!=1:raise ValueError("Expected one EPSG:4326 project polygon")
 poly=shape(doc["features"][0]["geometry"])
 if poly.is_empty or not poly.is_valid:raise ValueError("Invalid polygon")
 a.workdir.mkdir(parents=True,exist_ok=True)
 EXPECTED["2005"]=(3021,25.)
 trace={"sources":{}}
 paths={}
 for species,filekey in SPECIES.items():
  for year in ("2005","2010"):
   url=f"https://gis.slu.se/data/slu_forest_map/{year}/Data/Raster/Rt90/{filekey}_XX_P_{year[-2:]}.tif"
   name=f"{species}_{year}"
   target=a.workdir/(name+"_lulea_source_crs_clip.tif")
   # Archive only municipal source-CRS windows and preserve remote metadata.
   # Fails rather than substituting guessed species if SLU changes names.
   tmp={"sources":{}}
   crop_source(url,year,poly,target,tmp)
   info=tmp["sources"][year]
   trace["sources"][name]={"url":url,"source_crs":"EPSG:3021",
       "native_m":info["source_resolution_m"],"source_nodata":info["source_nodata"],
       "valid_native_pixels":info["valid_inside_polygon_pixels"],
       "sha256_clip":sha(target),"clip_filename":target.name}
   paths[name]=(target,3021)
 for year in ("2000","2005","2010"):
  paths["volume_"+year]=(a.volume_dir/f"lulea_total_volume_{year}_source_crs_clip.tif",3021)
 for year,epsg in (("2010",3021),("2015",3006),("2018",3006)):
  paths["bio_"+year]=(a.biomass_dir/f"lulea_biomass_{year}_source_crs_clip.tif",epsg)
 paths["age_2005"]=(a.age_history_dir/"lulea_forest_age_2005_source_crs_clip.tif",3021)
 paths["age_2010"]=(a.age_2010_dir/"lulea_forest_age_2010_source_crs_clip.tif",3021)
 geo=geom_transform(Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,poly)
 size=25.;left,bottom,right,top=geo.bounds
 left=math.floor(left/size)*size;bottom=math.floor(bottom/size)*size
 right=math.ceil(right/size)*size;top=math.ceil(top/size)*size
 width=round((right-left)/size);height=round((top-bottom)/size)
 if width*height>40_000_000:raise ValueError("Unexpected municipal working extent")
 grid=Affine(size,0,left,0,-size,top)
 keys_main=["volume_2000","volume_2005","volume_2010",
            "bio_2010","bio_2015","bio_2018","age_2005","age_2010"]
 stats={species:{"paired_cells":0,"sum_2005":0.,"sum_2010":0.,
                 "sum_totalvol_2005":0.,"sum_totalvol_2010":0.,
                 "increased_cells":0,"age_2005_cohorts":[{"min_age":AGE_BINS[i],
                   "max_age":AGE_BINS[i+1] if math.isfinite(AGE_BINS[i+1]) else None,
                   "cells":0,"sum_2005":0.,"sum_2010":0.}
                  for i in range(len(AGE_BINS)-1)]} for species in SPECIES}
 main_n=0;all_species_n=0;all_species_sums={k:0. for k in ("total05","total10","pine05","pine10","spruce05","spruce10","birch05","birch10","decid05","decid10")}
 birch_le_decid=0
 stability={
  "all_2005_ages":new_stability_bucket("all_2005_ages"),
  "age_2005_0_20":new_stability_bucket("age_2005_0_20"),
  "age_2005_20_40":new_stability_bucket("age_2005_20_40"),
  "age_2005_40_60":new_stability_bucket("age_2005_40_60"),
  "age_2005_60_plus":new_stability_bucket("age_2005_60_plus"),
  "age_2005_20_plus":new_stability_bucket("age_2005_20_plus"),
  "age_2005_20_plus_no_large_age_reset":new_stability_bucket("age_2005_20_plus_no_large_age_reset"),
  "age_2005_20_plus_age_consistent":new_stability_bucket("age_2005_20_plus_age_consistent")}
 with ExitStack() as stack:
  vrt={}
  for name,(path,epsg) in paths.items():
   src=stack.enter_context(rasterio.open(path))
   if not matches_expected_crs(src.crs,epsg) or src.count!=1 or src.nodata!=-9999:
    raise ValueError("Unverified CRS or NoData for "+name)
   vrt[name]=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=grid,
      width=width,height=height,src_nodata=-9999,nodata=-9999,dtype="float32",
      resampling=Resampling.average))
  for rr in range(0,height,256):
   for cc in range(0,width,256):
    win=Window(cc,rr,min(256,width-cc),min(256,height-rr))
    local_tf=rasterio.windows.transform(win,grid)
    inside=geometry_mask([mapping(geo)],out_shape=(int(win.height),int(win.width)),
                          transform=local_tf,invert=True,all_touched=False)
    if not inside.any():continue
    arrays={name:np.ma.asarray(r.read(1,window=win,masked=True),dtype="float64").filled(np.nan)
            for name,r in vrt.items()}
    valid_main=inside.copy()
    for name in keys_main:valid_main &=np.isfinite(arrays[name]) & (arrays[name]>=0)
    main_n+=int(valid_main.sum())
    for species in SPECIES:
     k5=f"{species}_2005";k10=f"{species}_2010"
     ok=valid_main & np.isfinite(arrays[k5]) & np.isfinite(arrays[k10])
     ok &= (arrays[k5]>=0)&(arrays[k10]>=0)
     n=int(ok.sum())
     if not n:continue
     s=stats[species];s["paired_cells"]+=n
     v5=arrays[k5][ok];v10=arrays[k10][ok]
     s["sum_2005"]+=float(v5.sum());s["sum_2010"]+=float(v10.sum())
     s["sum_totalvol_2005"]+=float(arrays["volume_2005"][ok].sum())
     s["sum_totalvol_2010"]+=float(arrays["volume_2010"][ok].sum())
     s["increased_cells"]+=int((v10>v5).sum())
     age=arrays["age_2005"][ok]
     for row in s["age_2005_cohorts"]:
      up=row["max_age"] if row["max_age"] is not None else float("inf")
      take=(age>=row["min_age"]) & (age<up)
      m=int(take.sum())
      if m:
       row["cells"]+=m
       row["sum_2005"]+=float(v5[take].sum())
       row["sum_2010"]+=float(v10[take].sum())
    all_mask=valid_main.copy()
    for species in SPECIES:
     for year in ("2005","2010"):
      a0=arrays[f"{species}_{year}"]
      all_mask &=np.isfinite(a0) & (a0>=0)
    m=int(all_mask.sum());all_species_n+=m
    if m:
     for year in ("2005","2010"):
      all_species_sums[f"total{year[-2:]}"]+=float(arrays["volume_"+year][all_mask].sum())
      for species,label in (("pine","pine"),("spruce","spruce"),
          ("birch","birch"),("deciduous","decid")):
       all_species_sums[f"{label}{year[-2:]}"]+=float(arrays[f"{species}_{year}"][all_mask].sum())
     birch_le_decid+=int(np.count_nonzero(arrays["birch_2005"][all_mask]<=arrays["deciduous_2005"][all_mask]))
     # Single 25 m pixels and identical source support, not independently observed species.
     vals05=[arrays[f"{species}_2005"][all_mask] for species in SPECIES]
     vals10=[arrays[f"{species}_2010"][all_mask] for species in SPECIES]
     total05=arrays["volume_2005"][all_mask]
     total10=arrays["volume_2010"][all_mask]
     c05,con05,p05=cell_dominance(vals05,total05)
     c10,con10,p10=cell_dominance(vals10,total10)
     age05=arrays["age_2005"][all_mask]
     age10=arrays["age_2010"][all_mask]
     cases=[
      ("all_2005_ages",np.ones(m,dtype=bool)),
      ("age_2005_0_20",age05<20),
      ("age_2005_20_40",(age05>=20)&(age05<40)),
      ("age_2005_40_60",(age05>=40)&(age05<60)),
      ("age_2005_60_plus",age05>=60),
      ("age_2005_20_plus",age05>=20),
      ("age_2005_20_plus_no_large_age_reset",(age05>=20)&(age10>=age05-10)),
      ("age_2005_20_plus_age_consistent",(age05>=20)&(age10>=age05-2)&(age10<=age05+12))]
     for name,selected in cases:
      record_stability(stability[name],c05,c10,con05,con10,p05,p10,selected)
 if main_n!=2316804:raise ValueError(f"Expected 2316804 baseline cells, got {main_n}")
 summaries={}
 for species,s in stats.items():
  n=s["paired_cells"]
  if not n:raise ValueError("No valid paired pixels for "+species)
  cells=s["age_2005_cohorts"]
  for row in cells:
   m=row["cells"]
   row["mean_volume_2005"]=row.pop("sum_2005")/m if m else None
   row["mean_volume_2010"]=row.pop("sum_2010")/m if m else None
   row["area_ha"]=m*.0625
  summaries[species]={"paired_cells":n,"paired_ha":n*.0625,
   "share_of_baseline_cells":n/main_n,
   "mean_species_volume_2005":s["sum_2005"]/n,
   "mean_species_volume_2010":s["sum_2010"]/n,
   "raw_mean_difference":(s["sum_2010"]-s["sum_2005"])/n,
   "relative_change_percent":100*(s["sum_2010"]/s["sum_2005"]-1) if s["sum_2005"]>0 else None,
   "total_volume_raw_change_on_same_species_support":(s["sum_totalvol_2010"]-s["sum_totalvol_2005"])/n,
   "share_cells_species_volume_increased":s["increased_cells"]/n,
   "cohorts_by_age_2005":cells}
 result={"status":"VERIFIED_SOURCE_PAIRED_SPECIES_VOLUMES_NOT_A_BIOMASS_CHANGE",
  "generated_utc":datetime.now(timezone.utc).isoformat(),
  "raster_crs":"EPSG:3006","cell_size_m":25,
  "baseline_cells":main_n,"baseline_area_ha":main_n*.0625,
  "species_results":summaries,
  "all_species_overlap_cells":all_species_n,
  "all_species_overlap_area_ha":all_species_n*.0625,
  "mean_on_full_species_overlap":{k:(v/all_species_n if all_species_n else None)
       for k,v in all_species_sums.items()},
  "share_cells_birch_2005_le_deciduous_2005":birch_le_decid/all_species_n if all_species_n else None,
  "dominance_stability_method":{
   "criterion":"max of pine, spruce, birch, other_deciduous >= 60 pct of four-component volume sum",
   "minimum_total_and_four_species_sum_raw":MINIMUM_VOLUME_RAW,
   "maximum_abs_difference_four_species_sum_and_total_share":MAX_COMPONENT_CLOSURE_GAP,
   "basis":"2005 vs 2010 estimated volume composition on identical 25m cells, not observed stem proportions",
   "unknown_class_included_in_matrix":True,
   "age_consistency_tolerance":"2010 age estimate between 2005 age minus 2 and plus 12",
   "age_reset_exclusion":"2010 age must not be >10 years below 2005 estimate (not a verified harvest mask)"},
  "dominance_stability":{name:finish_stability(bucket) for name,bucket in stability.items()},
  "source_clips":trace["sources"],
  "cautions":[
   "All species raster products are kNN estimates, not independent forest inventory measurements",
   "Source filenames and values do not verify physical volume unit or whether DECIDUOUS includes BIRCH",
   "Do not sum birch and deciduous as physical volume without confirming component definition",
   "The four-component sum is used solely for relative species composition and rejected where its gap against total exceeds 20pct",
   "For older stands, the age-consistency filter is only a sensitivity test and NOT proof of no logging",
   "Volume-dominant class is a raster estimate, NOT fixed stand identity: logging, thinning, succession and source model differences can all shift it",
   "Stratum age is as estimated in 2005; annual age, harvest and species composition can change",
   "Individual species pair masks may have fewer cells than baseline 144800.25 hectares",
   "No source raster or public biomass timeseries was modified",
   "No inference about actual growth, emissions or carbon sequestration authorized"]}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("SOURCE_METADATA",json.dumps(trace,ensure_ascii=False),flush=True)
 print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--volume-dir",type=Path,default=Path("release-volume"))
 p.add_argument("--biomass-dir",type=Path,default=Path("release-biomass"))
 p.add_argument("--age-history-dir",type=Path,default=Path("release-age-history"))
 p.add_argument("--age-2010-dir",type=Path,default=Path("release-age-2010"))
 p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
 p.add_argument("--workdir",type=Path,default=Path("species-lulea-clips"))
 p.add_argument("--qa-output",type=Path,default=Path("metadata/species_biomass_archive_qa.json"))
 p.add_argument("--output",type=Path,default=Path("metadata/species_volume_2005_2010_diagnostics.json"))
 run(p.parse_args())
