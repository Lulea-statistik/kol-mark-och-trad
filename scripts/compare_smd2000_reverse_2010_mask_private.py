#!/usr/bin/env python3
"""Private-only SMD2000 validation of the 2010 volume-defined forest proxy.

SMD2000 generalised vector landcover is from circa 2000, NOT a direct 2010
forest observation. This program never publishes or exports SMD geometry,
individual cells or reconstructable spatial grids.
"""
from __future__ import annotations
import argparse, json, math, os
from collections import defaultdict, Counter
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import fiona, rasterio
from shapely.geometry import shape, mapping
from shapely.ops import transform as shape_transform
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from rasterio.features import geometry_mask, rasterize
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from rasterio.transform import Affine
from fetch_and_compare_biomass_native import matches_expected_crs

YEARS=("2010","2015","2018")
SMD_FOREST={40,41,43,44,45,46,47,48,49}
SMD_YOUNG={55}
SMD_CUT={54}
SMD_WATER={80,81,82,83,84,85,86}
NMD_FOREST=set(range(111,118))|set(range(121,128))
NMD_TEMP={118,128}
NMD_WATER={61,62}
GROUPS=("forest","young","clearcut","water","other","unclassified")
NMD_GROUPS=("forest_2018","temporary_nonforest_2018","water_2018","other_2018")
MASKS=("volume50_all","volume50_smd2000_forest","volume50_smd2000_forest_or_young",
       "volume50_smd2000_nonwater","volume100_smd2000_forest","smd2000_forest_all_volume")
def smd_group(code):
    if code in SMD_FOREST:return "forest"
    if code in SMD_YOUNG:return "young"
    if code in SMD_CUT:return "clearcut"
    if code in SMD_WATER:return "water"
    if code==0:return "unclassified"
    return "other"
def nmd_group(code):
    if code in NMD_FOREST:return "forest_2018"
    if code in NMD_TEMP:return "temporary_nonforest_2018"
    if code in NMD_WATER:return "water_2018"
    return "other_2018"
def new():
    return {"cells":0,"sum_raw":{y:0.0 for y in YEARS},
            "zeros":{y:0 for y in YEARS}}
def add(dst,m,values):
    n=int(m.sum())
    dst["cells"]+=n
    if n:
        for y in YEARS:
            a=values[y][m]
            dst["sum_raw"][y]+=float(a.sum(dtype="float64"))
            dst["zeros"][y]+=int(np.count_nonzero(a==0))
def finish(d):
    n=d["cells"]
    x=d["sum_raw"]
    return {"cells":n,"area_ha":n*.0625,"sum_raw":x,
        "mean_raw":{y:x[y]/n if n else None for y in YEARS},
        "change_percent_2010_to_2018_raw":100*(x["2018"]/x["2010"]-1) if x["2010"] else None,
        "zero_biomass_cells":d["zeros"]}
def check_sum(a,b):
    if a["cells"]!=sum(x["cells"] for x in b.values()):raise ValueError("Cell partition mismatch")
    for y in YEARS:
        if not math.isclose(a["sum_raw"][y],sum(x["sum_raw"][y] for x in b.values()),
                            rel_tol=1e-8,abs_tol=.01):
            raise ValueError("Sum partition mismatch "+y)
def load_smd(path,epsg,work_crs):
    with fiona.open(path) as src:
        if "GRIDCODE" not in src.schema["properties"]:raise ValueError("Missing SMD GRIDCODE")
        if src.crs_wkt or src.crs:
            crs=CRS.from_user_input(src.crs_wkt or src.crs)
            if epsg and not crs.equals(CRS.from_epsg(epsg),ignore_axis_order=True):
                raise ValueError("Supplied SMD EPSG contradicts source CRS")
        elif epsg:
            crs=CRS.from_epsg(epsg)
        else:raise ValueError("SMD source has no CRS: supply independently verified --smd-epsg")
        if not crs.equals(CRS.from_epsg(3006),ignore_axis_order=True) and not epsg and not (src.crs_wkt or src.crs):
            raise ValueError("Unverified SMD coordinates")
        transformer=Transformer.from_crs(crs,work_crs,always_xy=True)
        geometries=[]
        counts=Counter()
        for feat in src:
            if not feat["geometry"]:continue
            geom=shape(feat["geometry"])
            if geom.is_empty:continue
            if not geom.is_valid:raise ValueError("Invalid SMD polygon "+str(feat["id"]))
            code=int(feat["properties"]["GRIDCODE"])
            if code<0 or code>255:raise ValueError("Unexpected SMD code")
            transformed=shape_transform(transformer.transform,geom)
            if not transformed.is_valid:raise ValueError("Invalid transformed SMD polygon")
            geometries.append((mapping(transformed),code))
            counts[code]+=1
    if not geometries:raise ValueError("No SMD polygons")
    return geometries,crs.to_string(),dict(counts)
