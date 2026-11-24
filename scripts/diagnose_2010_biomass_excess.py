#!/usr/bin/env python3
"""Diagnose 2010 biomass elevation: spatial coverage, age and 2010 volume.

Descriptive paired comparisons, no historical age backcasting and no claim
that different biomass source generations represent identical components.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime,timezone
import numpy as np
import rasterio
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from shapely.geometry import shape,mapping
from shapely.ops import transform as geom_transform
from pyproj import Transformer
from analyze_historic_volume import validate_archive
from analyze_forest_age_2010 import check_age
from verify_biomass_release import run as verify_biomass
from fetch_and_compare_biomass_native import matches_expected_crs

BINS=[0,20,40,60,80,100,120,150,200,500,float("inf")]
YEARS=("2010","2015","2018")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--biomass-dir",type=Path,default=Path("release-biomass"))
 p.add_argument("--volume-dir",type=Path,default=Path("release-volume"))
 p.add_argument("--age-dir",type=Path,default=Path("release-age"))
 p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
 p.add_argument("--output",type=Path,default=Path("metadata/biomass_2010_excess_diagnostics.json"))
 a=p.parse_args()
 verify_biomass(argparse.Namespace(directory=a.biomass_dir,
            output=Path("metadata/diagnostic_biomass_archive_qa.json")))
 validate_archive(a.volume_dir,a.boundary)
 check_age(a.age_dir,a.boundary)
 doc=json.loads(a.boundary.read_text(encoding="utf-8"))
 if doc.get("type")!="FeatureCollection" or len(doc["features"])!=1:
  raise ValueError("Expected one EPSG:4326 polygon")
 poly=shape(doc["features"][0]["geometry"])
 if poly.is_empty or not poly.is_valid:raise ValueError("Invalid working polygon")
 geo=geom_transform(Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,poly)
 size=25.; xmin,ymin,xmax,ymax=geo.bounds
 xmin=math.floor(xmin/size)*size; xmax=math.ceil(xmax/size)*size
 ymin=math.floor(ymin/size)*size; ymax=math.ceil(ymax/size)*size
 w=round((xmax-xmin)/size);h=round((ymax-ymin)/size)
 if w*h>40_000_000:raise ValueError("Unexpected analysis extent")
 grid=Affine(size,0,xmin,0,-size,ymax)
 sources={
  "bio2010":(a.biomass_dir/"lulea_biomass_2010_source_crs_clip.tif",3021),
  "bio2015":(a.biomass_dir/"lulea_biomass_2015_source_crs_clip.tif",3006),
  "bio2018":(a.biomass_dir/"lulea_biomass_2018_source_crs_clip.tif",3006),
  "age2010":(a.age_dir/"lulea_forest_age_2010_source_crs_clip.tif",3021),
  "vol2010":(a.volume_dir/"lulea_total_volume_2010_source_crs_clip.tif",3021)}
 base={y:{"own_n":0,"own_sum":0.,"paired_n":0,"paired_sum":0.,"paired_positive_n":0,"paired_positive_sum":0.} for y in YEARS}
 # Age is from 2010 for ALL comparisons, never presented as age in 2015/2018.
 groups=[{"age_from":BINS[i],"age_to":BINS[i+1] if math.isfinite(BINS[i+1]) else None,
           "n":0,"sums":{y:0. for y in YEARS},
           "diff_2010_2015_sum":0.,"diff_2010_2018_sum":0.}
          for i in range(len(BINS)-1)]
 # also 2010 volume-based strata, fixed for all years.
 bands=[
  {"label":"2010 volume = 0", "lo":0,"hi":0,"n":0,"sums":{y:0. for y in YEARS}},
  {"label":"2010 volume (0,50)", "lo":0,"hi":50,"n":0,"sums":{y:0. for y in YEARS}},
  {"label":"2010 volume [50,100)", "lo":50,"hi":100,"n":0,"sums":{y:0. for y in YEARS}},
  {"label":"2010 volume [100,200)", "lo":100,"hi":200,"n":0,"sums":{y:0. for y in YEARS}},
  {"label":"2010 volume >= 200", "lo":200,"hi":None,"n":0,"sums":{y:0. for y in YEARS}}]
 joint_n=0; paired_totals={y:0. for y in YEARS}
 with ExitStack() as stack:
  vrts={}
  for name,(path,epsg) in sources.items():
   src=stack.enter_context(rasterio.open(path))
   if not matches_expected_crs(src.crs,epsg) or src.count!=1 or src.nodata!=-9999:
    raise ValueError("Raster CRS/band/NoData differs: "+name)
   vrts[name]=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=grid,
      width=w,height=h,src_nodata=-9999,nodata=-9999,
      resampling=Resampling.average,dtype="float32"))
  for row in range(0,h,256):
   for col in range(0,w,256):
    win=Window(col,row,min(256,w-col),min(256,h-row))
    inside=geometry_mask([mapping(geo)],out_shape=(int(win.height),int(win.width)),
        transform=rasterio.windows.transform(win,grid),invert=True)
    if not inside.any():continue
    arr={name:np.ma.asarray(v.read(1,window=win,masked=True),
           dtype="float64").filled(np.nan) for name,v in vrts.items()}
    good={name:inside & np.isfinite(v) & (v>=0) for name,v in arr.items()}
    paired=good["bio2010"] & good["bio2015"] & good["bio2018"]
    joint=paired & good["age2010"] & good["vol2010"]
    joint_n+=int(joint.sum())
    for y in YEARS:
     key="bio"+y
     own=good[key]
     v=arr[key]
     base[y]["own_n"]+=int(own.sum());base[y]["own_sum"]+=float(v[own].sum())
     base[y]["paired_n"]+=int(paired.sum());base[y]["paired_sum"]+=float(v[paired].sum())
     nz=paired & (v>0)
     base[y]["paired_positive_n"]+=int(nz.sum());base[y]["paired_positive_sum"]+=float(v[nz].sum())
     paired_totals[y]+=float(v[joint].sum())
    if not joint.any():continue
    age=arr["age2010"];volume=arr["vol2010"]
    for g in groups:
     test=joint & (age>=g["age_from"]) & (age<(g["age_to"] if g["age_to"] is not None else float("inf")))
     n=int(test.sum())
     if not n:continue
     g["n"]+=n
     for y in YEARS:g["sums"][y]+=float(arr["bio"+y][test].sum())
    for b in bands:
     if b["hi"]==0:test=joint & (volume==0)
     elif b["hi"] is None:test=joint & (volume>=b["lo"])
     else:test=joint & (volume>b["lo"] if b["lo"]==0 else volume>=b["lo"]) & (volume<b["hi"])
     n=int(test.sum())
     if not n:continue
     b["n"]+=n
     for y in YEARS:b["sums"][y]+=float(arr["bio"+y][test].sum())
 if not joint_n:raise ValueError("No valid joint cells")
 for y in YEARS:
  x=base[y]
  x["own_area_ha"]=x["own_n"]*.0625
  x["paired_area_ha"]=x["paired_n"]*.0625
  x["own_mean"]=x["own_sum"]/x["own_n"] if x["own_n"] else None
  x["paired_mean"]=x["paired_sum"]/x["paired_n"] if x["paired_n"] else None
  x["paired_positive_mean"]=x["paired_positive_sum"]/x["paired_positive_n"] if x["paired_positive_n"] else None
 def finish(g):
  n=g["n"]
  g["area_ha"]=n*.0625
  g["raw_means"]={y:g["sums"][y]/n if n else None for y in YEARS}
  g["mean_2010_minus_2015"]=((g["sums"]["2010"]-g["sums"]["2015"])/n) if n else None
  g["mean_2010_minus_2018"]=((g["sums"]["2010"]-g["sums"]["2018"])/n) if n else None
  g["share_of_total_2010_minus_2015"]=((g["sums"]["2010"]-g["sums"]["2015"])/(paired_totals["2010"]-paired_totals["2015"])) if paired_totals["2010"]!=paired_totals["2015"] else None
  g["share_of_total_2010_minus_2018"]=((g["sums"]["2010"]-g["sums"]["2018"])/(paired_totals["2010"]-paired_totals["2018"])) if paired_totals["2010"]!=paired_totals["2018"] else None
  g.pop("sums")
  return g
 for group in groups:finish(group)
 for band in bands:finish(band)
 if sum(g["n"] for g in groups)!=joint_n or sum(g["n"] for g in bands)!=joint_n:
  raise ValueError("Age or volume strata failed to partition common valid sample")
 result={"created_utc":datetime.now(timezone.utc).isoformat(),
  "status":"DESCRIPTIVE_2010_EXCESS_DIAGNOSTICS_NOT_HARMONIZED",
  "analysis_crs":"EPSG:3006","cell_size_m":25,
  "boundary_note":"Lulea project working geometry, not independently official municipal boundary",
  "paired_biomass_only":base,
  "joint_valid_with_2010_age_volume":{"cells":joint_n,"area_ha":joint_n*.0625,
    "raw_means":{y:paired_totals[y]/joint_n for y in YEARS}},
  "strata_age_as_of_2010":groups,"strata_volume_as_of_2010":bands,
  "limitations":[
   "All three biomass generations are compared cell for cell and their per-source independent coverage is reported",
   "Age and volume strata refer ONLY to 2010 baseline; not contemporary 2015 or 2018 stand classes",
   "2010 volume strata are a structural proxy, NOT verified pine/spruce classes",
   "No forest mask and no dated harvest exclusion in this particular diagnostic",
   "Strata and raw ratios do not prove equivalent biomass components, calibration method or physical units",
   "Difference remaining in fixed 2010 strata cannot distinguish real growth, harvest and product method shifts",
   "2010 biomass and volume are related model sources; not independent verification",
   "No actual 2015 or 2018 stand-age or species data used. No causal decomposition authorized"
  ]}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
