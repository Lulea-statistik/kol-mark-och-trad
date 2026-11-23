#!/usr/bin/env python3
"""Verify archived biomass raster excerpts BEFORE any statistics are computed.

Checks Release SHA256SUMS/provenance against downloaded bytes, source expectations,
boundary fingerprint, raster CRS, pixel size, NoData, valid count and summary
distributions. These clips are derived municipal excerpts, not SLU originals.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from fetch_and_compare_biomass_native import matches_expected_crs, EXPECTED

ROOT=Path(__file__).resolve().parents[1]
SOURCES={"2010":"biomass_2010","2015":"biomass_2015_leaf","2018":"biomass"}
YEARS=("2010","2015","2018")
def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(8*1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def run(args):
    catalog=json.loads((ROOT/"docs/data/preview/preview_layers.json").read_text(encoding="utf-8"))
    boundary=ROOT/"docs/data/lulea_boundary.geojson"
    boundary_hash=digest(boundary)
    results={}
    for year in YEARS:
        stem="lulea_biomass_"+year
        tif=args.directory/(stem+"_source_crs_clip.tif")
        provenance=args.directory/(stem+"_provenance.json")
        checks=args.directory/(stem+"_SHA256SUMS.txt")
        for f in (tif,provenance,checks):
            if not f.is_file() or f.stat().st_size==0:
                raise ValueError(f"{year}: missing or empty release asset: {f}")
        lines=[x.strip().split(maxsplit=1) for x in checks.read_text().splitlines() if x.strip()]
        signed={v.strip():h for h,v in lines}
        for file in (tif,provenance):
            if signed.get(file.name)!=digest(file):
                raise ValueError(f"{year}: SHA256SUMS differs from actual bytes: {file.name}")
        meta=json.loads(provenance.read_text(encoding="utf-8"))
        expected_url=catalog["layers"][SOURCES[year]]["source"]
        if meta["year"]!=year or meta["origin_url"]!=expected_url:
            raise ValueError(f"{year}: unexpected source identity")
        if meta["project_boundary_sha256"]!=boundary_hash:
            raise ValueError(f"{year}: boundary has changed since this clip was archived")
        if meta["asset_sha256"]!=digest(tif) or meta["asset_size_bytes"]!=tif.stat().st_size:
            raise ValueError(f"{year}: provenance SHA or size mismatch")
        if meta.get("asset_filename")!=tif.name or meta.get("physical_units_verified") is not False:
            raise ValueError(f"{year}: provenance requires review")
        if "DERIVATIVE" not in meta["asset_type"]:
            raise ValueError(f"{year}: cannot establish that file is municipal derived excerpt")
        epsg,res=EXPECTED[year]
        total=0
        nonzero=0
        zeros=0
        min_v=float("inf")
        max_v=float("-inf")
        sum_v=0.0
        sample=[]
        with rasterio.open(tif) as src:
            if src.count!=1 or not matches_expected_crs(src.crs,epsg):
                raise ValueError(f"{year}: raster band or CRS mismatch; expected EPSG:{epsg}")
            if any(not math.isclose(abs(r),res,abs_tol=0.05) for r in src.res):
                raise ValueError(f"{year}: pixel resolution mismatch")
            if src.nodata!=-9999.0 or src.dtypes[0]!="float32":
                raise ValueError(f"{year}: clip NoData/type unexpected")
            if [src.width,src.height]!=meta["crop_size_pixels"]:
                raise ValueError(f"{year}: raster shape differs from provenance")
            if any(not math.isclose(abs(r),res,abs_tol=0.05) for r in meta["source_resolution_m"]):
                raise ValueError(f"{year}: source grid metadata differs from raster")
            for _,window in src.block_windows(1):
                data=src.read(1,window=window,masked=True)
                good=np.asarray(data.compressed(),dtype="float64")
                if not good.size:
                    continue
                if not np.isfinite(good).all() or np.any(good<0):
                    raise ValueError(f"{year}: non-finite or negative valid pixels")
                total+=good.size
                zeros+=int(np.count_nonzero(good==0))
                nonzero+=int(np.count_nonzero(good>0))
                min_v=min(min_v,float(good.min()))
                max_v=max(max_v,float(good.max()))
                sum_v+=float(good.sum(dtype="float64"))
            if total != meta["valid_pixels_inside_project_boundary"]:
                raise ValueError(f"{year}: valid pixel count {total} differs from provenance {meta['valid_pixels_inside_project_boundary']}")
        if total==0:
            raise ValueError(f"{year}: no valid pixel values")
        results[year]={
            "source_url":expected_url,"archive_tif":tif.name,
            "sha256":digest(tif),"archive_bytes":tif.stat().st_size,
            "source_crs_epsg":epsg,"source_resolution_m":res,
            "valid_cells":total,"zero_cells":zeros,"positive_cells":nonzero,
            "valid_cell_fraction":total/(meta["crop_size_pixels"][0]*meta["crop_size_pixels"][1]),
            "raw_min":min_v,"raw_max":max_v,"raw_mean":sum_v/total,
            "source_units_confirmed_by_raster_metadata":False
        }
        print(year,"validated:",total,"valid cells, mean raw",round(sum_v/total,3),flush=True)
    report={
        "schema_version":1,"validated_utc":datetime.now(timezone.utc).isoformat(),
        "release_tag":"biomass-source-clips-lulea-v1",
        "boundary_sha256":boundary_hash,
        "status":"byte_and_raster_checks_passed",
        "important":"Clipped municipal derivatives; raw units, model components and temporal comparability are not verified by this script.",
        "years":results
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Release archive integrity and raster metadata verified",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--directory",type=Path,required=True)
    p.add_argument("--output",type=Path,default=Path("metadata/biomass_release_validation.json"))
    run(p.parse_args())
