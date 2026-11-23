#!/usr/bin/env python3
"""Fetch only the municipal source-CRS windows of three biomass GeoTIFFs.

Never overwrite original raster files or website statistics. Fails visibly when
SLU remote rasters or georeferencing are unavailable. Writes diagnostic JSON.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds, transform as window_transform
from shapely.geometry import shape, mapping
from shapely.ops import transform as shape_transform
from pyproj import Transformer, CRS as PyprojCRS

ROOT = Path(__file__).resolve().parents[1]
LAYERS = {"2010":"biomass_2010","2015":"biomass_2015_leaf","2018":"biomass"}
EXPECTED = {"2010":(3021,25.0),"2015":(3006,12.5),"2018":(3006,10.0)}

def save_diagnostics(path, report):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def matches_expected_crs(source_crs, expected_epsg):
    """Check expected EPSG, also recognizing the top-level authority of legacy WKT1.

    WKT1 exported by some older SLU GeoTIFFs carries AUTHORITY["EPSG","3021"]
    at the outermost PROJCS level, although PROJ/pyproj may not report equality
    with the modern EPSG database definition. Never accept an unknown CRS.
    """
    if source_crs is None:
        return False
    try:
        if source_crs.to_epsg() == expected_epsg:
            return True
        wkt = source_crs.to_wkt()
        if PyprojCRS.from_user_input(wkt).equals(
            PyprojCRS.from_epsg(expected_epsg), ignore_axis_order=True
        ):
            return True
        # Last AUTHORITY/ID, immediately before the final CRS bracket,
        # identifies the outer PROJCS rather than a nested datum/ellipsoid.
        match = re.search(
            r'(?:AUTHORITY|ID)\s*\[\s*"EPSG"\s*,\s*"?([0-9]+)"?\s*\]\s*\]\s*
def crop_source(url, year, boundary, destination, report):
    # Passing /vsicurl explicitly can avoid GDAL attempts at full-file downloads.
    # A genuine range-enabled GeoTIFF is required for practical remote window reads.
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                      CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
                      GDAL_HTTP_MAX_RETRY="2",
                      GDAL_HTTP_RETRY_DELAY="2",
                      GDAL_HTTP_TIMEOUT="35"):
        with rasterio.open("/vsicurl/"+url) as src:
            expected_epsg, expected_res = EXPECTED[year]
            if not src.crs or not matches_expected_crs(src.crs, expected_epsg):
                raise ValueError(f"{year}: CRS {src.crs} differs from expected EPSG:{expected_epsg}")
            rx,ry=map(abs,src.res)
            if abs(rx-expected_res)>0.05 or abs(ry-expected_res)>0.05:
                raise ValueError(f"{year}: {src.res} m resolution differs from {expected_res} m")
            if src.nodata is None:
                raise ValueError(f"{year}: NoData undefined; cannot safely mask")
            if src.scales[0]!=1 or src.offsets[0]!=0:
                raise ValueError(f"{year}: nonidentity band scale/offset requires independent review")
            source_boundary=shape_transform(
                Transformer.from_crs("EPSG:4326",src.crs,always_xy=True).transform,boundary)
            if source_boundary.is_empty or not source_boundary.is_valid:
                raise ValueError(f"{year}: municipal polygon transformation invalid")
            b=source_boundary.bounds
            window=from_bounds(*b,transform=src.transform).round_offsets().round_lengths()
            full=Window(0,0,src.width,src.height)
            try:
                window=window.intersection(full)
            except rasterio.errors.WindowError:
                raise ValueError(f"{year}: no intersecting source raster extent")
            w,h=int(window.width),int(window.height)
            if w*h>350_000_000:
                raise ValueError(f"{year}: clipped source bbox too large ({w*h} pixels)")
            tf=window_transform(window,src.transform)
            profile=src.profile.copy()
            profile.update(driver="GTiff",count=1,width=w,height=h,transform=tf,
                           dtype="float32",nodata=-9999.0,compress="deflate",
                           tiled=True,blockxsize=256,blockysize=256)
            destination.parent.mkdir(parents=True,exist_ok=True)
            with rasterio.open(destination,"w",**profile) as dst:
                kept=0
                for row in range(0,h,256):
                    for col in range(0,w,256):
                        hh=min(256,h-row);ww=min(256,w-col)
                        local=Window(col,row,ww,hh)
                        absolute=Window(int(window.col_off)+col,int(window.row_off)+row,ww,hh)
                        arr=src.read(1,window=absolute,masked=True)
                        valid=geometry_mask([mapping(source_boundary)],out_shape=(hh,ww),
                                            transform=window_transform(local,tf),
                                            invert=True,all_touched=False)
                        vals=np.asarray(arr.filled(-9999.0),dtype="float32")
                        vals[~valid]=-9999.0
                        kept+=int(np.count_nonzero(valid & (vals!=-9999.0)))
                        dst.write(vals,1,window=local)
            report["sources"][year]={
                "status":"cropped","url":url,"crs":str(src.crs),
                "source_resolution_m":[rx,ry],"source_nodata":float(src.nodata),
                "local_crop":str(destination),"crop_size":[w,h],
                "valid_inside_polygon_pixels":kept,
                "source_scale":src.scales[0],"source_offset":src.offsets[0]
            }
            if kept==0:
                raise ValueError(f"{year}: no valid source cells inside project boundary")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--diagnostics",type=Path,default=ROOT/"metadata/biomass_native_fetch_diagnostics.json")
    parser.add_argument("--output",type=Path,default=ROOT/"metadata/biomass_native_area_comparison.json")
    parser.add_argument("--workdir",type=Path,default=Path("/tmp/biomass_native"))
    parser.add_argument("--boundary",type=Path,default=ROOT/"docs/data/lulea_boundary.geojson")
    args=parser.parse_args()
    metadata=json.loads((ROOT/"docs/data/preview/preview_layers.json").read_text(encoding="utf-8"))
    boundary_doc=json.loads(args.boundary.read_text(encoding="utf-8"))
    if boundary_doc.get("type")!="FeatureCollection" or len(boundary_doc.get("features",[]))!=1:
        raise ValueError("Expected a single verified project boundary FeatureCollection")
    boundary=shape(boundary_doc["features"][0]["geometry"])
    if boundary.is_empty or not boundary.is_valid:
        raise ValueError("Project boundary is invalid")
    report={"started_utc":datetime.now(timezone.utc).isoformat(),
            "status":"in_progress","source_crs":"source-specific; see individual source",
            "analysis_crs":"EPSG:3006",
            "boundary_crs":"EPSG:4326",
            "boundary_note":"Project Lulea working geometry; not official municipality boundary",
            "sources":{},"error":None}
    save_diagnostics(args.diagnostics,report)
    try:
        local={}
        for year,layer in LAYERS.items():
            url=metadata["layers"][layer]["source"]
            if not url.startswith("https://gis.slu.se/") or not url.lower().endswith(".tif"):
                raise ValueError(f"{year}: unexpected source URL: {url}")
            print("Reading source-CRS municipal windows:",year,url,flush=True)
            local[year]=args.workdir/f"biomass_{year}_lulea_source_crs.tif"
            crop_source(url,year,boundary,local[year],report)
            save_diagnostics(args.diagnostics,report)
        cmd=[sys.executable,str(ROOT/"scripts/compare_biomass_native_area.py"),
             "--raster-2010",str(local["2010"]),
             "--raster-2015",str(local["2015"]),
             "--raster-2018",str(local["2018"]),
             "--boundary",str(args.boundary),
             "--output",str(args.output)]
        subprocess.run(cmd,check=True)
        report["status"]="completed_unverified_units"
        report["comparison_result"]=str(args.output)
        print("Native areal comparison completed, units and products NOT verified as equivalent",flush=True)
    except Exception as error:
        report["status"]="failed"
        report["error"]=str(error)
        report["traceback"]=traceback.format_exc()[-5000:]
        print("Native biomass fetch/compare failed:",error,file=sys.stderr,flush=True)
        raise
    finally:
        report["finished_utc"]=datetime.now(timezone.utc).isoformat()
        save_diagnostics(args.diagnostics,report)

if __name__=="__main__":main()
,
            wkt, re.IGNORECASE,
        )
        return bool(match and int(match.group(1)) == expected_epsg)
    except (ValueError, TypeError, RuntimeError):
        return False

def crop_source(url, year, boundary, destination, report):
    # Passing /vsicurl explicitly can avoid GDAL attempts at full-file downloads.
    # A genuine range-enabled GeoTIFF is required for practical remote window reads.
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                      CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
                      GDAL_HTTP_MAX_RETRY="2",
                      GDAL_HTTP_RETRY_DELAY="2",
                      GDAL_HTTP_TIMEOUT="35"):
        with rasterio.open("/vsicurl/"+url) as src:
            expected_epsg, expected_res = EXPECTED[year]
            if not src.crs or not matches_expected_crs(src.crs, expected_epsg):
                raise ValueError(f"{year}: CRS {src.crs} differs from expected EPSG:{expected_epsg}")
            rx,ry=map(abs,src.res)
            if abs(rx-expected_res)>0.05 or abs(ry-expected_res)>0.05:
                raise ValueError(f"{year}: {src.res} m resolution differs from {expected_res} m")
            if src.nodata is None:
                raise ValueError(f"{year}: NoData undefined; cannot safely mask")
            if src.scales[0]!=1 or src.offsets[0]!=0:
                raise ValueError(f"{year}: nonidentity band scale/offset requires independent review")
            source_boundary=shape_transform(
                Transformer.from_crs("EPSG:4326",src.crs,always_xy=True).transform,boundary)
            if source_boundary.is_empty or not source_boundary.is_valid:
                raise ValueError(f"{year}: municipal polygon transformation invalid")
            b=source_boundary.bounds
            window=from_bounds(*b,transform=src.transform).round_offsets().round_lengths()
            full=Window(0,0,src.width,src.height)
            try:
                window=window.intersection(full)
            except rasterio.errors.WindowError:
                raise ValueError(f"{year}: no intersecting source raster extent")
            w,h=int(window.width),int(window.height)
            if w*h>350_000_000:
                raise ValueError(f"{year}: clipped source bbox too large ({w*h} pixels)")
            tf=window_transform(window,src.transform)
            profile=src.profile.copy()
            profile.update(driver="GTiff",count=1,width=w,height=h,transform=tf,
                           dtype="float32",nodata=-9999.0,compress="deflate",
                           tiled=True,blockxsize=256,blockysize=256)
            destination.parent.mkdir(parents=True,exist_ok=True)
            with rasterio.open(destination,"w",**profile) as dst:
                kept=0
                for row in range(0,h,256):
                    for col in range(0,w,256):
                        hh=min(256,h-row);ww=min(256,w-col)
                        local=Window(col,row,ww,hh)
                        absolute=Window(int(window.col_off)+col,int(window.row_off)+row,ww,hh)
                        arr=src.read(1,window=absolute,masked=True)
                        valid=geometry_mask([mapping(source_boundary)],out_shape=(hh,ww),
                                            transform=window_transform(local,tf),
                                            invert=True,all_touched=False)
                        vals=np.asarray(arr.filled(-9999.0),dtype="float32")
                        vals[~valid]=-9999.0
                        kept+=int(np.count_nonzero(valid & (vals!=-9999.0)))
                        dst.write(vals,1,window=local)
            report["sources"][year]={
                "status":"cropped","url":url,"crs":str(src.crs),
                "source_resolution_m":[rx,ry],"source_nodata":float(src.nodata),
                "local_crop":str(destination),"crop_size":[w,h],
                "valid_inside_polygon_pixels":kept,
                "source_scale":src.scales[0],"source_offset":src.offsets[0]
            }
            if kept==0:
                raise ValueError(f"{year}: no valid source cells inside project boundary")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--diagnostics",type=Path,default=ROOT/"metadata/biomass_native_fetch_diagnostics.json")
    parser.add_argument("--output",type=Path,default=ROOT/"metadata/biomass_native_area_comparison.json")
    parser.add_argument("--workdir",type=Path,default=Path("/tmp/biomass_native"))
    parser.add_argument("--boundary",type=Path,default=ROOT/"docs/data/lulea_boundary.geojson")
    args=parser.parse_args()
    metadata=json.loads((ROOT/"docs/data/preview/preview_layers.json").read_text(encoding="utf-8"))
    boundary_doc=json.loads(args.boundary.read_text(encoding="utf-8"))
    if boundary_doc.get("type")!="FeatureCollection" or len(boundary_doc.get("features",[]))!=1:
        raise ValueError("Expected a single verified project boundary FeatureCollection")
    boundary=shape(boundary_doc["features"][0]["geometry"])
    if boundary.is_empty or not boundary.is_valid:
        raise ValueError("Project boundary is invalid")
    report={"started_utc":datetime.now(timezone.utc).isoformat(),
            "status":"in_progress","source_crs":"source-specific; see individual source",
            "analysis_crs":"EPSG:3006",
            "boundary_crs":"EPSG:4326",
            "boundary_note":"Project Lulea working geometry; not official municipality boundary",
            "sources":{},"error":None}
    save_diagnostics(args.diagnostics,report)
    try:
        local={}
        for year,layer in LAYERS.items():
            url=metadata["layers"][layer]["source"]
            if not url.startswith("https://gis.slu.se/") or not url.lower().endswith(".tif"):
                raise ValueError(f"{year}: unexpected source URL: {url}")
            print("Reading source-CRS municipal windows:",year,url,flush=True)
            local[year]=args.workdir/f"biomass_{year}_lulea_source_crs.tif"
            crop_source(url,year,boundary,local[year],report)
            save_diagnostics(args.diagnostics,report)
        cmd=[sys.executable,str(ROOT/"scripts/compare_biomass_native_area.py"),
             "--raster-2010",str(local["2010"]),
             "--raster-2015",str(local["2015"]),
             "--raster-2018",str(local["2018"]),
             "--boundary",str(args.boundary),
             "--output",str(args.output)]
        subprocess.run(cmd,check=True)
        report["status"]="completed_unverified_units"
        report["comparison_result"]=str(args.output)
        print("Native areal comparison completed, units and products NOT verified as equivalent",flush=True)
    except Exception as error:
        report["status"]="failed"
        report["error"]=str(error)
        report["traceback"]=traceback.format_exc()[-5000:]
        print("Native biomass fetch/compare failed:",error,file=sys.stderr,flush=True)
        raise
    finally:
        report["finished_utc"]=datetime.now(timezone.utc).isoformat()
        save_diagnostics(args.diagnostics,report)

if __name__=="__main__":main()
