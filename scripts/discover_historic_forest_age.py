#!/usr/bin/env python3
"""Discover SLU forest map year 2000/2005 age and biomass raster URLs.

A source is accepted only when a remote GTiff opens and its raster metadata
matches the expected original CRS and resolution. No guesses promoted to data.
"""
from __future__ import annotations
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
import rasterio
from fetch_and_compare_biomass_native import matches_expected_crs

class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            href=dict(attrs).get("href","")
            if href:self.links.append(href)

def discover(year):
    base=f"https://gis.slu.se/data/slu_forest_map/{year}/Data/Raster/Rt90/"
    try:
        with urllib.request.urlopen(base,timeout=35) as page:
            html=page.read(1_000_000).decode("utf-8","replace")
        parser=Links();parser.feed(html)
        listing=[urllib.parse.unquote(x).split("/")[-1] for x in parser.links]
        candidate=[v for v in listing if v.lower().endswith(".tif") and
                   (re.search(r"age",v,re.I) or re.search(r"biomass",v,re.I))]
        return base,candidate,None
    except Exception as err:
        return base,[],str(err)

def probe(url):
    result={"url":url,"status":"unverified"}
    try:
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                          GDAL_HTTP_MAX_RETRY="2",GDAL_HTTP_TIMEOUT="35",
                          CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff"):
            with rasterio.open("/vsicurl/"+url) as src:
                result.update(status="verified" if src.count==1 and
                    matches_expected_crs(src.crs,3021) and
                    all(abs(abs(r)-25)<.05 for r in src.res) and src.nodata is not None
                    and src.scales[0]==1 and src.offsets[0]==0 else "unexpected_metadata",
                    crs_wkt=src.crs.to_wkt() if src.crs else None,
                    native_epsg=src.crs.to_epsg() if src.crs else None,
                    resolution=list(src.res),bands=src.count,nodata=src.nodata,
                    scale=src.scales[0],offset=src.offsets[0],dtype=src.dtypes[0])
    except Exception as err:result["error"]=str(err)[:500]
    return result

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("metadata/historical_forest_raster_discovery.json"))
    a=p.parse_args()
    report={"created_utc":datetime.now(timezone.utc).isoformat(),"years":{}}
    for year in ("2000","2005"):
        base,listed,error=discover(year)
        # Listing is authoritative when available. Candidate fallback is
        # recorded but must independently open to be trusted.
        expected=[f"AGE_XX_P_{year[-2:]}.tif"]
        if year=="2005":expected.append("BIOMASS_XX_P_05.tif")
        paths=sorted(set(listed+expected))
        items=[probe(urllib.parse.urljoin(base,p)) for p in paths]
        report["years"][year]={"listing_error":error,"listed_candidates":listed,
                               "files":items}
        print(year,json.dumps(items,ensure_ascii=False),flush=True)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Discovery may be incomplete even if all guessed paths are absent; retain
    # the evidence rather than declaring nonexistent dataset.
    if not all(any(v["status"]=="verified" and "AGE" in v["url"].upper()
                   for v in report["years"][year]["files"]) for year in ("2000","2005")):
        raise SystemExit("Historical AGE metadata not fully verified. Review diagnostic artifact.")
if __name__=="__main__":main()
