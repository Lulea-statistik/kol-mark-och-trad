#!/usr/bin/env python3
"""Reverse fixed-mask biomass comparison: modelled 2010 forest proxy -> 2018.

Do not mislabel modelled 2010 volume as an observed 2010 forest landcover map.
Joint 2010/15/18-valid 25m cells are compared as in PR99; NMD2018 forest
retained solely to cross-tab historical proxy vs 2018 forest/nonforest.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from shapely.geometry import shape, mapping
from shapely.ops import transform as transform_geom
from fetch_and_compare_biomass_native import matches_expected_crs

YEARS=("2010","2015","2018")
FOREST=set(range(111,118))|set(range(121,128))
THRESHOLDS=(0,10,50,100)
def new():
    return {"cells":0,"sums":{y:0.0 for y in YEARS},"zero_biomass":{y:0 for y in YEARS}}
def aggregate(dst,biom,selected):
    n=int(selected.sum())
    if not n:return
    dst["cells"]+=n
    for y in YEARS:
        a=biom[y][selected]
        dst["sums"][y]+=float(a.sum(dtype="float64"))
        dst["zero_biomass"][y]+=int(np.count_nonzero(a==0))
def finish(d):
    n=d["cells"]
    return {"cells":n,"area_ha":n*.0625,"raw_sum":d["sums"],
        "mean_raw":{y:(d["sums"][y]/n if n else None) for y in YEARS},
        "modelled_tonnes_dry_matter_by_year":{y:d["sums"][y]*.0625 for y in YEARS},
        "mass_unit_basis":"2010 source-producer confirmed tTS/ha for exact BIOMASS_XX_P_10.tif; 2015/2018 documented tTS/ha; year-to-year compartment/model equivalence NOT verified",
        "verified_cross_year_physical_change_percent":None,
        "delta_2010_minus_2018_raw":d["sums"]["2010"]-d["sums"]["2018"],
        "percent_2018_change_vs_2010_raw":(100*(d["sums"]["2018"]/d["sums"]["2010"]-1)
             if d["sums"]["2010"] else None),
        "zero_biomass_cells":d["zero_biomass"]}
def run(args):
    geo=json.loads(args.boundary.read_text(encoding="utf-8"))
    if geo.get("type")!="FeatureCollection" or len(geo.get("features",[]))!=1:
        raise ValueError("Expected project EPSG4326 boundary feature")
    boundary=shape(geo["features"][0]["geometry"])
    if boundary.is_empty or not boundary.is_valid:raise ValueError("Invalid work boundary")
    geom=transform_geom(Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,boundary)
    if geom.is_empty or not geom.is_valid:raise ValueError("Invalid EPSG3006 project boundary")
    unit=25
    a,b,c,d=geom.bounds
    left=math.floor(a/unit)*unit; bottom=math.floor(b/unit)*unit
    right=math.ceil(c/unit)*unit; top=math.ceil(d/unit)*unit
    width=round((right-left)/unit);height=round((top-bottom)/unit)
    if width*height>40000000:raise ValueError("Unreasonable raster grid size")
    transform=Affine(unit,0,left,0,-unit,top)
    all_cells=new()
    volume_valid=new()
    original_forest=new()
    thresholds={str(t):{"all":new(),"forest_2018":new(),"not_forest_2018":new(),
                         "temporary_nonforest_2018":new(),"water_2018":new()} for t in THRESHOLDS}
    volbins={name:new() for name in ("zero","0_to_10","10_to_50","50_to_100","100_plus","missing")}
    with ExitStack() as st:
        biom={}
        for y in YEARS:
            src=st.enter_context(rasterio.open(getattr(args,"biomass_"+y)))
            epsg,res=(3021,25) if y=="2010" else ((3006,12.5) if y=="2015" else (3006,10))
            if not matches_expected_crs(src.crs,epsg) or src.count!=1 or src.nodata is None or any(abs(abs(x)-res)>.05 for x in src.res):
                raise ValueError("Invalid source raster "+y)
            biom[y]=st.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=transform,width=width,
                height=height,resampling=Resampling.average,src_nodata=src.nodata,nodata=-9999,dtype="float32"))
        volume_source=st.enter_context(rasterio.open(args.volume_2010))
        if not matches_expected_crs(volume_source.crs,3021) or volume_source.count!=1 or volume_source.nodata is None or any(abs(abs(x)-25)>.05 for x in volume_source.res):
            raise ValueError("Invalid original 2010 volume source")
        volume=st.enter_context(WarpedVRT(volume_source,crs="EPSG:3006",transform=transform,width=width,
             height=height,resampling=Resampling.average,src_nodata=volume_source.nodata,nodata=-9999,dtype="float32"))
        nmd_source=st.enter_context(rasterio.open(args.nmd))
        if not matches_expected_crs(nmd_source.crs,3006) or nmd_source.count!=1 or any(abs(abs(x)-10)>.05 for x in nmd_source.res):
            raise ValueError("Invalid NMD2018 base source")
        nmd=st.enter_context(WarpedVRT(nmd_source,crs="EPSG:3006",transform=transform,width=width,
             height=height,resampling=Resampling.nearest,src_nodata=nmd_source.nodata,nodata=255,dtype="uint8"))
        for row in range(0,height,256):
            for col in range(0,width,256):
                win=Window(col,row,min(256,width-col),min(256,height-row))
                inside=geometry_mask([mapping(geom)],out_shape=(int(win.height),int(win.width)),
                    transform=rasterio.windows.transform(win,transform),invert=True,all_touched=False)
                if not inside.any():continue
                raw={y:np.ma.asarray(biom[y].read(1,window=win,masked=True),
                           dtype="float64").filled(np.nan) for y in YEARS}
                vv=np.ma.asarray(volume.read(1,window=win,masked=True),dtype="float64").filled(np.nan)
                nn=nmd.read(1,window=win,masked=True)
                joint=inside.copy()
                for y in YEARS:joint &= np.isfinite(raw[y])&(raw[y]>=0)
                joint &= ~np.ma.getmaskarray(nn)&(nn.data!=255)
                if not joint.any():continue
                aggregate(all_cells,raw,joint)
                vgood=np.isfinite(vv)&(vv>=0)
                jointvolume=joint&vgood
                aggregate(volume_valid,raw,jointvolume)
                nforest=joint & np.isin(nn.data,list(FOREST))
                aggregate(original_forest,raw,nforest)
                groups={
                    "zero":jointvolume&(vv==0),
                    "0_to_10":jointvolume&(vv>0)&(vv<10),
                    "10_to_50":jointvolume&(vv>=10)&(vv<50),
                    "50_to_100":jointvolume&(vv>=50)&(vv<100),
                    "100_plus":jointvolume&(vv>=100),
                    "missing":joint&(~vgood)}
                for name,mask in groups.items():aggregate(volbins[name],raw,mask)
                for t,rows in thresholds.items():
                    threshold=float(t)
                    proxy=jointvolume&((vv>0) if threshold==0 else (vv>=threshold))
                    aggregate(rows["all"],raw,proxy)
                    aggregate(rows["forest_2018"],raw,proxy&nforest)
                    aggregate(rows["not_forest_2018"],raw,proxy&(~nforest))
                    aggregate(rows["temporary_nonforest_2018"],raw,proxy&np.isin(nn.data,(118,128)))
                    aggregate(rows["water_2018"],raw,proxy&np.isin(nn.data,(61,62)))
    overall=finish(all_cells)
    if overall["cells"]!=2456410:
        raise ValueError("PR99 same-pixel shared population drift "+str(overall["cells"]))
    original=finish(original_forest)
    if original["cells"]!=1705502:raise ValueError("PR99 NMD2018-forest reference drift")
    result={"status":"2010_MODELED_VOLUME_MASK_RAW_ONLY_NOT_HISTORICAL_FOREST_CLASS",
      "created_utc":datetime.now(timezone.utc).isoformat(),
      "source_definition":"SLU Skogskarta 2010 estimated wood volume (EPSG3021 25m), not measured forest-cover map",
      "mask_reference_year":2010,"temporal_target_year":2018,
      "analysis_crs":"EPSG:3006","grid_resolution_m":25,
      "common_valid_raster_rule":"same biomass-positive-or-zero/non-nodata cells 2010,2015,2018 and valid NMD2018",
      "all_common":overall,"with_valid_2010_volume":finish(volume_valid),
      "original_2018_NMD_forest_mask":original,
      "2010_volume_bands":{name:finish(v) for name,v in volbins.items()},
      "2010_modeled_volume_proxy_thresholds":{
          t:{name:finish(val) for name,val in data.items()} for t,data in thresholds.items()},
      "physical_biomass_tonnes_2010":"available per exact 25m common mask in modelled_tonnes_dry_matter_by_year; NOT a municipality stock",
      "year_to_year_physical_comparability_verified":False,
      "limitations":[
       "A 2010 volume threshold is a historical MODEL proxy, not independent NMD2010 forest classification.",
       "The 2010 volume and biomass rasters are correlated modelling outputs and cannot independently validate one another.",
       "Proxy threshold >0 is inclusive of low possibly spurious volume values on roads, open land and water.",
       "2010 timber volume >=50 or >=100 is an operational mature forest-volume filter, NOT a comprehensive 2010 forest-land map; young/regenerating/low-volume forest can be missed.",
       "2018 NMD classes are used only for cross-tabulation, not to define reverse 2010 selection.",
       "Common valid biomass mask for all years means this analysis is not a municipality-wide 2010 forest stock.",
       "2010 physical unit tTS/ha and above-stump biomass confirmed by SLU on 2026-11-25; 2015 and 2018 also documented tTS/ha but model components and inclusion of leaves may not match.",
       "True biomass loss from forest harvest between 2010 and 2018 is preserved without corrections.",
       "Full raster grid CRS transformation applied before comparisons; missing values never converted to zero."
      ]}
    for t,g in result["2010_modeled_volume_proxy_thresholds"].items():
        if g["all"]["cells"]!=g["forest_2018"]["cells"]+g["not_forest_2018"]["cells"]:
            raise ValueError("Reverse mask does not partition into 2018 forest/nonforest for "+t)
        if not math.isclose(g["all"]["raw_sum"]["2010"],
            g["forest_2018"]["raw_sum"]["2010"]+g["not_forest_2018"]["raw_sum"]["2010"],rel_tol=1e-9):
            raise ValueError("Reverse mask sums do not reconcile for "+t)
    if sum(v["cells"] for v in result["2010_volume_bands"].values())!=overall["cells"]:
        raise ValueError("Volume bins and missing volume fail to partition common cells")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for y in YEARS:p.add_argument("--biomass-"+y,type=Path,required=True)
    p.add_argument("--volume-2010",type=Path,required=True)
    p.add_argument("--nmd",type=Path,required=True)
    p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    p.add_argument("--output",type=Path,default=Path("metadata/biomass_2010_reference_reverse_2018.json"))
    run(p.parse_args())
