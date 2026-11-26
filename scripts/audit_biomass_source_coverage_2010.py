#!/usr/bin/env python3
"""Audit the effective raster-data masks and cross-year selection effects.

NMD2018 is a *later* land cover reference. Native NoData and effective
warped validity are not equivalent to a historical water/forest mask.
"""
from __future__ import annotations
import argparse
import json
import math
from collections import defaultdict
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from shapely.geometry import shape,mapping
from shapely.ops import transform as project_geom
from fetch_and_compare_biomass_native import matches_expected_crs

FOREST=set(range(111,118)) | set(range(121,128))
WATER={61,62}
RASTERS=("biomass_2010","volume_2010","biomass_2015","biomass_2018")
def group(code):
    if code in WATER:return "Water_NMD2018"
    if code in FOREST:return "Forest_NMD2018"
    return "Other_NMD2018"

def run(args):
    boundary=json.loads(args.boundary.read_text(encoding="utf-8"))
    if boundary.get("type")!="FeatureCollection" or len(boundary.get("features",[]))!=1:
        raise ValueError("Expected single EPSG:4326 polygon FeatureCollection")
    geom=shape(boundary["features"][0]["geometry"])
    if not geom.is_valid or geom.is_empty:raise ValueError("Invalid municipality boundary")
    geom=project_geom(Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,geom)
    step=25.
    left,bottom,right,top=geom.bounds
    left=math.floor(left/step)*step;right=math.ceil(right/step)*step
    bottom=math.floor(bottom/step)*step;top=math.ceil(top/step)*step
    width=int(round((right-left)/step));height=int(round((top-bottom)/step))
    if width*height>40000000:raise ValueError("Excessive target grid")
    transform=Affine(step,0,left,0,-step,top)
    source_meta={}
    grouped=defaultdict(lambda:defaultdict(int))
    classed=defaultdict(lambda:defaultdict(int))
    coverage_stats=defaultdict(lambda:defaultdict(int))
    with ExitStack() as stack:
        rasters={}
        for key in RASTERS:
            source=stack.enter_context(rasterio.open(getattr(args,key)))
            expected_crs=3021 if key in ("biomass_2010","volume_2010") else 3006
            expected_res=25 if key in ("biomass_2010","volume_2010") else (12.5 if key=="biomass_2015" else 10)
            if source.crs is None or not matches_expected_crs(source.crs,expected_crs) or source.count!=1:
                raise ValueError("Raster CRS/band mismatch: "+key)
            if abs(abs(source.res[0])-expected_res)>.1 or source.nodata is None:
                raise ValueError("Raster resolution/NoData mismatch: "+key)
            source_meta[key]={
                "crs_native":str(source.crs),"expected_epsg":expected_crs,
                "resolution_native_m":list(source.res),"nodata_native":str(source.nodata),
                "mask_flag_enums":[x.name for x in source.mask_flag_enums[0]],
                "native_width":source.width,"native_height":source.height,
                "original_bounds":list(source.bounds)}
            rasters[key]=stack.enter_context(WarpedVRT(source,crs="EPSG:3006",
                transform=transform,width=width,height=height,
                resampling=Resampling.average,src_nodata=source.nodata,
                nodata=-9999,dtype="float32"))
        nmd_source=stack.enter_context(rasterio.open(args.nmd))
        if nmd_source.crs is None or not matches_expected_crs(nmd_source.crs,3006) or nmd_source.count!=1:
            raise ValueError("NMD original CRS/band invalid")
        if any(abs(abs(r)-10)>.01 for r in nmd_source.res):
            raise ValueError("NMD source is not the expected 10m layer")
        nmd=stack.enter_context(WarpedVRT(nmd_source,crs="EPSG:3006",
            transform=transform,width=width,height=height,
            resampling=Resampling.nearest,src_nodata=nmd_source.nodata,
            nodata=255,dtype="uint8"))
        for y in range(0,height,256):
            for x in range(0,width,256):
                w=Window(x,y,min(256,width-x),min(256,height-y))
                inside=geometry_mask([mapping(geom)],out_shape=(int(w.height),int(w.width)),
                    transform=rasterio.windows.transform(w,transform),
                    invert=True,all_touched=False)
                if not inside.any():continue
                cls=nmd.read(1,window=w,masked=True)
                nmd_valid=inside & ~np.ma.getmaskarray(cls) & (cls.data!=255)
                coverage_stats["area"]["inside_municipality_grid_cells"]+=int(inside.sum())
                coverage_stats["area"]["nmd_valid_cells"]+=int(nmd_valid.sum())
                if not nmd_valid.any():continue
                arr={};valid={}
                for key in RASTERS:
                    m=rasters[key].read(1,window=w,masked=True)
                    arr[key]=m.data
                    valid[key]=~np.ma.getmaskarray(m) & np.isfinite(arr[key]) & (arr[key]>=0)
                maskcode=np.zeros_like(inside,dtype=np.uint8)
                for idx,key in enumerate(RASTERS):
                    maskcode |= valid[key].astype("uint8") << idx
                # maskcode bits: 1 biomass2010, 2 volume2010,
                #                4 biomass2015, 8 biomass2018.
                for code in np.unique(cls.data[nmd_valid]):
                    classified=nmd_valid & (cls.data==code)
                    g=group(int(code))
                    counts=np.bincount(maskcode[classified],minlength=16)
                    for signature,count in enumerate(counts):
                        if not count:continue
                        grouped[g]["pattern_"+format(signature,"04b")]+=int(count)
                        classed[str(int(code))]["pattern_"+format(signature,"04b")]+=int(count)
                    n=int(classified.sum())
                    grouped[g]["nmd_cells"]+=n
                    classed[str(int(code))]["nmd_cells"]+=n
                    # 1011: 2010 biomass and volume + 2018 biomass, but NoData 2015.
                    # 1111: all four valid. Distinguish positive biomass from zero.
                    for signature in (11,15):
                        chosen=classified & (maskcode==signature)
                        positive2010=chosen & (arr["biomass_2010"]>0)
                        positive2018=chosen & (arr["biomass_2018"]>0)
                        label="pattern_"+format(signature,"04b")
                        for stats in (grouped[g],classed[str(int(code))]):
                            stats[label+"_positive_2010_cells"]+=int(positive2010.sum())
                            stats[label+"_positive_2018_cells"]+=int(positive2018.sum())
                            stats[label+"_2010_tonnes_TS"]+=float(arr["biomass_2010"][chosen].sum(dtype="float64"))*.0625
                            stats[label+"_2018_tonnes_TS"]+=float(arr["biomass_2018"][chosen].sum(dtype="float64"))*.0625
                            if signature==15:
                                stats[label+"_2015_tonnes_TS"]+=float(arr["biomass_2015"][chosen].sum(dtype="float64"))*.0625

                    for key in RASTERS:
                        q=classified & valid[key]
                        v=int(q.sum())
                        grouped[g][key+"_valid"]+=v
                        classed[str(int(code))][key+"_valid"]+=v
                        z=int((q & (arr[key]==0)).sum())
                        grouped[g][key+"_valid_zero"]+=z
                        classed[str(int(code))][key+"_valid_zero"]+=z
                    # "Old sources both present" vs extra selection due 2015/18.
                    pair=classified & valid["biomass_2010"] & valid["volume_2010"]
                    all_years=pair & valid["biomass_2015"] & valid["biomass_2018"]
                    grouped[g]["both_2010_valid"]+=int(pair.sum())
                    grouped[g]["both_2010_and_later_valid"]+=int(all_years.sum())
                    classed[str(int(code))]["both_2010_valid"]+=int(pair.sum())
                    classed[str(int(code))]["both_2010_and_later_valid"]+=int(all_years.sum())
    for g,stats in grouped.items():
        stats["area_ha"]=stats["nmd_cells"]*.0625
        pair=stats["both_2010_valid"]
        stats["fraction_2010_pair_retained_by_joint_2015_2018"]=stats["both_2010_and_later_valid"]/pair if pair else None
    for key,stats in classed.items():
        stats["area_ha"]=stats["nmd_cells"]*.0625
    if sum(x["nmd_cells"] for x in grouped.values())!=coverage_stats["area"]["nmd_valid_cells"]:
        raise ValueError("NMD coverage mismatch")
    for g,stats in grouped.items():
        if sum(stats.get("pattern_"+format(i,"04b"),0) for i in range(16))!=stats["nmd_cells"]:
            raise ValueError("Mask signatures do not partition "+g)
    for signature in ("pattern_1011","pattern_1111"):
        for group,stats in grouped.items():
            selected=stats.get(signature,0)
            for year in ("2010","2018"):
                positive=stats.get(signature+"_positive_"+year+"_cells",0)
                if not 0<=positive<=selected:raise ValueError("Positive count invalid "+group+year)
                if stats.get(signature+"_"+year+"_tonnes_TS",0)<0:
                    raise ValueError("Negative biomass "+group+year)
        years=("2010","2015","2018") if signature=="pattern_1111" else ("2010","2018")
        for year in years:
            a=sum(v.get(signature+"_"+year+"_tonnes_TS",0) for v in classed.values())
            b=sum(v.get(signature+"_"+year+"_tonnes_TS",0) for v in grouped.values())
            if not math.isclose(a,b,rel_tol=1e-9,abs_tol=.01):
                raise ValueError("NMD2018 per-class biomass sum does not reconcile with group "+signature+year)
    missing2015=sum(v.get("pattern_1011",0) for v in grouped.values())
    positive2010=sum(v.get("pattern_1011_positive_2010_cells",0) for v in grouped.values())
    common=sum(v.get("pattern_1111",0) for v in grouped.values())
    out={"status":"EFFECTIVE_VALID_DATA_MASK_AUDIT_NOT_HISTORICAL_LANDCOVER",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "analysis_crs":"EPSG:3006","pixel_size_m":25,"source_files":source_meta,
        "mask_signature_bits":{"1":"biomass_2010","2":"volume_2010","4":"biomass_2015","8":"biomass_2018"},
        "area":dict(coverage_stats["area"]),
        "coverage_cohorts":{
          "all_three_years_valid_cells":common,
          "biomass_2010_and_2018_valid_biomass2015_nodata_cells":missing2015,
          "biomass2010_positive_2015_nodata_2018_valid_cells":positive2010,
          "biomass2010_positive_2015_nodata_2018_valid_area_ha":positive2010*.0625,
          "2015_nodata_cohort_area_ha":missing2015*.0625,
          "year_valid_cells":{year:sum(v.get("biomass_"+year+"_valid",0) for v in grouped.values()) for year in ("2010","2015","2018")},
          "landcover_reference_year":2018,
          "missing2015_signature":"1011"
        },
        "group_rows":dict(grouped),
        "class_rows":dict(classed),
        "method":"Native CRS and NoData checked for each original GeoTIFF. Raster values fully warped to common 25m EPSG:3006 grid. Mask comparisons use effective warped-validity, not a supplied 2010 land-use mask.",
        "limitations":[
         "NMD2018 is later than 2010: water categories do not prove 2010 water.",
         "Native NoData and effective warped data presence do not identify the historical semantic forest/water training mask.",
         "Warped average mixes source pixels and can create fringe validity. A source-pixel-native mask audit is needed before claiming an original source class.",
         "Only NMD-valid cells inside the municipal polygon are counted. Other water or invalid NMD cells are excluded.",
         "2010 pair selection is independent of 2015/2018; the latter years are only applied in the explicitly labelled shared-population subset.",
         "All biomass and volume comparisons are unharmonized raw data; zero values are tracked separately from NoData."
        ]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Mask coverage area",out["area"])
    print("Original source metadata",json.dumps(source_meta,ensure_ascii=False))
    print("Group coverage patterns",json.dumps(out["group_rows"],ensure_ascii=False))
    print("COVERAGE_COHORT_RESULTS",json.dumps(out["coverage_cohorts"],ensure_ascii=False))
    print("COVERAGE_PATTERN_1011_DETAILS",json.dumps({k:{
      "cells":v.get("pattern_1011",0),"positive_2010":v.get("pattern_1011_positive_2010_cells",0),
      "tonnes_2010":v.get("pattern_1011_2010_tonnes_TS",0),
      "tonnes_2018":v.get("pattern_1011_2018_tonnes_TS",0)
      } for k,v in grouped.items()},ensure_ascii=False))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in RASTERS:p.add_argument("--"+key.replace("_","-"),type=Path,required=True)
    p.add_argument("--nmd",type=Path,required=True)
    p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    p.add_argument("--output",type=Path,default=Path("metadata/biomass_source_coverage_2010.json"))
    run(p.parse_args())
