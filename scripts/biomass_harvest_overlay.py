#!/usr/bin/env python3
"""Exploratory overlay of Skogsstyrelsen detected harvests and archived biomass.

No source raster changes. Harvest layer is an incomplete guiding dataset,
NOT a complete register of forest loss. The different remote raster products
also differ in methods and observation times. Output is descriptive only.
"""
from __future__ import annotations
import argparse
import json
import math
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import rasterize, geometry_mask
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from shapely.geometry import shape, mapping
from shapely.ops import transform as geom_transform
from pyproj import Transformer

BASE="https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSkogsbruk/MapServer/6/query"
FIELDS="OBJECTID,Kommunnr,Arendear,Avvdatum,Avverktyp,Kalladatum,Arealha"

def request(params,timeout=45):
    data=urllib.parse.urlencode(params).encode("utf-8")
    req=urllib.request.Request(BASE,data=data,headers={"User-Agent":"Lulea-statistik-biomass-quality-analysis/1.0","Accept":"application/json"})
    last=None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=timeout) as resp:
                item=json.load(resp)
            if "error" in item:
                raise ValueError("Skogsstyrelsen REST error: "+str(item["error"])[:450])
            return item
        except (OSError,ValueError) as ex:
            last=ex
            if attempt<2: time.sleep(2*(attempt+1))
    raise RuntimeError(f"Skogsstyrelsen service unavailable: {last}")

def date_year(value):
    if value is None or value=="":
        return None
    if isinstance(value,(int,float)):
        try: return datetime.fromtimestamp(value/1000,timezone.utc).year
        except (ValueError,OverflowError): return None
    try: return int(str(value)[:4])
    except ValueError: return None

def read_harvest(boundary_3006):
    query={"where":"Kommunnr = '2580'","returnIdsOnly":"true","f":"json"}
    response=request(query)
    ids=response.get("objectIds")
    if not isinstance(ids,list):
        raise RuntimeError("No objectIds returned; cannot establish complete harvesting coverage")
    ids=sorted(set(ids))
    polygons={"2011_2015":[],"2016_2018":[]}
    records=defaultdict(int)
    non_geo=0
    transformer=Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True)
    for offset in range(0,len(ids),150):
        group=ids[offset:offset+150]
        resp=request({"objectIds":",".join(map(str,group)),"outFields":FIELDS,
                      "returnGeometry":"true","outSR":"4326","f":"geoJSON"},timeout=65)
        features=resp.get("features")
        if not isinstance(features,list):
            raise ValueError("Expected GeoJSON features from Skogsstyrelsen REST API")
        for feature in features:
            props=feature.get("properties",{})
            if str(props.get("Kommunnr",""))!="2580":
                continue
            year=date_year(props.get("Avvdatum"))
            if year is None:
                records["missing_avverkning_date"]+=1
                continue
            if year<2011 or year>2018:
                records["outside_2011_2018"]+=1
                continue
            geom=feature.get("geometry")
            if not geom:
                non_geo+=1
                continue
            g=geom_transform(transformer.transform,shape(geom))
            if g.is_empty or not g.is_valid:
                non_geo+=1
                continue
            g=g.intersection(boundary_3006)
            if g.is_empty:
                records["outside_work_boundary"]+=1
                continue
            if not g.is_valid:
                raise ValueError("Invalid intersected polygon; do not silently repair topology")
            period="2011_2015" if year<=2015 else "2016_2018"
            polygons[period].append(g)
            records[period+"_records"]+=1
        if len(features)!=len(group):
            raise ValueError(f"Pagination count mismatch: requested {len(group)}, returned {len(features)}")
    records["municipality_object_ids_total"]=len(ids)
    records["non_geometric_or_invalid"]=non_geo
    return polygons,dict(records)

