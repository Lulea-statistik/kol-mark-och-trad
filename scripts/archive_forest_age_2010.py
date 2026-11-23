#!/usr/bin/env python3
"""Archive source-grid SLU Skogskarta 2010 age for the Lulea project polygon.

An estimated 2010 age surface is NOT evidence of age in 2000 or 2025
for harvested/regenerated pixels. Keep in a separate age release.
"""
from __future__ import annotations
import argparse,json,hashlib
from datetime import datetime,timezone
from pathlib import Path
from shapely.geometry import shape
import rasterio
from fetch_and_compare_biomass_native import crop_source,matches_expected_crs

ROOT=Path(__file__).resolve().parents[1]
URL="https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/AGE_XX_P_10.tif"
def sha(file):
    h=hashlib.sha256()
    with file.open("rb") as handle:
        for block in iter(lambda:handle.read(8*1024*1024),b""):h.update(block)
    return h.hexdigest()
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,default=Path("age-release-assets"))
    a=parser.parse_args()
    boundary=ROOT/"docs/data/lulea_boundary.geojson"
    document=json.loads(boundary.read_text(encoding="utf-8"))
    if document.get("type")!="FeatureCollection" or len(document.get("features",[]))!=1:
        raise ValueError("Project boundary must contain exactly one feature")
    polygon=shape(document["features"][0]["geometry"])
    if polygon.is_empty or not polygon.is_valid:
        raise ValueError("Invalid boundary")
    a.output_dir.mkdir(parents=True,exist_ok=True)
    stem="lulea_forest_age_2010"
    tif=a.output_dir/(stem+"_source_crs_clip.tif")
    meta=a.output_dir/(stem+"_provenance.json")
    sha_file=a.output_dir/(stem+"_SHA256SUMS.txt")
    report={"sources":{}}
    crop_source(URL,"2010",polygon,tif,report)
    with rasterio.open(tif) as src:
        if src.count!=1 or not matches_expected_crs(src.crs,3021) or src.nodata!=-9999:
            raise ValueError("Age raster CRS/band/nodata differs from expected 2010 Skogskarta")
        if any(abs(abs(x)-25)>0.05 for x in src.res):
            raise ValueError("Age source cell size differs from 25 m")
    if tif.stat().st_size>=2_000_000_000:raise ValueError("Release asset size exceeds conservative limit")
    info=report["sources"]["2010"]
    provenance={
      "created_utc":datetime.now(timezone.utc).isoformat(),
      "source_url":URL,"product":"SLU Skogskarta 2010 AGE",
      "asset_type":"municipal source CRS derived raster clip, not whole original",
      "source_crs":"EPSG:3021","source_resolution_m":25,
      "source_nodata":info["source_nodata"],"clip_nodata":-9999,
      "valid_inside_polygon_pixels":info["valid_inside_polygon_pixels"],
      "boundary_sha256":sha(boundary),"asset_sha256":sha(tif),
      "asset_size_bytes":tif.stat().st_size,"source_scale":info["source_scale"],
      "source_offset":info["source_offset"],"age_reference_year":2010,
      "units_verified_by_independent_product_metadata":False,
      "caution":"Estimated stand age 2010; not suitable for automatic backcasting over harvest or regeneration."
    }
    meta.write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    sha_file.write_text(f"{sha(tif)}  {tif.name}\n{sha(meta)}  {meta.name}\n",encoding="utf-8")
    print(json.dumps(provenance,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
