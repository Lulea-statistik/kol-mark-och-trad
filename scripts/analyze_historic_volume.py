#!/usr/bin/env python3
"""Validate archive bytes and compare 2000/2005/2010 wood volume with 2010 biomass.

All cross-year values are descriptive until product definitions and physical
units are verified. Uses identical 25 m target cells in EPSG:3006 and
retains a common valid footprint for every displayed year.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from shapely.geometry import shape,mapping
from shapely.ops import transform as geom_transform
from pyproj import Transformer

from fetch_and_compare_biomass_native import matches_expected_crs

YEARS=("2000","2005","2010")
SOURCE_URLS={
    "2000":"https://gis.slu.se/data/slu_forest_map/2000/Data/Raster/Rt90/TOTALVOL_XX_P_00.tif",
    "2005":"https://gis.slu.se/data/slu_forest_map/2005/Data/Raster/Rt90/TOTALVOL_XX_P_05.tif",
    "2010":"https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/TOTALVOL_XX_P_10.tif",
}
def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda:src.read(8*1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def validate_archive(directory,boundary):
    result={}
    for year in YEARS:
        stem=f"lulea_total_volume_{year}"
        tif=directory/(stem+"_source_crs_clip.tif")
        meta_file=directory/(stem+"_provenance.json")
        checks_file=directory/(stem+"_SHA256SUMS.txt")
        for f in (tif,meta_file,checks_file):
            if not f.is_file() or f.stat().st_size==0:
                raise ValueError(f"{year}: missing asset {f}")
        entries={}
        for line in checks_file.read_text().splitlines():
            hash_val,file_name=line.strip().split(maxsplit=1)
            entries[file_name.strip()]=hash_val
        for f in (tif,meta_file):
            if entries.get(f.name)!=sha256(f):
                raise ValueError(f"{year}: SHA256 mismatch for {f.name}")
        m=json.loads(meta_file.read_text())
        if str(m.get("year"))!=year or m.get("source_url")!=SOURCE_URLS[year]:
            raise ValueError(f"{year}: wrong product or source URL")
        if m.get("boundary_sha256")!=sha256(boundary):
            raise ValueError(f"{year}: project boundary changed")
        if m.get("asset_sha256")!=sha256(tif) or m.get("asset_size_bytes")!=tif.stat().st_size:
            raise ValueError(f"{year}: provenance checksum or size mismatch")
        with rasterio.open(tif) as src:
            if src.count!=1 or not matches_expected_crs(src.crs,3021):
                raise ValueError(f"{year}: invalid CRS or band")
            if not all(math.isclose(abs(x),25,abs_tol=0.05) for x in src.res):
                raise ValueError(f"{year}: unexpected pixel resolution")
            if src.nodata!=-9999 or src.dtypes[0]!="float32":
                raise ValueError(f"{year}: unexpected raster type/nodata")
            if [src.width,src.height]!=m.get("crop_size_pixels"):
                raise ValueError(f"{year}: raster dimensions differ from provenance")
            valid=0
            for _,w in src.block_windows(1):
                arr=np.asarray(src.read(1,window=w,masked=True).compressed(),dtype="float64")
                if arr.size and (not np.isfinite(arr).all() or (arr<0).any()):
                    raise ValueError(f"{year}: invalid values")
                valid+=arr.size
            if valid!=m.get("valid_inside_polygon_pixels"):
                raise ValueError(f"{year}: valid pixel count mismatch")
        result[year]={"file":tif.name,"sha256":sha256(tif),"valid_native_cells":valid,
                      "source_epsg":3021,"resolution_m":25}
    return result

def run(args):
    boundary_doc=json.loads(args.boundary.read_text())
    if boundary_doc.get("type")!="FeatureCollection" or len(boundary_doc.get("features",[]))!=1:
        raise ValueError("Expected one project boundary in GeoJSON EPSG:4326")
    geom=shape(boundary_doc["features"][0]["geometry"])
    if geom.is_empty or not geom.is_valid:
        raise ValueError("Invalid project boundary")
    archives=validate_archive(args.directory,args.boundary)
    biomass= args.biomass_directory/"lulea_biomass_2010_source_crs_clip.tif"
    # The biomass release is independently checked by verify_biomass_release.py.
    if not biomass.is_file():
        raise ValueError("Biomass raster 2010 missing")
    geom_3006=geom_transform(Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,geom)
    step=25.0
    xmin,ymin,xmax,ymax=geom_3006.bounds
    xmin=math.floor(xmin/step)*step; ymin=math.floor(ymin/step)*step
    xmax=math.ceil(xmax/step)*step; ymax=math.ceil(ymax/step)*step
    width=round((xmax-xmin)/step);height=round((ymax-ymin)/step)
    if width*height>40_000_000: raise ValueError("Unexpected target grid size")
    target=Affine(step,0,xmin,0,-step,ymax)
    names=("2000","2005","2010","biomass_2010")
    accum={n:{"sum":0.0,"zero":0,"min":float("inf"),"max":float("-inf")} for n in names}
    pair={"positive_both_count":0,"volume_sum":0.0,"biomass_sum":0.0,
          "volume_sq":0.0,"biomass_sq":0.0,"product_sum":0.0,
          "ratio_sum":0.0,"ratio_min":float("inf"),"ratio_max":float("-inf")}
    n_common=0
    with ExitStack() as stack:
        v={}
        for name in names:
            path=biomass if name=="biomass_2010" else args.directory/f"lulea_total_volume_{name}_source_crs_clip.tif"
            src=stack.enter_context(rasterio.open(path))
            if not matches_expected_crs(src.crs,3021) or src.nodata!=-9999:
                raise ValueError("Unexpected source CRS or NoData for "+name)
            v[name]=stack.enter_context(WarpedVRT(
                src,crs="EPSG:3006",transform=target,width=width,height=height,
                resampling=Resampling.average,src_nodata=src.nodata,nodata=-9999,
                dtype="float32"))
        for r0 in range(0,height,256):
            for c0 in range(0,width,256):
                win=Window(c0,r0,min(256,width-c0),min(256,height-r0))
                shape_tile=(int(win.height),int(win.width))
                inside=geometry_mask([mapping(geom_3006)],out_shape=shape_tile,
                                     transform=rasterio.windows.transform(win,target),invert=True)
                if not inside.any():continue
                arr={name:np.ma.asarray(v[name].read(1,window=win,masked=True),dtype="float64").filled(np.nan)
                     for name in names}
                common=inside.copy()
                for a in arr.values():common &= np.isfinite(a)&(a>=0)
                count=int(common.sum())
                if count==0:continue
                n_common+=count
                for name in names:
                    values=arr[name][common]
                    accum[name]["sum"]+=float(values.sum(dtype="float64"))
                    accum[name]["zero"]+=int(np.count_nonzero(values==0))
                    accum[name]["min"]=min(accum[name]["min"],float(values.min()))
                    accum[name]["max"]=max(accum[name]["max"],float(values.max()))
                volume=arr["2010"][common];biom=arr["biomass_2010"][common]
                positive=(volume>0)&(biom>0)
                x=volume[positive];y=biom[positive]
                if x.size:
                    ratio=y/x
                    pair["positive_both_count"]+=int(x.size)
                    pair["volume_sum"]+=float(x.sum())
                    pair["biomass_sum"]+=float(y.sum())
                    pair["volume_sq"]+=float(np.dot(x,x))
                    pair["biomass_sq"]+=float(np.dot(y,y))
                    pair["product_sum"]+=float(np.dot(x,y))
                    pair["ratio_sum"]+=float(ratio.sum())
                    pair["ratio_min"]=min(pair["ratio_min"],float(ratio.min()))
                    pair["ratio_max"]=max(pair["ratio_max"],float(ratio.max()))
    if n_common==0 or pair["positive_both_count"]==0:
        raise ValueError("No jointly valid common cells with positive 2010 volume and biomass")
    n=pair["positive_both_count"]
    numerator=n*pair["product_sum"]-pair["volume_sum"]*pair["biomass_sum"]
    v1=n*pair["volume_sq"]-pair["volume_sum"]**2
    v2=n*pair["biomass_sq"]-pair["biomass_sum"]**2
    r=numerator/math.sqrt(v1*v2) if v1>0 and v2>0 else None
    result={
        "calculated_utc":datetime.now(timezone.utc).isoformat(),
        "status":"exploratory_raw_units_not_final_biomass",
        "source_archive":"total-wood-volume-lulea-2000-2010-v1",
        "archive_validation":archives,
        "comparison_crs":"EPSG:3006","grid_resolution_m":25,
        "common_valid_cells":n_common,"common_valid_area_ha":n_common*0.0625,
        "means_on_four_product_common_support":{
            name:{"mean_raw":accum[name]["sum"]/n_common,
                  "share_zero":accum[name]["zero"]/n_common,
                  "min_raw":accum[name]["min"],"max_raw":accum[name]["max"]}
            for name in names
        },
        "volume_trend_percent_on_common_support":{
            "2000_to_2005":(accum["2005"]["sum"]/accum["2000"]["sum"]-1)*100 if accum["2000"]["sum"] else None,
            "2005_to_2010":(accum["2010"]["sum"]/accum["2005"]["sum"]-1)*100 if accum["2005"]["sum"] else None,
            "2000_to_2010":(accum["2010"]["sum"]/accum["2000"]["sum"]-1)*100 if accum["2000"]["sum"] else None
        },
        "biomass_volume_2010_positive_pixels":{
            "n_pixels":n,"pearson_r_raw":r,
            "mean_of_per_cell_raw_ratios":pair["ratio_sum"]/n,
            "ratio_min":pair["ratio_min"],"ratio_max":pair["ratio_max"],
            "note":"Ratios are exploratory: no reliable conversion factor between timber volume and dry biomass is established"
        },
        "cautions":[
            "Raw values have not been validated as physically comparable across SLU source vintages",
            "No historical biomass for 2000/2005 has been synthesized",
            "This common support includes nonforest zero cells unless masked by independent land/forest classification",
            "A high correlation does not validate a biomass-to-volume conversion coefficient",
            "The source dates and forest model changes require independent product metadata validation"
        ]
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--directory",type=Path,default=Path("release-volume"))
    p.add_argument("--biomass-directory",type=Path,default=Path("release-biomass"))
    p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    p.add_argument("--output",type=Path,default=Path("metadata/volume_history_biomass_2010_comparison.json"))
    run(p.parse_args())
