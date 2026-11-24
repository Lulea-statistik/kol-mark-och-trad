#!/usr/bin/env python3
"""Diagnose apparent 2005->2010 volume increase on identical raster cells.

The projected 2005 biomass uses a coefficient derived from 2010, so its
reported jump is mathematically the volume change, NOT independently
measured biomass. Validate source archives; separately analyze dated
estimated stand ages for 2005 and 2010. No causal attribution.
"""
from __future__ import annotations
import argparse,json,math
from contextlib import ExitStack
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from shapely.geometry import shape,mapping
from shapely.ops import transform as geom_transform
from pyproj import Transformer
from analyze_historic_volume import validate_archive
from analyze_forest_age_2010 import check_age
from model_age_adjusted_biomass import validate_historical_age
from verify_biomass_release import run as verify_biomass
from fetch_and_compare_biomass_native import matches_expected_crs

AGE_BINS=(0,20,40,60,80,100,120,150,200,500,float("inf"))
SOURCE={
 "volume_2000":("volume","2000",3021),
 "volume_2005":("volume","2005",3021),
 "volume_2010":("volume","2010",3021),
 "age_2005":("age","2005",3021),
 "age_2010":("age","2010",3021),
 "biomass_2010":("biomass","2010",3021),
 "biomass_2015":("biomass","2015",3006),
 "biomass_2018":("biomass","2018",3006)
}
def run(a):
 validate_archive(a.volume_dir,a.boundary)
 validate_historical_age(a.age_history_dir,a.boundary)
 check_age(a.age_2010_dir,a.boundary)
 verify_biomass(argparse.Namespace(directory=a.biomass_dir,output=a.qa_output))
 doc=json.loads(a.boundary.read_text(encoding="utf-8"))
 if doc.get("type")!="FeatureCollection" or len(doc.get("features",[]))!=1:
  raise ValueError("Expected one project polygon in GeoJSON EPSG:4326")
 poly=shape(doc["features"][0]["geometry"])
 if poly.is_empty or not poly.is_valid:raise ValueError("Invalid working polygon")
 xy=geom_transform(Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,poly)
 xmin,ymin,xmax,ymax=xy.bounds;step=25.
 xmin=math.floor(xmin/step)*step; ymin=math.floor(ymin/step)*step
 xmax=math.ceil(xmax/step)*step; ymax=math.ceil(ymax/step)*step
 w=round((xmax-xmin)/step);h=round((ymax-ymin)/step)
 if w*h>40_000_000:raise ValueError("Unexpected raster size")
 grid=Affine(step,0,xmin,0,-step,ymax)
 paths={}
 for key,(kind,year,_) in SOURCE.items():
  if kind=="volume":path=a.volume_dir/f"lulea_total_volume_{year}_source_crs_clip.tif"
  elif kind=="biomass":path=a.biomass_dir/f"lulea_biomass_{year}_source_crs_clip.tif"
  elif year=="2010":path=a.age_2010_dir/f"lulea_forest_age_{year}_source_crs_clip.tif"
  else:path=a.age_history_dir/f"lulea_forest_age_{year}_source_crs_clip.tif"
  paths[key]=path
 sums={year:0. for year in ("2000","2005","2010")}
 year_positive={year:0 for year in ("2000","2005","2010")}
 sample=0
 increased=decreased=same=0
 age_reset=age_approximately_stable=age_high_shift=0
 # A baseline classification from 2005, not 2010, to avoid using the
 # endpoint state as a predictor of change.
 rows=[{"age_2005_lower":AGE_BINS[i],
        "age_2005_upper":AGE_BINS[i+1] if math.isfinite(AGE_BINS[i+1]) else None,
        "n":0,"volume_2005_sum":0.,"volume_2010_sum":0.,
        "sum_age_2005":0.,"sum_age_2010":0.}
       for i in range(len(AGE_BINS)-1)]
 age_groups={
  "age_2010_at_least_10_less_than_2005":{"n":0,"volume_2005_sum":0.,"volume_2010_sum":0.},
  "age_2010_roughly_age_2005_plus_five":{"n":0,"volume_2005_sum":0.,"volume_2010_sum":0.},
  "other_age_changes":{"n":0,"volume_2005_sum":0.,"volume_2010_sum":0.}
 }
 with ExitStack() as stack:
  vrt={}
  for key,(_,_,epsg) in SOURCE.items():
   src=stack.enter_context(rasterio.open(paths[key]))
   if src.count!=1 or src.nodata!=-9999 or not matches_expected_crs(src.crs,epsg):
    raise ValueError(key+" raster does not have verified source CRS/NoData")
   vrt[key]=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",
           transform=grid,width=w,height=h,src_nodata=-9999,nodata=-9999,
           resampling=Resampling.average,dtype="float32"))
  for rr in range(0,h,256):
   for cc in range(0,w,256):
    win=Window(cc,rr,min(256,w-cc),min(256,h-rr))
    inside=geometry_mask([mapping(xy)],out_shape=(int(win.height),int(win.width)),
       transform=rasterio.windows.transform(win,grid),invert=True)
    if not inside.any():continue
    vals={k:np.ma.asarray(v.read(1,window=win,masked=True),
                dtype="float64").filled(np.nan) for k,v in vrt.items()}
    valid=inside.copy()
    for v in vals.values():valid &= np.isfinite(v)&(v>=0)
    if not valid.any():continue
    sample+=int(valid.sum())
    v0=vals["volume_2000"][valid]
    v5=vals["volume_2005"][valid]
    v10=vals["volume_2010"][valid]
    a5=vals["age_2005"][valid]
    a10=vals["age_2010"][valid]
    for year,v in (("2000",v0),("2005",v5),("2010",v10)):
     sums[year]+=float(v.sum(dtype="float64"))
     year_positive[year]+=int(np.count_nonzero(v>0))
    increased+=int(np.count_nonzero(v10>v5))
    decreased+=int(np.count_nonzero(v10<v5))
    same+=int(np.count_nonzero(v10==v5))
    reset=a10<a5-10
    steady=(a10>=a5-2)&(a10<=a5+12)
    strange=~(reset|steady)
    age_reset+=int(np.count_nonzero(reset))
    age_approximately_stable+=int(np.count_nonzero(steady))
    age_high_shift+=int(np.count_nonzero(strange))
    for label,selected in (
     ("age_2010_at_least_10_less_than_2005",reset),
     ("age_2010_roughly_age_2005_plus_five",steady),
     ("other_age_changes",strange)):
     n=int(np.count_nonzero(selected))
     if not n:continue
     row=age_groups[label]
     row["n"]+=n
     row["volume_2005_sum"]+=float(v5[selected].sum(dtype="float64"))
     row["volume_2010_sum"]+=float(v10[selected].sum(dtype="float64"))
    for row in rows:
     upper=row["age_2005_upper"] if row["age_2005_upper"] is not None else float("inf")
     sel=(a5>=row["age_2005_lower"])&(a5<upper)
     n=int(np.count_nonzero(sel))
     if not n:continue
     row["n"]+=n
     row["volume_2005_sum"]+=float(v5[sel].sum(dtype="float64"))
     row["volume_2010_sum"]+=float(v10[sel].sum(dtype="float64"))
     row["sum_age_2005"]+=float(a5[sel].sum(dtype="float64"))
     row["sum_age_2010"]+=float(a10[sel].sum(dtype="float64"))
 if sample<=0 or sums["2005"]<=0:raise ValueError("No joint 8-layer support")
 if sum(row["n"] for row in rows)!=sample or sum(row["n"] for row in age_groups.values())!=sample:
  raise ValueError("Age classification did not partition common sample")
 delta=sums["2010"]-sums["2005"]
 for row in rows:
  n=row["n"]
  row["area_ha"]=n*.0625
  row["mean_volume_2005"]=row.pop("volume_2005_sum")/n if n else None
  row["mean_volume_2010"]=row.pop("volume_2010_sum")/n if n else None
  row["mean_age_2005"]=row.pop("sum_age_2005")/n if n else None
  row["mean_age_2010"]=row.pop("sum_age_2010")/n if n else None
  if n:row["mean_change_2005_2010"]=row["mean_volume_2010"]-row["mean_volume_2005"]
 for label,row in age_groups.items():
  n=row["n"];s5=row.pop("volume_2005_sum");s10=row.pop("volume_2010_sum")
  row["area_ha"]=n*.0625
  row["mean_volume_2005"]=s5/n if n else None
  row["mean_volume_2010"]=s10/n if n else None
  row["difference_contribution_fraction"]=(s10-s5)/delta if delta else None
 result={
  "generated_utc":datetime.now(timezone.utc).isoformat(),
  "status":"HISTORICAL_VOLUME_CHANGE_DESCRIPTIVE_NOT_GROWTH",
  "analysis_crs":"EPSG:3006","pixel_size_m":25,
  "common_valid_cells":sample,"common_valid_area_ha":sample*.0625,
  "volume_raw_means":{year:sums[year]/sample for year in sums},
  "volume_raw_change_percent_2000_2005":100*(sums["2005"]/sums["2000"]-1) if sums["2000"]>0 else None,
  "volume_raw_change_percent_2005_2010":100*(sums["2010"]/sums["2005"]-1),
  "volume_cells_increase_fraction_2005_2010":increased/sample,
  "volume_cells_decrease_fraction_2005_2010":decreased/sample,
  "volume_cells_equal_fraction_2005_2010":same/sample,
  "age_difference_classes":{"age_2010_at_least_10_less_than_2005":age_groups["age_2010_at_least_10_less_than_2005"],
   "age_2010_roughly_age_2005_plus_five":age_groups["age_2010_roughly_age_2005_plus_five"],
   "other_age_changes":age_groups["other_age_changes"]},
  "baseline_age_2005_strata":rows,
  "biomass_2005_is_derived_from_2010_factor":True,
  "biomass_peak_2005_to_2010_not_independent":True,
  "cautions":[
   "2005 biomass in current website is 2005 total volume times 2010 biomass/volume on a separate common support; its apparent change to 2010 is by construction volume change",
   "All three volume estimates are separate SLU kNN remote-sensing products; differences are not measured live wood growth",
   "2005 and 2010 age are modelled maps whose image dates and errors are not synchronized",
   "Age difference < -10 years flags possible reset (harvest, regeneration, inconsistent age models), NOT proven logging",
   "Stable-age criterion of -2 to +12 years is a diagnostic tolerance only, not an inferential growth model",
   "Only common support of 8 available layers, not official Lulea boundary or verified forest-land mask",
   "No stem species stratification here and no assumption biomass products 2010-2018 use the same components"
  ]}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--volume-dir",type=Path,default=Path("release-volume"))
 p.add_argument("--biomass-dir",type=Path,default=Path("release-biomass"))
 p.add_argument("--age-2010-dir",type=Path,default=Path("release-age-2010"))
 p.add_argument("--age-history-dir",type=Path,default=Path("release-age-history"))
 p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
 p.add_argument("--qa-output",type=Path,default=Path("metadata/biomass_release_validation_2005_2010.json"))
 p.add_argument("--output",type=Path,default=Path("metadata/volume_2005_2010_diagnostics.json"))
 run(p.parse_args())
