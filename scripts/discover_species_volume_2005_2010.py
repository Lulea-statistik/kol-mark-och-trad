#!/usr/bin/env python3
"""Locate historical tree-species volume rasters for Skogskarta 2005/2010.

Never infer species layer or units from an unverified filename. Inspect the
actual directory listing; candidates are independently opened as GeoTIFF.
No national raster is downloaded.
"""
from __future__ import annotations
import argparse,json,re,urllib.parse,urllib.request
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
import rasterio
from fetch_and_compare_biomass_native import matches_expected_crs

class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=="a":
   x=dict(attrs).get("href")
   if x:self.links.append(x)

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--output",type=Path,default=Path("metadata/species_volume_source_2005_2010.json"))
 a=p.parse_args()
 result={"generated_utc":datetime.now(timezone.utc).isoformat(),"status":"completed_discovery_only",
         "source_years":{},"verified_species_source_count":0,
         "limitations":["File name alone is NOT authoritative proof of species composition or units",
                        "Historical species volume rasters may share kNN calibration with TOTALVOL and are not independent validation"]}
 for year in (2005,2010):
  base=f"https://gis.slu.se/data/slu_forest_map/{year}/Data/Raster/Rt90/"
  record={"directory":base,"listed_tifs":[],"candidate_files":[],"listing_error":None}
  try:
   req=urllib.request.Request(base,headers={"User-Agent":"Lulea-statistik-forest-species-discovery/1.0"})
   with urllib.request.urlopen(req,timeout=45) as res:
    markup=res.read(2_000_000).decode("utf-8","replace")
   parser=Links();parser.feed(markup)
   tif_names=sorted(set(urllib.parse.unquote(x).split("/")[-1] for x in parser.links if x.lower().split("?")[0].endswith((".tif",".tiff"))))
   record["listed_tifs"]=tif_names[:250]
  except Exception as exc: record["listing_error"]=str(exc)[:600]
  patterns=[r"pine",r"spruc",r"sprce",r"gran",r"tall",r"birch",r"decid",r"conif"]
  candidates=[n for n in record["listed_tifs"] if any(re.search(p,n,re.I) for p in patterns)]
  for name in candidates:
   url=urllib.parse.urljoin(base,urllib.parse.quote(name))
   item={"name":name,"url":url,"verified":False}
   try:
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
      GDAL_HTTP_MAX_RETRY="1",GDAL_HTTP_TIMEOUT="40",
      CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff"):
     with rasterio.open("/vsicurl/"+url) as src:
      item.update(epsg=src.crs.to_epsg() if src.crs else None,
         crs_wkt=src.crs.to_wkt() if src.crs else None,
         cell_size_m=list(src.res),bands=src.count,nodata=src.nodata,
         scale=src.scales[0],offset=src.offsets[0],dtype=src.dtypes[0])
      item["verified"]=bool(matches_expected_crs(src.crs,3021) and
        all(abs(abs(x)-25)<0.05 for x in src.res) and src.count==1 and
        src.nodata is not None and src.scales[0]==1 and src.offsets[0]==0)
      if item["verified"]:result["verified_species_source_count"]+=1
   except Exception as exc:item["error"]=str(exc)[:600]
   record["candidate_files"].append(item)
  result["source_years"][str(year)]=record
  print(year,"listed",len(record["listed_tifs"]),"species candidates",
        [(x["name"],x["verified"]) for x in record["candidate_files"]],flush=True)
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("verified source files",result["verified_species_source_count"],flush=True)
if __name__=="__main__":main()
