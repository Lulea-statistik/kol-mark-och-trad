#!/usr/bin/env python3
"""Check recorded harvests in NMD2018 BASE codes 118/128 against volume 2010.

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
    # The provider's Kommunnr attribute filter can return null objectIds for
    # Lulea even when spatially intersecting polygons exist. Use the actual
    # project boundary bbox in source EPSG:3006 and check each geometry later.
    xmin,ymin,xmax,ymax=boundary_3006.bounds
    envelope=json.dumps({"xmin":xmin,"ymin":ymin,"xmax":xmax,"ymax":ymax,
                         "spatialReference":{"wkid":3006}})
    query={"where":"1=1","geometry":envelope,
           "geometryType":"esriGeometryEnvelope","inSR":"3006",
           "spatialRel":"esriSpatialRelIntersects",
           "returnIdsOnly":"true","f":"json"}
    response=request(query)
    ids=response.get("objectIds")
    if not isinstance(ids,list):
        raise RuntimeError("No objectIds in geographic query response; service response keys: "+str(sorted(response)))
    ids=sorted(set(ids))
    if len(ids)>200_000:
        raise ValueError(f"Unexpected number of candidate features: {len(ids)}")
    polygons={"2011_2015":[],"2016_2018":[]}
    records=defaultdict(int)
    records["sample_municipality_codes"]=[]
    records["sample_dates"]=[]
    non_geo=0
    other_municipality=0
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
            # The work boundary, not the provider's optional municipality code,
            # determines whether a polygon belongs to the analysis area.
            # Inspect metadata but never discard a geographically overlapping
            # polygon because Kommunnr uses a different coding convention.
            municipality=str(props.get("Kommunnr","")).strip()
            if municipality!="2580":
                other_municipality+=1
                if len(records.get("sample_municipality_codes",[]))<8 and municipality not in records.get("sample_municipality_codes",[]):
                    records.setdefault("sample_municipality_codes",[]).append(municipality)
            year=date_year(props.get("Avvdatum"))
            records["returned_geojson_features"]+=1
            if len(records["sample_dates"])<8:
                records["sample_dates"].append({"Avvdatum":str(props.get("Avvdatum"))[:32],"Arendear":str(props.get("Arendear"))[:12],"Kommunnr":municipality})
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
    records["spatial_candidate_ids"]=len(ids)
    records["other_municipality_attribute"]=other_municipality
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
        raise ValueError("No dated harvested polygons for 2011-2018; diagnostic counts: "+json.dumps(metadata,ensure_ascii=False))
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
    focus_aggregates={key:defaultdict(float) for key in classes}
    focus_aggregates_all=defaultdict(float)
    high_totals={key:defaultdict(float) for key in classes}
    low_totals={key:defaultdict(float) for key in classes}
    missing_volume=0
    with rasterio.open(paths["2010"]) as r0, rasterio.open(paths["2015"]) as r15, rasterio.open(paths["2018"]) as r18, rasterio.open(args.nmd) as nmd, rasterio.open(args.volume_2010) as volume:
        from fetch_and_compare_biomass_native import matches_expected_crs
        for year,src in [("2010",r0),("2015",r15),("2018",r18)]:
            if not matches_expected_crs(src.crs,3021 if year=="2010" else 3006):
                raise ValueError("Unverified raster CRS: "+year)
            if src.nodata is None: raise ValueError("NoData missing: "+year)
        if not nmd.crs or nmd.crs.to_epsg()!=3006 or nmd.count!=1 or any(abs(abs(x)-10)>.01 for x in nmd.res):
            raise ValueError("Unexpected NMD original CRS/band/resolution")
        if nmd.nodata in (118,128):raise ValueError("NMD NoData overlaps class zero")
        if not matches_expected_crs(volume.crs,3021) or volume.count!=1 or volume.nodata is None:
            raise ValueError("Unexpected volume 2010 CRS/band/NoData")
        if any(abs(abs(x)-25)>.05 for x in volume.res):
            raise ValueError("Unexpected original 2010 volume resolution")
        with WarpedVRT(nmd,crs="EPSG:3006",transform=affine,width=width,height=height,
                       resampling=Resampling.nearest,src_nodata=nmd.nodata,nodata=255,dtype="uint8") as nmdvrt,\
             WarpedVRT(volume,crs="EPSG:3006",transform=affine,width=width,height=height,
                       resampling=Resampling.average,src_nodata=volume.nodata,nodata=-9999,dtype="float32") as volumevrt,\
             WarpedVRT(r0,crs="EPSG:3006",transform=affine,width=width,height=height,
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
                    nmd_data=nmdvrt.read(1,window=win,masked=True)
                    volume_data=volumevrt.read(1,window=win,masked=True)
                    volume_values=np.ma.asarray(volume_data,dtype="float64").filled(np.nan)
                    focus=joint & (~np.ma.getmaskarray(nmd_data)) & np.isin(nmd_data.data,(118,128))
                    high=focus & np.isfinite(volume_values) & (volume_values>=100)
                    low=focus & np.isfinite(volume_values) & (volume_values>=0) & (volume_values<100)
                    missing_volume+=int((focus & ~np.isfinite(volume_values)).sum())
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
                        selected_focus=focus & (flags==flag)
                        nf=int(selected_focus.sum())
                        focus_bucket=focus_aggregates[label]
                        focus_bucket["cells"]+=nf
                        focus_aggregates_all["cells"]+=nf
                        for subset,out in ((high,high_totals),(low,low_totals)):
                            subset_flags=subset & (flags==flag)
                            out[label]["cells"]+=int(subset_flags.sum())
                            for yr,arr in zip(("2010","2015","2018"),rasters):
                                out[label]["sum_"+yr]+=float(arr[subset_flags].sum(dtype="float64"))
                        for yr,arr in zip(("2010","2015","2018"),rasters):
                            focus_bucket["sum_"+yr]+=float(arr[selected_focus].sum(dtype="float64"))
                            focus_aggregates_all["sum_"+yr]+=float(arr[selected_focus].sum(dtype="float64"))
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
    focussed={}
    for label,b in focus_aggregates.items():
        n=int(b["cells"])
        mean={year:(b["sum_"+year]/n if n else None) for year in ("2010","2015","2018")}
        focussed[label]={"cells":n,"area_ha":n*.0625,"biomass_mean_raw":mean,
          "raw_sum_difference_2010_minus_2015":b["sum_2010"]-b["sum_2015"],
          "raw_sum_difference_2010_minus_2018":b["sum_2010"]-b["sum_2018"]}
    nfocus=int(focus_aggregates_all["cells"])
    if nfocus!=469240:
        raise ValueError(f"PR101 population differs: {nfocus} != 469240")
    high_count=int(sum(x["cells"] for x in high_totals.values()))
    low_count=int(sum(x["cells"] for x in low_totals.values()))
    if high_count!=119269:
        raise ValueError(f"PR101 high volume count differs: {high_count}")
    if high_count+low_count+missing_volume!=nfocus:
        raise ValueError("Volume categories do not partition temporary nonforest")
    raw_diff=focus_aggregates_all["sum_2010"]-focus_aggregates_all["sum_2018"]
    if not math.isclose(raw_diff,10430209.959174048,rel_tol=1e-7):
        raise ValueError("PR101 biomass-delta mismatch")
    def strata(mapping):
        return {k:{"cells":int(v["cells"]),"area_ha":int(v["cells"])*.0625,
                   "sum_raw":{y:v["sum_"+y] for y in ("2010","2015","2018")},
                   "delta_2010_2018":v["sum_2010"]-v["sum_2018"]}
                for k,v in mapping.items()}
    high_stats=strata(high_totals)
    low_stats=strata(low_totals)
    high_diff=sum(x["delta_2010_2018"] for x in high_stats.values())
    recorded_high_diff=sum(x["delta_2010_2018"] for k,x in high_stats.items() if k!="not_recorded")
    if sum(x["cells"] for x in focussed.values())!=nfocus:
        raise AssertionError("Harvest classes fail to partition focus population")
    result={
      "focus":"NMD2018 BASE 118/128 temporarily not forest on shared 2010/2015/2018 biomass cells",
      "nmd_base_codes":[118,128],
      "high_volume_2010_ge100_cells":high_count,
      "high_volume_harvest_periods":high_stats,
      "low_volume_2010_lt100_cells":low_count,
      "low_volume_harvest_periods":low_stats,
      "raw_delta_2010_2018":raw_diff,
      "high_volume_raw_delta_2010_2018":high_diff,
      "high_volume_recorded_harvest_cell_share":(high_count-high_stats["not_recorded"]["cells"])/high_count,
      "high_volume_recorded_harvest_delta_share":recorded_high_diff/high_diff if high_diff else None,
      "focus_cells":nfocus,"focus_area_ha":nfocus*.0625,
      "focus_harvest_periods":focussed,
      "focus_unmatched_2010_volume_cells":missing_volume,
      "focus_share_harvest_2011_2018":(nfocus-focussed["not_recorded"]["cells"])/nfocus,
      "focus_share_of_2010_2018_raw_difference_in_recorded_harvest_cells":(
          sum(b["raw_sum_difference_2010_minus_2018"] for k,b in focussed.items() if k!="not_recorded")/
          (focus_aggregates_all["sum_2010"]-focus_aggregates_all["sum_2018"])
          if focus_aggregates_all["sum_2010"]!=focus_aggregates_all["sum_2018"] else None),
      "generated_utc":datetime.now(timezone.utc).isoformat(),
      "status":"descriptive_only_no_causal_inference",
      "harvest_layer_rest":BASE,"harvest_source_crs":"EPSG:3006",
      "harvest_geojson_query_crs":"EPSG:4326 (requested outSR=4326; transformed to EPSG:3006)",
      "working_polygon_crs":"EPSG:4326 (project boundary); transformed to EPSG:3006",
      "comparison_grid_crs":"EPSG:3006","grid_resolution_m":25,
      "query_filter":"Spatial bbox EPSG:3006, intersect actual Lulea working boundary, then Avvdatum 2011-2018; Kommunnr diagnostic only; Arendear NOT substituted",
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
        "Spatial intersection with Lulea boundary controls inclusion; Kommunnr is an attribute diagnostic only"
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
    parser.add_argument("--nmd",type=Path,required=True,help="Original NMD2018 BASE raster, EPSG:3006 10m")
    parser.add_argument("--volume-2010",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=Path("metadata/nmd2018_temporary_not_forest_harvest_2011_2018.json"))
    run(parser.parse_args())
