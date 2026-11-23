#!/usr/bin/env python3
"""Archive native CRS forest TOTAL VOLUME clips, not biomass estimates."""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from rasterio import open as rio_open
from shapely.geometry import shape
from fetch_and_compare_biomass_native import crop_source, EXPECTED, matches_expected_crs

ROOT=Path(__file__).resolve().parents[1]
SOURCES={
  "2000":"https://gis.slu.se/data/slu_forest_map/2000/Data/Raster/Rt90/TOTALVOL_XX_P_00.tif",
  "2005":"https://gis.slu.se/data/slu_forest_map/2005/Data/Raster/Rt90/TOTALVOL_XX_P_05.tif",
  "2010":"https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/TOTALVOL_XX_P_10.tif",
}
for year in SOURCES: EXPECTED[year]=(3021,25.0)

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(8*1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--year",choices=sorted(SOURCES),required=True)
    parser.add_argument("--output-dir",type=Path,default=Path("release-assets"))
    args=parser.parse_args()
    boundary_path=ROOT/"docs/data/lulea_boundary.geojson"
    geom=json.loads(boundary_path.read_text(encoding="utf-8"))
    if geom.get("type")!="FeatureCollection" or len(geom.get("features",[]))!=1:
        raise ValueError("Expected one GeoJSON project boundary feature in EPSG:4326")
    boundary=shape(geom["features"][0]["geometry"])
    if boundary.is_empty or not boundary.is_valid:
        raise ValueError("Invalid project boundary")
    args.output_dir.mkdir(parents=True,exist_ok=True)
    stem=f"lulea_total_volume_{args.year}"
    tif=args.output_dir/(stem+"_source_crs_clip.tif")
    provenance=args.output_dir/(stem+"_provenance.json")
    checks=args.output_dir/(stem+"_SHA256SUMS.txt")
    diag={"sources":{}}
    crop_source(SOURCES[args.year],args.year,boundary,tif,diag)
    if not tif.is_file() or tif.stat().st_size==0 or tif.stat().st_size>=2_000_000_000:
        raise ValueError("Missing/invalid archived crop size or release size threshold")
    info=diag["sources"][args.year]
    with rio_open(tif) as src:
        if not matches_expected_crs(src.crs,3021) or src.count!=1:
            raise ValueError("Unexpected raster band or CRS; expected EPSG:3021")
        if any(abs(abs(r)-25)>0.05 for r in src.res) or src.nodata!=-9999:
            raise ValueError("Unexpected source resolution or NoData")
    data={
      "schema_version":1,"created_utc":datetime.now(timezone.utc).isoformat(),
      "year":args.year,"product":"SLU Skogskarta total standing wood volume",
      "source_url":SOURCES[args.year],
      "asset_type":"boundary-masked municipal clip in original raster CRS, derived not source original",
      "source_crs":"EPSG:3021","source_resolution_m":25.0,
      "source_nodata":info["source_nodata"],"source_scale":info["source_scale"],
      "source_offset":info["source_offset"],"crop_size_pixels":info["crop_size"],
      "valid_inside_polygon_pixels":info["valid_inside_polygon_pixels"],
      "boundary_file":str(boundary_path.relative_to(ROOT)),
      "boundary_sha256":sha(boundary_path),"asset_filename":tif.name,
      "asset_size_bytes":tif.stat().st_size,"asset_sha256":sha(tif),
      "physical_units_verified":False,
      "biomass_estimate":None,
      "caution":"Virkesvolym och biomassa är skilda variabler. Ingen konvertering eller harmoniserad tidsserie utförd."
    }
    provenance.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    checks.write_text(f"{sha(tif)}  {tif.name}\n{sha(provenance)}  {provenance.name}\n",encoding="utf-8")
    print(json.dumps(data,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