def run(args):
    if args.output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("Output must be OUTSIDE repository; licensed SMD cross-tabulations are PRIVATE")
    fc=json.loads(args.boundary.read_text(encoding="utf-8"))
    if fc.get("type")!="FeatureCollection" or len(fc.get("features",[]))!=1:
        raise ValueError("Invalid boundary GeoJSON")
    boundary=shape(fc["features"][0]["geometry"])
    if boundary.is_empty or not boundary.is_valid:raise ValueError("Invalid boundary")
    geom=shape_transform(Transformer.from_crs(4326,3006,always_xy=True).transform,boundary)
    minx,miny,maxx,maxy=geom.bounds
    xmin=math.floor(minx/25)*25
    ymin=math.floor(miny/25)*25
    xmax=math.ceil(maxx/25)*25
    ymax=math.ceil(maxy/25)*25
    width=round((xmax-xmin)/25);height=round((ymax-ymin)/25)
    if width*height>40000000:raise ValueError("Unreasonable analysis extent")
    tf=Affine(25,0,xmin,0,-25,ymax)
    smd_geoms,smd_crs,code_counts=load_smd(args.smd_shp,args.smd_epsg,CRS.from_epsg(3006))
    # SMD polygons must NEVER be exported or put in GitHub artifact.
    smd=rasterize(smd_geoms,out_shape=(height,width),transform=tf,
                  all_touched=False,fill=0,dtype="uint8")
    groups={name:new() for name in GROUPS}
    result={name:{"all":new(),"by_smd2000":{g:new() for g in GROUPS},
                   "by_nmd2018":{g:new() for g in NMD_GROUPS}} for name in MASKS}
    common=new()
    with ExitStack() as stack:
        bv={}
        for y in YEARS:
            src=stack.enter_context(rasterio.open(getattr(args,"biomass_"+y)))
            epsg,px=(3021,25) if y=="2010" else ((3006,12.5) if y=="2015" else (3006,10))
            if not matches_expected_crs(src.crs,epsg) or src.count!=1 or src.nodata is None or any(abs(abs(v)-px)>.05 for v in src.res):
                raise ValueError("Unverified biomass source "+y)
            bv[y]=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=tf,width=width,height=height,
                        src_nodata=src.nodata,nodata=-9999,resampling=Resampling.average,dtype="float32"))
        vsrc=stack.enter_context(rasterio.open(args.volume_2010))
        if not matches_expected_crs(vsrc.crs,3021) or vsrc.nodata is None or any(abs(abs(v)-25)>.05 for v in vsrc.res):
            raise ValueError("Unexpected 2010 volume raster")
        vol=stack.enter_context(WarpedVRT(vsrc,crs="EPSG:3006",transform=tf,width=width,height=height,
                        src_nodata=vsrc.nodata,nodata=-9999,resampling=Resampling.average,dtype="float32"))
        nsrc=stack.enter_context(rasterio.open(args.nmd))
        if not matches_expected_crs(nsrc.crs,3006) or nsrc.nodata is None or any(abs(abs(v)-10)>.05 for v in nsrc.res):
            raise ValueError("Unexpected 2018 NMD source")
        nmd=stack.enter_context(WarpedVRT(nsrc,crs="EPSG:3006",transform=tf,width=width,height=height,
                        src_nodata=nsrc.nodata,nodata=255,resampling=Resampling.nearest,dtype="uint8"))
        for rr in range(0,height,256):
            for cc in range(0,width,256):
                win=Window(cc,rr,min(256,width-cc),min(256,height-rr))
                ht,wt=int(win.height),int(win.width)
                inside=geometry_mask([mapping(geom)],out_shape=(ht,wt),
                  transform=rasterio.windows.transform(win,tf),invert=True)
                if not inside.any():continue
                values={y:np.ma.asarray(bv[y].read(1,window=win,masked=True),dtype="float64").filled(np.nan) for y in YEARS}
                v=np.ma.asarray(vol.read(1,window=win,masked=True),dtype="float64").filled(np.nan)
                c=nmd.read(1,window=win,masked=True)
                eligible=inside&(~np.ma.getmaskarray(c))&(c.data!=255)
                for y in YEARS:eligible &= np.isfinite(values[y])&(values[y]>=0)
                if not eligible.any():continue
                add(common,eligible,values)
                classes=smd[rr:rr+ht,cc:cc+wt]
                cvol=np.isfinite(v)&(v>=0)
                group_masks={name:(classes==0 if name=="unclassified" else
                         np.isin(classes,list(SMD_FOREST if name=="forest" else
                         SMD_YOUNG if name=="young" else SMD_CUT if name=="clearcut" else
                         SMD_WATER if name=="water" else
                         set(range(1,256))-SMD_FOREST-SMD_YOUNG-SMD_CUT-SMD_WATER)))
                         for name in GROUPS}
                for name,mask in group_masks.items():add(groups[name],eligible&mask,values)
                selections={
                   "volume50_all":eligible&cvol&(v>=50),
                   "volume50_smd2000_forest":eligible&cvol&(v>=50)&group_masks["forest"],
                   "volume50_smd2000_forest_or_young":eligible&cvol&(v>=50)&(group_masks["forest"]|group_masks["young"]),
                   "volume50_smd2000_nonwater":eligible&cvol&(v>=50)&(~group_masks["water"])&(~group_masks["unclassified"]),
                   "volume100_smd2000_forest":eligible&cvol&(v>=100)&group_masks["forest"],
                   "smd2000_forest_all_volume":eligible&group_masks["forest"]}
                ngroups={name:np.isin(c.data,list(NMD_FOREST if name=="forest_2018" else
                          NMD_TEMP if name=="temporary_nonforest_2018" else NMD_WATER if name=="water_2018"
                          else set(range(1,255))-NMD_FOREST-NMD_TEMP-NMD_WATER))
                         for name in NMD_GROUPS}
                for name,mask in selections.items():
                    entry=result[name]
                    add(entry["all"],mask,values)
                    for g,m in group_masks.items():add(entry["by_smd2000"][g],mask&m,values)
                    for g,m in ngroups.items():add(entry["by_nmd2018"][g],mask&m,values)
    full=finish(common)
    if full["cells"]!=2456410:raise ValueError("PR99 comparable area has changed")
    out={}
    for name,entry in result.items():
        x=finish(entry["all"])
        s={g:finish(v) for g,v in entry["by_smd2000"].items()}
        n={g:finish(v) for g,v in entry["by_nmd2018"].items()}
        check_sum(x,s);check_sum(x,n)
        out[name]={"all":x,"by_smd2000":s,"by_nmd2018":n}
    check_sum(full,{k:finish(v) for k,v in groups.items()})
    output={"status":"PRIVATE_SMD2000_SENSITIVITY_NOT_VERIFIED_2010_FOREST",
      "created_utc":datetime.now(timezone.utc).isoformat(),
      "source_smd_crs":smd_crs,"smd_reference_year":2000,
      "smd_polygon_counts":code_counts,
      "analysis_crs":"EPSG:3006","pixel_size_m":25,
      "baseline_common_valid":full,
      "smd2000_groups":{g:finish(x) for g,x in groups.items()},
      "proxy_masks":out,
      "biomass_2010_tonnes":None,
      "private_output":True,"publishable_without_license_review":False,
      "limits":[
        "Generalized SMD2000 vector based on circa 2000 observations; not an observed 2010 vegetation map",
        "Volume proxy is a 2010 model and has previously given nonzero values on water",
        "SMD polygons may differ among three locally supplied archives; primary EPSG3006 .prj version preferred",
        "Cannot infer logging from SMD2000-vs-NMD2018 class difference",
        "Raw 2010 biomass units and root components unverified; cannot claim physical percent change",
        "Only same common-valid 2010,2015,2018 grid is selected; outside not included",
        "No raster, polygons, coordinates or cell-level outputs may enter public GitHub"]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PRIVATE SMD2000 validation finished. Rows:",len(out),", output kept outside repository",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--smd-shp",type=Path,required=True)
    p.add_argument("--smd-epsg",type=int)
    for y in YEARS:p.add_argument("--biomass-"+y,type=Path,required=True)
    p.add_argument("--volume-2010",type=Path,required=True)
    p.add_argument("--nmd",type=Path,required=True)
    p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    p.add_argument("--output",type=Path,required=True,help="PRIVATE JSON outside public repo")
    run(p.parse_args())
