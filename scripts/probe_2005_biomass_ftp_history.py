#!/usr/bin/env python3
"""Check whether 2015 FTP-index historical SLU 2005 biomass still has live URL.

The FTPStatus 2015 inventory proves historical existence, NOT current access.
Never download entire national raster; use HTTP HEAD, 1-byte range, and
GDAL remote metadata only after a working endpoint is detected.
"""
from __future__ import annotations
import argparse, json, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urljoin

HISTORICAL={
 "report":"https://www.ftpstatus.com/reports/salix.slu.se.pdf",
 "scan_date":"2015-01-10",
 "remote_path":"/download/skogskarta/2005/_Swedenxx/Biomass_XX_P_05.tif",
 "modified":"2011-03-15",
 "historical_size":"1.45 GB",
 "deprecated_zip":"/download/skogskarta/2005/oo_ignore/deprecated/2005__Sweden_biomass.zip"
}
BASE="https://gis.slu.se/data/slu_forest_map/2005/"
DIRS=["Data/Raster/Rt90/","Data/knn.gdb/","LayerFiles/Rt90/"]
CANDIDATES=[
 "Data/Raster/Rt90/Biomass_XX_P_05.tif",
 "Data/Raster/Rt90/Biomass_xx_P_05.tif",
 "Data/Raster/Rt90/BIOMASS_XX_P_05.tif",
 "Data/Raster/Rt90/biomass_xx_p_05.tif",
 "Data/Raster/Rt90/biomass_XX_P_05.tif",
 "Data/Raster/Rt90/BIOMASS_XX_P_05.TIF",
 "Data/Raster/Rt90/Biomass_XX_P_05.TIF",
 "Data/knn.gdb/",
 "LayerFiles/Rt90/"
]
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,t,attrs):
  if t=="a":
   href=dict(attrs).get("href")
   if href:self.links.append(href)
def req(url,method="HEAD",range_header=None):
 out={"url":url,"method":method}
 headers={"User-Agent":"Lulea-statistik-historical-forest-source/1.0"}
 if range_header:headers["Range"]=range_header
 request=urllib.request.Request(url,method=method,headers=headers)
 try:
  with urllib.request.urlopen(request,timeout=25) as response:
   out["status"]=response.status
   out["content_type"]=response.headers.get("Content-Type")
   out["content_length"]=response.headers.get("Content-Length")
   out["accept_ranges"]=response.headers.get("Accept-Ranges")
   out["content_range"]=response.headers.get("Content-Range")
   if method=="GET" and range_header and response.status==206:
    out["sample"]=response.read(32).hex()
 except urllib.error.HTTPError as e:
  out["status"]=e.code;out["error"]=str(e)
 except Exception as e:out["status"]="error";out["error"]=str(e)[:500]
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=Path("metadata/slu_2005_biomass_historic_ftp_probe.json"))
 a=p.parse_args()
 result={"created_utc":datetime.now(timezone.utc).isoformat(),
  "historic_evidence":HISTORICAL,"current_raster_verified":False,
  "current_url":None,"directory_listings":[],"http_candidates":[],
  "conclusion":"historical file existence does not establish current access"}
 for path in DIRS:
  url=urljoin(BASE,path)
  d={"url":url}
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=25) as response:
    content=response.read(300000).decode("utf-8","replace")
   html=Links();html.feed(content)
   d["status"]="read"
   d["links"]=html.links[:250]
  except Exception as e:d["status"]="error";d["error"]=str(e)[:300]
  result["directory_listings"].append(d)
 urls=[urljoin(BASE,p) for p in CANDIDATES if not p.endswith("/")]
 for d in result["directory_listings"]:
  for href in d.get("links",[]):
   if "biomass" in href.lower() and (href.lower().endswith(".tif") or href.lower().endswith(".tiff")):
    urls.append(urljoin(d["url"],href))
 for url in sorted(set(urls)):
  record=req(url)
  if record.get("status")==200:
   range_result=req(url,method="GET",range_header="bytes=0-31")
   record["range_test"]=range_result
   if range_result.get("status")==206:
    try:
     import rasterio
     from fetch_and_compare_biomass_native import matches_expected_crs
     with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
         GDAL_HTTP_MAX_RETRY="1",GDAL_HTTP_TIMEOUT="25",
         CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff"):
      with rasterio.open("/vsicurl/"+url) as src:
       record["raster"]={"crs_wkt":src.crs.to_wkt() if src.crs else None,
          "crs_is_epsg3021":matches_expected_crs(src.crs,3021),"resolution":src.res,
          "nodata":src.nodata,"scale":src.scales[0],"offset":src.offsets[0],
          "bands":src.count,"dtype":src.dtypes[0]}
       record["verified_raster"]=bool(src.count==1 and src.nodata is not None
           and matches_expected_crs(src.crs,3021)
           and all(abs(abs(v)-25)<0.05 for v in src.res))
       if record["verified_raster"]:
        result["current_raster_verified"]=True
        result["current_url"]=url
    except Exception as e:record["raster_error"]=str(e)[:500]
  result["http_candidates"].append(record)
  print(json.dumps({"url":url,"status":record.get("status"),
    "verified":record.get("verified_raster",False)},ensure_ascii=False),flush=True)
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("VERIFIED RASTER:",result["current_url"],flush=True)
 # This is a discovery run. A pass means the inventory was completed;
 # users must check current_raster_verified before using the data.
if __name__=="__main__":main()
