#!/usr/bin/env python3
"""Inspect the public SLU download indexes without downloading multi-GB rasters.

Output is a reviewable inventory, not a claim of validated carbon raster values.
All links must remain on gis.slu.se/data/ and discovery is capped.
"""
from __future__ import annotations
import argparse
import json
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, unquote
from urllib.request import Request, urlopen
from collections import deque
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
START=[
 "https://gis.slu.se/data/carbon/",
 "https://gis.slu.se/data/slu_forest_map/2015/",
 "https://gis.slu.se/data/slu_skogliga_grunddata/SGD2/data/",
]
ALLOWED_HOST="gis.slu.se"
BASE_PATH="/data/"
KEYWORDS=("stock","soc","biomass","biomassa","volym","volume","carbon","kol","lule","norrbotten","metadata","readme")
EXTS=(".tif",".tiff",".zip",".vrt",".pdf",".xml",".txt",".docx",".gpkg",".7z",".tfw")
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=="a":
   d=dict(attrs)
   if d.get("href"):self.links.append(d["href"])
def safe_url(href,parent):
 url=urljoin(parent,href)
 parsed=urlparse(url)
 if parsed.scheme!="https" or parsed.hostname!=ALLOWED_HOST:return None
 if not parsed.path.startswith(BASE_PATH):return None
 if parsed.query:return None
 if parsed.path==urlparse(parent).path:return None
 if ".." in unquote(parsed.path).split("/"):return None
 return url
def discover(starts=START,max_pages=35,seconds=1):
 queue=deque((u,0) for u in starts)
 visited=set();files=[];errors=[]
 while queue and len(visited)<max_pages:
  url,depth=queue.popleft()
  if url in visited:continue
  visited.add(url)
  try:
   req=Request(url,headers={"User-Agent":"Lulea-statistik-carbon-source-inventory/1.0"})
   with urlopen(req,timeout=25) as response:
    raw=response.read(2_000_000)
   parser=Links();parser.feed(raw.decode("utf-8",errors="replace"))
  except Exception as exc:
   errors.append({"url":url,"error":str(exc)[:300]});continue
  for href in parser.links:
   target=safe_url(href,url)
   if not target:continue
   path=unquote(urlparse(target).path)
   name=path.rstrip("/").rsplit("/",1)[-1]
   if name.endswith("/") or path.endswith("/"):
    if depth<3 and len(visited)+len(queue)<max_pages*4:queue.append((target,depth+1))
   elif name.lower().endswith(EXTS):
    files.append({"url":target,"name":name,"possible_relevance":any(word in path.lower() for word in KEYWORDS),
                  "directory":url})
  if seconds:time.sleep(seconds)
 return {"checked_at":datetime.now(timezone.utc).isoformat(),
         "scope":"Public SLU directory listings; files not downloaded or verified",
         "catalogue_urls":starts,"directories_checked":len(visited),
         "files":list({x["url"]:x for x in files}.values()),"errors":errors}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--max-pages",type=int,default=35)
 p.add_argument("--sleep",type=float,default=.25)
 p.add_argument("--output",type=Path,default=ROOT/"metadata"/"slu_source_inventory.json")
 args=p.parse_args()
 result=discover(max_pages=args.max_pages,seconds=args.sleep)
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Directory pages checked:",result["directories_checked"])
 print("Files found:",len(result["files"]))
 for x in result["files"]:
  if x["possible_relevance"]:print("CANDIDATE",x["url"])
 for e in result["errors"]:print("SOURCE ERROR",e["url"],e["error"])
 if not result["files"]:raise SystemExit("No file listings found; inspect source availability")
if __name__=="__main__":main()
