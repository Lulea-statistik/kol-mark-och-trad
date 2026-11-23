#!/usr/bin/env python3
"""Make a persistent, source-CRS Lulea GeoTIFF excerpt for a GitHub Release.

The result is a clipped DERIVATIVE, not a bit-for-bit copy of SLU's national TIFF.
Pixel resolution, values and original source CRS are retained inside the polygon.
No dataset is claimed complete until every source value is successfully read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from rasterio import open as open_raster
from fetch_and_compare_biomass_native import crop_source, EXPECTED
from shapely.geometry import shape

ROOT=Path(__file__).resolve().parents[1]
SOURCE_KEYS={"2010":"biomass_2010","2015":"biomass_2015_leaf","2018":"biomass"}
LIMIT_BYTES=2_000_000_000  # conservative; GitHub release per-asset limit is 2 GiB.

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(8*1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--year",required=True,choices=SOURCE_KEYS)
    p.add_argument("--output-dir",type=Path,default=Path("release-assets"))
    args=p.parse_args()
    manifest=json.loads((ROOT/"docs/data/preview/preview_layers.json").read_text(encoding="utf-8"))
    source=manifest["layers"][SOURCE_KEYS[args.year]]
    url=source["source"]
    if not url.startswith("https://gis.slu.se/") or not url.lower().endswith(".tif"):
        raise ValueError("Untrusted source URL in metadata")
    boundary_file=ROOT/"docs/data/lulea_boundary.geojson"
    boundary_doc=json.loads(boundary_file.read_text(encoding="utf-8"))
    if boundary_doc.get("type")!="FeatureCollection" or len(boundary_doc.get("features",[]))!=1:
        raise ValueError("Expected a single project boundary FeatureCollection")
    boundary=shape(boundary_doc["features"][0]["geometry"])
    if boundary.is_empty or not boundary.is_valid:
        raise ValueError("Invalid project boundary")
    args.output_dir.mkdir(parents=True,exist_ok=True)
    raster=args.output_dir/f"lulea_biomass_{args.year}_source_crs_clip.tif"
    provenance=args.output_dir/f"lulea_biomass_{args.year}_provenance.json"
    crop_report={"sources":{}}
    crop_source(url,args.year,boundary,raster,crop_report)
    if not raster.is_file() or raster.stat().st_size == 0:
        raise ValueError("No completed output raster")
    if raster.stat().st_size>=LIMIT_BYTES:
        raster.unlink(missing_ok=True)
        raise ValueError(f"Raster clip exceeds conservative release size limit of {LIMIT_BYTES} bytes; use external object storage or spatial tiles")
    info=crop_report["sources"][args.year]
    epsg,res=EXPECTED[args.year]
    with open_raster(raster) as src:
        if src.crs is None or src.crs.to_epsg() not in (epsg,None):
            raise ValueError("Output CRS differs from source CRS")
        if abs(abs(src.res[0])-res)>0.05 or abs(abs(src.res[1])-res)>0.05:
            raise ValueError("Output source grid resolution altered")
        if src.count!=1 or src.nodata != -9999:
            raise ValueError("Unexpected number of bands or NoData after cropping")
    data={
        "schema_version":1,
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "year":args.year,
        "origin_url":url,
        "origin_dataset":"SLU raster as recorded in project preview manifest; exact remote version is not pinned",
        "asset_type":"Lulea boundary-masked source-CRS excerpt (DERIVATIVE), not full national original",
        "source_crs":info["crs"],
        "source_resolution_m":info["source_resolution_m"],
        "original_nodata":info["source_nodata"],
        "excerpt_nodata":-9999,
        "source_scale":info["source_scale"],
        "source_offset":info["source_offset"],
        "crop_size_pixels":info["crop_size"],
        "valid_pixels_inside_project_boundary":info["valid_inside_polygon_pixels"],
        "project_boundary_file":"docs/data/lulea_boundary.geojson",
        "project_boundary_sha256":sha256(boundary_file),
        "asset_filename":raster.name,
        "asset_size_bytes":raster.stat().st_size,
        "asset_sha256":sha256(raster),
        "physical_units_verified":False,
        "notes":"Values in polygon are sampled from the source TIFF without resampling; all pixels outside polygon set NoData. For full original archival preservation, download original GeoTIFF separately."
    }
    provenance.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data,ensure_ascii=False,indent=2),flush=True)
    (args.output_dir/f"lulea_biomass_{args.year}_SHA256SUMS.txt").write_text(
        f"{data['asset_sha256']}  {raster.name}\n{sha256(provenance)}  {provenance.name}\n",encoding="utf-8")
if __name__=="__main__":
    main()
