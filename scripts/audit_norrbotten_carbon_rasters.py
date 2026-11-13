#!/usr/bin/env python3
"""Read real metadata of the two Norrbotten SLU carbon rasters.

Do not download either whole county raster and do not make carbon totals.
Results are an auditable JSON artifact for a later municipality-only import.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

ROOT=Path(__file__).resolve().parents[1]
URLS={
 "soil":"https://gis.slu.se/data/carbon/2023/Stock_SOC_2023_Lan/SOC_2023_Norrbottens.tif",
 "soil_all":"https://gis.slu.se/data/carbon/2023/Stock_All_2023_Lan/Stock_All_2023_Norrbottens.tif",
}
def probe_http(url):
 item={}
 for method in ("HEAD","GET"):
  req=Request(url,method=method,headers={"User-Agent":"Lulea-statistik-carbon-raster-audit/1.0",
    "Range":"bytes=0-4095"} if method=="GET" else {"User-Agent":"Lulea-statistik-carbon-raster-audit/1.0"})
  try:
   with urlopen(req,timeout=45) as res:
    item[method.lower()]={"status":res.status,"content_length":res.headers.get("Content-Length"),
      "accept_ranges":res.headers.get("Accept-Ranges"),"content_type":res.headers.get("Content-Type")}
    if method=="GET":
     if res.status!=206:
      item["get"]["warning"]="Server did not confirm byte range; response body NOT downloaded"
     else:
      item["get"]["bytes_received"]=len(res.read(4096))
  except (HTTPError,URLError,TimeoutError) as e:
   item[method.lower()]={"error":str(e)[:250]}
 return item

def raster_metadata(url):
 import rasterio
 # GDAL /vsicurl uses HTTP range reads for GeoTIFF header/metadata.
 # Disable directory listings that might cause extra huge requests.
 env={"GDAL_DISABLE_READDIR_ON_OPEN":"EMPTY_DIR","CPL_VSIL_CURL_ALLOWED_EXTENSIONS":".tif",
      "GDAL_HTTP_MAX_RETRY":"2","GDAL_HTTP_RETRY_DELAY":"1"}
 with rasterio.Env(**env):
  with rasterio.open("/vsicurl/"+url) as ds:
   band=ds.indexes[0]
   scale=ds.scales[0] if ds.scales else None
   offset=ds.offsets[0] if ds.offsets else None
   tags=ds.tags()
   bands=ds.tags(band)
   return {"driver":ds.driver,"width":ds.width,"height":ds.height,
       "count":ds.count,"dtype":ds.dtypes[0],"nodata":ds.nodata,
       "crs":str(ds.crs) if ds.crs else None,"epsg":ds.crs.to_epsg() if ds.crs else None,
       "resolution":[abs(ds.transform.a),abs(ds.transform.e)],
       "bounds":list(ds.bounds),"scale":scale,"offset":offset,
       "units":ds.units[0] if ds.units else None,
       "tags":tags,"band_tags":bands,"descriptions":list(ds.descriptions),
       "overviews":ds.overviews(band),"is_tiled":ds.is_tiled}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--output",type=Path,default=ROOT/"metadata"/"norrbotten_carbon_raster_audit.json")
 args=p.parse_args()
 entries={}
 for key,url in URLS.items():
  record={"url":url,"http":probe_http(url),"raster":None,"raster_error":None,
          "physical_units_verified":False,"lulea_extent_verified":False}
  try:record["raster"]=raster_metadata(url)
  except Exception as exc:record["raster_error"]=str(exc)[:1000]
  # A GeoTIFF 'unit' string is not sufficient to establish whether values
  # are kg C/m2, tonnes/ha, etc.; require external product documentation.
  if record["raster"]:
   m=record["raster"]
   record["crs_reported"]=bool(m["crs"])
   record["pixel_scale_offset_reported"]=[m["scale"],m["offset"]]
  entries[key]=record
  print(key,"EPSG:",(record["raster"] or {}).get("epsg"),"error:",record["raster_error"],flush=True)
 output={"checked_at":datetime.now(timezone.utc).isoformat(),
     "scope":"SLU Norrbotten 2023 county raster metadata, no geographic raster downloaded or carbon sum calculated",
     "units_status":"UNVERIFIED: verify product manual before any carbon conversion",
     "entries":entries}
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
 print("Audit file:",args.output)
 if all(not x["raster"] for x in entries.values()):
  raise SystemExit("No raster headers could be read. Review audit artifact and source access.")
if __name__=="__main__":main()