def run(args):
    boundary=json.loads(args.boundary.read_text(encoding="utf-8"))
    if boundary.get("type")!="FeatureCollection" or len(boundary.get("features",[]))!=1:
        raise ValueError("Expected one GeoJSON boundary feature; source EPSG:4326")
    raw=shape(boundary["features"][0]["geometry"])
    if raw.is_empty or not raw.is_valid:
        raise ValueError("Invalid project boundary")
    to_3006=Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True)
    bound=geom_transform(to_3006.transform,raw)
    harvest,metadata=read_harvest(bound)
    if not harvest["2011_2015"] and not harvest["2016_2018"]:
        raise ValueError("No dated harvested polygons for 2011-2018; cannot test harvest hypothesis")
    step=25.0
    xmin,ymin,xmax,ymax=bound.bounds
    xmin=math.floor(xmin/step)*step; ymin=math.floor(ymin/step)*step
    xmax=math.ceil(xmax/step)*step; ymax=math.ceil(ymax/step)*step
    width=round((xmax-xmin)/step);height=round((ymax-ymin)/step)
    if width*height>40_000_000:
        raise ValueError("Unexpected grid extent")
    affine=Affine(step,0,xmin,0,-step,ymax)
    paths={year:args.directory/("lulea_biomass_"+year+"_source_crs_clip.tif") for year in ("2010","2015","2018")}
    classes={"not_recorded":0,"harvest_2011_2015":1,"harvest_2016_2018":2,"both_periods":3}
    aggregates={key:defaultdict(float) for key in classes}
    with rasterio.open(paths["2010"]) as r0, rasterio.open(paths["2015"]) as r15, rasterio.open(paths["2018"]) as r18:
        from fetch_and_compare_biomass_native import matches_expected_crs
        for year,src in [("2010",r0),("2015",r15),("2018",r18)]:
            if not matches_expected_crs(src.crs,3021 if year=="2010" else 3006):
                raise ValueError("Unverified raster CRS: "+year)
            if src.nodata is None: raise ValueError("NoData missing: "+year)
        with WarpedVRT(r0,crs="EPSG:3006",transform=affine,width=width,height=height,
                       resampling=Resampling.average,src_nodata=r0.nodata,nodata=-9999,dtype="float32") as v0,\
             WarpedVRT(r15,crs="EPSG:3006",transform=affine,width=width,height=height,
                       resampling=Resampling.average,src_nodata=r15.nodata,nodata=-9999,dtype="float32") as v15,\
             WarpedVRT(r18,crs="EPSG:3006",transform=affine,width=width,height=height,
                       resampling=Resampling.average,src_nodata=r18.nodata,nodata=-9999,dtype="float32") as v18:
            for rr in range(0,height,256):
                for cc in range(0,width,256):
                    win=Window(cc,rr,min(256,width-cc),min(256,height-rr))
                    t=rasterio.windows.transform(win,affine)
                    wh=(int(win.height),int(win.width))
                    inside=geometry_mask([mapping(bound)],out_shape=wh,transform=t,invert=True)
                    if not inside.any():continue
                    rasters=[]
                    for vrt in (v0,v15,v18):
                        d=vrt.read(1,window=win,masked=True)
                        rasters.append(np.ma.asarray(d,dtype="float64").filled(np.nan))
                    joint=inside
                    for arr in rasters: joint=joint & np.isfinite(arr) & (arr>=0)
                    if not joint.any():continue
                    # Rasterize overlaps as two bit flags. Explicitly retain both-period class.
                    flags=np.zeros(wh,dtype=np.uint8)
                    for key,bit in [("2011_2015",1),("2016_2018",2)]:
                        from rasterio.features import rasterize
                        window_bbox=rasterio.windows.bounds(win,affine)
                        from shapely.geometry import box as make_box
                        b=make_box(*window_bbox)
                        polys=[g for g in harvest[key] if g.intersects(b)]
                        if polys:
                            mask=rasterize(((mapping(g),1) for g in polys),
                                           out_shape=wh,transform=t,fill=0,dtype=np.uint8)
                            flags |= mask*bit
                    for label,flag in classes.items():
                        selected=joint & (flags==flag)
                        n=int(selected.sum())
                        if n==0:continue
                        bucket=aggregates[label]
                        bucket["cells"]+=n
                        for yr,arr in zip(("2010","2015","2018"),rasters):
                            bucket["sum_"+yr]+=float(arr[selected].sum(dtype="float64"))
                        bucket["count_2010_gt_2015"]+=int(np.count_nonzero(rasters[0][selected]>rasters[1][selected]))
                        bucket["count_2010_gt_2018"]+=int(np.count_nonzero(rasters[0][selected]>rasters[2][selected]))
    diagnostics={}
    for label,bucket in aggregates.items():
        n=int(bucket["cells"])
        if not n:
            diagnostics[label]={"common_valid_cells":0};continue
        means={yr:bucket["sum_"+yr]/n for yr in ("2010","2015","2018")}
        diagnostics[label]={
            "common_valid_cells":n,"area_ha":n*0.0625,
            "mean_raw_by_year":means,
            "mean_raw_2010_minus_2015":means["2010"]-means["2015"],
            "mean_raw_2010_minus_2018":means["2010"]-means["2018"],
            "share_cells_2010_gt_2015":bucket["count_2010_gt_2015"]/n,
            "share_cells_2010_gt_2018":bucket["count_2010_gt_2018"]/n,
        }
    result={
      "generated_utc":datetime.now(timezone.utc).isoformat(),
      "status":"descriptive_only_no_causal_inference",
      "harvest_layer_rest":BASE,"harvest_source_crs":"EPSG:3006",
      "harvest_geojson_query_crs":"EPSG:4326 (requested outSR=4326; transformed to EPSG:3006)",
      "working_polygon_crs":"EPSG:4326 (project boundary); transformed to EPSG:3006",
      "comparison_grid_crs":"EPSG:3006","grid_resolution_m":25,
      "query_filter":"Kommunnr='2580', Avvdatum in 2011-2018; Arendear NOT substituted",
      "harvest_feature_counts":metadata,
      "strata":diagnostics,
      "limitations":[
        "Skogsstyrelsens detected harvest polygons are an incomplete guiding dataset, not a complete harvest register",
        "Unnotified harvests and harvests smaller than 0.5 ha are not represented",
        "Remote service geometry and date attributes must be quality checked; missing dated records excluded",
        "Harvests between a specific raster's actual observation dates are unknown, years are proxies",
        "Pixels outside recorded harvest polygons are not necessarily unharvested",
        "No independent forest land mask applied; source product methodology and units not fully harmonized",
        "Rasters are source-CRS excerpts but fully warped to EPSG:3006 for cell-level overlay",
        "Only records from municipality code 2580 and project working boundary are included"
      ],
      "no_source_data_modified":True
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--directory",type=Path,default=Path("release-assets"))
    parser.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    parser.add_argument("--output",type=Path,default=Path("metadata/biomass_harvest_overlay_2011_2018.json"))
    run(parser.parse_args())
