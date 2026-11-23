#!/usr/bin/env python3
"""Archive 2000 and 2005 stand age from verified SLU Skogskarta source rasters.

Only clipped municipal derivatives, never national originals. Reuses source
CRS clipping procedure. Does not equate stand AGE with stand productivity.
"""
from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from shapely.geometry import shape
import rasterio
from fetch_and_compare_biomass_native import crop_source,EXPECTED,matches_expected_crs

ROOT=Path(__file__).resolve().parents[1]
YEARS=("2000","2005")
URLS={year:f"https://gis.slu.se/data/slu_forest_map/{year}/Data/Raster/Rt90/AGE_XX_P_{year[-2:]}.tif" for year in YEARS}
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as file:
        for b in iter(lambda:file.read(8*1024*1024),b""):h.update(b)
    return h.hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--year",required=True,choices=YEARS)
    parser.add_argument("--output-dir",type=Path,default=Path("age-release-assets"))
    args=parser.parse_args()
    source=URLS[args.year]
    boundary_file=ROOT/"docs/data/lulea_boundary.geojson"
    boundary_data=json.loads(boundary_file.read_text(encoding="utf-8"))
    if boundary_data.get("type")!="FeatureCollection" or len(boundary_data.get("features",[]))!=1:
        raise ValueError("Exactly one valid EPSG:4326 project polygon is required")
    polygon=shape(boundary_data["features"][0]["geometry"])
    if polygon.is_empty or not polygon.is_valid:raise ValueError("Invalid project polygon")
    prefix=f"lulea_forest_age_{args.year}"
    args.output_dir.mkdir(parents=True,exist_ok=True)
    dest=args.output_dir/(prefix+"_source_crs_clip.tif")
    meta=args.output_dir/(prefix+"_provenance.json")
    sums=args.output_dir/(prefix+"_SHA256SUMS.txt")
    EXPECTED[args.year]=(3021,25.0)
    diagnostics={"sources":{}}
    crop_source(source,args.year,polygon,dest,diagnostics)
    info=diagnostics["sources"][args.year]
    with rasterio.open(dest) as raster:
        if raster.count!=1 or not matches_expected_crs(raster.crs,3021) or raster.nodata!=-9999:
            raise ValueError("Unexpected clipped AGE source CRS/band/nodata")
        if any(abs(abs(v)-25)>0.05 for v in raster.res):
            raise ValueError("AGE source cell size differs from 25 m")
    if not dest.is_file() or dest.stat().st_size>=2_000_000_000:
        raise ValueError("Output missing or exceeds permitted release asset size")
    provenance={"created_utc":datetime.now(timezone.utc).isoformat(),
       "product":"SLU Skogskarta historical AGE","year":args.year,
       "source_url":source,"source_crs":"EPSG:3021",
       "source_resolution_m":25.0,"source_nodata":info["source_nodata"],
       "clip_nodata":-9999,"source_scale":info["source_scale"],
       "source_offset":info["source_offset"],
       "asset_type":"municipal boundary-clipped derived age raster, not national source original",
       "source_crop_size_pixels":info["crop_size"],
       "valid_inside_polygon_pixels":info["valid_inside_polygon_pixels"],
       "boundary_sha256":sha(boundary_file),"asset_sha256":sha(dest),
       "asset_size_bytes":dest.stat().st_size,
       "model_reference":"age estimated by SLU for nominal reference year; acquisition dates vary",
       "independent_age_accuracy_verified":False}
    meta.write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    sums.write_text(f"{sha(dest)}  {dest.name}\n{sha(meta)}  {meta.name}\n",encoding="utf-8")
    print(json.dumps(provenance,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
