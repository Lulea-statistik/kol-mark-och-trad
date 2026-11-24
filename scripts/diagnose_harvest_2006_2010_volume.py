#!/usr/bin/env python3
"""Overlap actually mapped 2006-2010 harvests with 2005/2010 raster volume.

Compare identical cells and classify 2005 vs 2010 age changes. NOT a causal
growth or harvest model. Report missing record and detection limitations.
"""
from __future__ import annotations
import argparse,json,math
from collections import defaultdict
from datetime import datetime,timezone
from contextlib import ExitStack
from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask,rasterize
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from shapely.geometry import shape,mapping,box
from shapely.ops import transform as geom_transform
from pyproj import Transformer
from biomass_harvest_overlay import request,date_year,FIELDS,BASE
from analyze_historic_volume import validate_archive
from analyze_forest_age_2010 import check_age
from model_age_adjusted_biomass import validate_historical_age
from verify_biomass_release import run as verify_biomass
from diagnose_2005_2010_volume_jump import SOURCE
from fetch_and_compare_biomass_native import matches_expected_crs

def load_polygons(geo):
 xmin,ymin,xmax,ymax=geo.bounds
 env=json.dumps({"xmin":xmin,"ymin":ymin,"xmax":xmax,"ymax":ymax,"spatialReference":{"wkid":3006}})
 q={"where":"1=1","geometry":env,"geometryType":"esriGeometryEnvelope",
    "inSR":"3006","spatialRel":"esriSpatialRelIntersects",
    "returnIdsOnly":"true","f":"json"}
 rsp=request(q)
 ids=rsp.get("objectIds")
 if not isinstance(ids,list):raise ValueError("Harvest service lacked objectIds")
 if len(ids)>200000:raise ValueError("Unexpected number of harvest polygons")
 to3006=Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True)
 found=[];counts=defaultdict(int)
 for start in range(0,len(ids),150):
  group=ids[start:start+150]
  rsp=request({"objectIds":",".join(map(str,group)),"outFields":FIELDS,
               "returnGeometry":"true","outSR":"4326","f":"geoJSON"},timeout=65)
  features=rsp.get("features")
  if not isinstance(features,list) or len(features)!=len(group):
   raise ValueError("ArcGIS harvest pagination or GeoJSON failed")
  for f in features:
   props=f.get("properties",{})
   year=date_year(props.get("Avvdatum"))
   counts["fetched_features"]+=1
   if year is None:counts["missing_date"]+=1;continue
   if not 2006<=year<=2010:continue
   if not f.get("geometry"):counts["missing_geometry"]+=1;continue
   g=geom_transform(to3006.transform,shape(f["geometry"]))
   if g.is_empty or not g.is_valid:
    counts["invalid_geometry"]+=1;continue
   if not g.intersects(geo):continue
   clipped=g.intersection(geo)
   if clipped.is_empty or not clipped.is_valid:raise ValueError("Invalid clip of harvest geometry")
   found.append(clipped)
   counts["year_"+str(year)]+=1
 counts["bbox_query_ids"]=len(ids)
 counts["valid_2006_2010_clip_polygons"]=len(found)
 if not found:raise ValueError("No 2006-2010 harvest polygons found: cannot confirm complete historical coverage")
 return found,dict(counts)

