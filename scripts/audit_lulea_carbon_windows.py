#!/usr/bin/env python3
"""Audit SLU's two Norrbotten GeoTIFFs at Lulea's actual municipality footprint.

This deliberately samples a few source-CRS windows instead of downloading the
whole raster, and never estimates a municipality carbon total from samples.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window, transform as window_transform
from rasterio.features import geometry_mask
from shapely.geometry import shape, mapping
from shapely.ops import transform as shape_transform
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
BOUNDARY=ROOT/"docs"/"data"/"lulea_boundary.geojson"
TARGETS={
 "soil":"https://gis.slu.se/data/carbon/2023/Stock_SOC_2023_Lan/SOC_2023_Norrbottens.tif",
 "soil_all":"https://gis.slu.se/data/carbon/2023/Stock_All_2023_Lan/Stock_All_2023_Norrbottens.tif",
}
ENV={
 "GDAL_DISABLE_READDIR_ON_OPEN":"EMPTY_DIR",
 "CPL_VSIL_CURL_ALLOWED_EXTENSIONS":".tif",
 "GDAL_HTTP_MAX_RETRY":"2",
 "GDAL_HTTP_RETRY_DELAY":"1",
 "GDAL_HTTP_TIMEOUT":"45",
}
def audit(url,polygon,sample_size):
 result={"url":url,"status":"unverified","physical_units_verified":False,
         "carbon_total_computed":False,"municipal_polygon_crs":"EPSG:4326",
         "municipal_geometry_status":"working boundary, not yet validated against official dataset"}
 with rasterio.Env(**ENV):
  with rasterio.open("/vsicurl/"+url) as src:
   if not src.crs:raise ValueError("Raster source CRS missing")
   if src.count!=1:raise ValueError("Unexpected number of bands")
   poly_src=shape_transform(Transformer.from_crs("EPSG:4326",src.crs,always_xy=True).transform,polygon)
   if not poly_src.is_valid or poly_src.is_empty:raise ValueError("Invalid municipal boundary")
   raw_window=from_bounds(*poly_src.bounds,transform=src.transform)
   window=raw_window.round_offsets().round_lengths().intersection(Window(0,0,src.width,src.height))
   result.update({
    "status":"source_georeferencing_verified",
    "crs":str(src.crs),"epsg":src.crs.to_epsg(),
    "pixel_size":[float(src.res[0]),float(src.res[1])],
    "raster_size":[src.width,src.height],"source_nodata":src.nodata,
    "source_dtype":src.dtypes[0],"scale":src.scales[0],"offset":src.offsets[0],
    "source_units_tag":src.units[0],"band_description":src.descriptions[0],
    "tags":src.tags(),"band_tags":src.tags(1),
    "municipal_bbox_pixels":[int(window.height),int(window.width)],
    "municipal_bbox_metres":list(poly_src.bounds),
   })
   if window.width<=0 or window.height<=0:raise ValueError("Source does not overlap municipality bbox")
   # Six spatially separated, compact windows. Each is independently masked
   # to the municipality geometry IN THE SOURCE CRS before sampling.
   wins=[]
   for fy in (.2,.5,.8):
    for fx in (.3,.7):
     cx=int(window.col_off+window.width*fx)
     cy=int(window.row_off+window.height*fy)
     col=max(0,min(src.width-sample_size,cx-sample_size//2))
     row=max(0,min(src.height-sample_size,cy-sample_size//2))
     wins.append(Window(col,row,min(src.width,sample_size),min(src.height,sample_size)))
   samples=[]
   for w in wins:
    wt=window_transform(w,src.transform)
    inside=geometry_mask([mapping(poly_src)],out_shape=(int(w.height),int(w.width)),
                         transform=wt,invert=True,all_touched=False)
    arr=src.read(1,window=w,masked=True)
    valid=inside&(~np.ma.getmaskarray(arr))&np.isfinite(np.asarray(arr.data))
    vals=np.asarray(arr.data)[valid]
    samples.append({"row":int(w.row_off),"col":int(w.col_off),
       "pixels_inside_polygon":int(np.count_nonzero(inside)),
       "pixels_valid":int(vals.size),
       "min_raw":float(np.min(vals)) if vals.size else None,
       "max_raw":float(np.max(vals)) if vals.size else None,
       "mean_raw":float(np.mean(vals.astype("float64"))) if vals.size else None})
   result["source_crs_samples"]=samples
   result["important_limit"]="Samples cover tiny selected windows only, not full Lulea area. Never aggregate or extrapolate raw values as tonnes C."
 return result

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--output",type=Path,default=ROOT/"metadata"/"lulea_carbon_window_audit.json")
 p.add_argument("--sample-size",type=int,default=128)
 args=p.parse_args()
 if not 16<=args.sample_size<=256:p.error("sample-size must be between 16 and 256")
 fc=json.loads(BOUNDARY.read_text(encoding="utf-8"))
 polygon=shape(fc["features"][0]["geometry"])
 if not polygon.is_valid or polygon.is_empty:raise SystemExit("Invalid Lulea working boundary")
 result={"checked_at":datetime.now(timezone.utc).isoformat(),"scope":"Lulea municipality working boundary, two county rasters, only bounded samples",
         "no_carbon_totals":True,"products":{}}
 for key,url in TARGETS.items():
  try:
   item=audit(url,polygon,args.sample_size)
  except Exception as e:
   item={"url":url,"status":"failed","error":str(e)[:1200]}
  result["products"][key]=item
  print(key,"status:",item["status"],"EPSG:",item.get("epsg"),
        "source units tag:",item.get("source_units_tag"),"municipal bbox:",item.get("municipal_bbox_pixels"),flush=True)
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
 print("AUDIT",args.output)
 if not all(x.get("status")=="source_georeferencing_verified" for x in result["products"].values()):
  raise SystemExit("One or both SLU carbon raster windows failed; inspect artifact")
if __name__=="__main__":main()