def run(a):
 validate_archive(a.volume_dir,a.boundary)
 validate_historical_age(a.age_history_dir,a.boundary)
 check_age(a.age_2010_dir,a.boundary)
 verify_biomass(argparse.Namespace(directory=a.biomass_dir,output=a.qa_output))
 doc=json.loads(a.boundary.read_text(encoding="utf-8"))
 if doc.get("type")!="FeatureCollection" or len(doc.get("features",[]))!=1:raise ValueError("Project working geometry must be one feature")
 poly=shape(doc["features"][0]["geometry"])
 if poly.is_empty or not poly.is_valid:raise ValueError("Invalid boundary")
 xy=geom_transform(Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,poly)
 harvested,counts=load_polygons(xy)
 size=25.
 left,bottom,right,top=xy.bounds
 left=math.floor(left/size)*size;bottom=math.floor(bottom/size)*size
 right=math.ceil(right/size)*size;top=math.ceil(top/size)*size
 width=round((right-left)/size);height=round((top-bottom)/size)
 if width*height>40_000_000:raise ValueError("Unexpected area extent")
 grid=Affine(size,0,left,0,-size,top)
 paths={}
 for name,(kind,year,epsg) in SOURCE.items():
  if kind=="volume":path=a.volume_dir/f"lulea_total_volume_{year}_source_crs_clip.tif"
  elif kind=="biomass":path=a.biomass_dir/f"lulea_biomass_{year}_source_crs_clip.tif"
  elif year=="2010":path=a.age_2010_dir/f"lulea_forest_age_{year}_source_crs_clip.tif"
  else:path=a.age_history_dir/f"lulea_forest_age_{year}_source_crs_clip.tif"
  paths[name]=(path,epsg)
 stats={k:defaultdict(float) for k in ("harvest_detected_2006_2010","no_harvest_record_2006_2010")}
 with ExitStack() as stack:
  vrt={}
  for name,(path,epsg) in paths.items():
   src=stack.enter_context(rasterio.open(path))
   if src.nodata!=-9999 or src.count!=1 or not matches_expected_crs(src.crs,epsg):
    raise ValueError("Unverified raster native CRS for "+name)
   vrt[name]=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=grid,
    width=width,height=height,nodata=-9999,src_nodata=-9999,dtype="float32",resampling=Resampling.average))
  for row in range(0,height,256):
   for col in range(0,width,256):
    win=Window(col,row,min(256,width-col),min(256,height-row))
    tf=rasterio.windows.transform(win,grid);wh=(int(win.height),int(win.width))
    inside=geometry_mask([mapping(xy)],out_shape=wh,transform=tf,invert=True)
    if not inside.any():continue
    v={k:np.ma.asarray(src.read(1,window=win,masked=True),dtype="float64").filled(np.nan)
       for k,src in vrt.items()}
    joint=inside.copy()
    for arr in v.values():joint &=np.isfinite(arr)&(arr>=0)
    if not joint.any():continue
    tile=box(*rasterio.windows.bounds(win,grid))
    chosen=[g for g in harvested if g.intersects(tile)]
    harv=(rasterize(((mapping(g),1) for g in chosen),out_shape=wh,transform=tf,
                    fill=0,dtype="uint8")>0) if chosen else np.zeros(wh,dtype=bool)
    for label,flag in (("harvest_detected_2006_2010",harv),("no_harvest_record_2006_2010",~harv)):
     mask=joint &flag
     n=int(mask.sum())
     if not n:continue
     b=stats[label];b["cells"]+=n
     v5=v["volume_2005"][mask];v10=v["volume_2010"][mask]
     b["sum_vol_2005"]+=float(v5.sum());b["sum_vol_2010"]+=float(v10.sum())
     b["vol_increase_cells"]+=int((v10>v5).sum())
     a5=v["age_2005"][mask];a10=v["age_2010"][mask]
     b["age_reset_cells"]+=int((a10<a5-10).sum())
 if sum(int(x["cells"]) for x in stats.values())!=2316804:
  raise ValueError("Expected exact same 8-source 144800.25 ha population as website")
 out={}
 total_delta=sum(x["sum_vol_2010"]-x["sum_vol_2005"] for x in stats.values())
 for key,b in stats.items():
  n=int(b["cells"])
  out[key]={"cells":n,"area_ha":n*.0625,
    "mean_volume_2005":b["sum_vol_2005"]/n if n else None,
    "mean_volume_2010":b["sum_vol_2010"]/n if n else None,
    "raw_mean_change":(b["sum_vol_2010"]-b["sum_vol_2005"])/n if n else None,
    "share_cells_volume_increased":b["vol_increase_cells"]/n if n else None,
    "share_cells_age_2010_at_least_10_years_lower":b["age_reset_cells"]/n if n else None,
    "contribution_to_total_volume_net_increase":(b["sum_vol_2010"]-b["sum_vol_2005"])/total_delta if total_delta else None}
 result={"status":"HARVEST_2006_2010_HISTORICAL_VOLUME_DESCRIPTIVE_ONLY",
  "generated_utc":datetime.now(timezone.utc).isoformat(),
  "harvest_source":BASE,
  "project_boundary_crs":"EPSG:4326","harvest_source_crs":"EPSG:3006",
  "analysis_crs":"EPSG:3006","grid_cell_m":25,
  "common_valid_cells":sum(x["cells"] for x in out.values()),
  "common_valid_area_ha":sum(x["area_ha"] for x in out.values()),
  "harvest_source_records":counts,
  "strata":out,
  "limitations":[
   "The 2006-2010 detection layers are incomplete and dates may reflect later detection",
   "No recorded harvest is NOT proof that land was not harvested",
   "Five-year source map nominal epochs do not guarantee acquisition dates 2005 vs 2010",
   "All volume and age values are model raster estimates, not field-measured changes",
   "Age reset proxy is neither proof of harvest nor verification of the harvest polygons",
   "Raster sample limited to eight-way valid footprint 144800.25 ha, not official municipality forest area",
   "No species or site productivity control; descriptive contrasts do not establish causality"]}
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
 p.add_argument("--qa-output",type=Path,default=Path("metadata/biomass_2006_2010_harvest_qa.json"))
 p.add_argument("--output",type=Path,default=Path("metadata/harvest_2006_2010_volume_diagnostics.json"))
 run(p.parse_args())
