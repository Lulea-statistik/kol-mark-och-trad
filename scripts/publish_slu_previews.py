#!/usr/bin/env python3
"""Publish existing generated SLU preview images and metadata, never carbon totals."""
import json
import shutil
from pathlib import Path

root=Path(__file__).resolve().parents[1]
source=root/"metadata"/"lulea_carbon_preview"
out=root/"docs"/"data"/"preview"
doc=json.loads((source/"preview_audit.json").read_text(encoding="utf-8"))
if doc.get("source_units_verified") is not False or doc.get("no_carbon_totals_computed") is not True:
    raise SystemExit("Unexpected audit flags; no publication")
layers={}
for key in ("soil","soil_all"):
    r=doc["files"][key]
    if r.get("status")!="visual_preview_created" or r.get("units_verified") is not False:
        raise SystemExit(f"Invalid source preview {key}")
    if r.get("source_crs")!="EPSG:3006":raise SystemExit("Source CRS changed, inspect first")
    bounds=r["preview_bounds_4326"]
    if len(bounds)!=4:raise SystemExit("Bad preview bounds")
    west,south,east,north=bounds
    if not (19<west<25 and 64<south<67 and 19<east<25 and 64<north<67):
        raise SystemExit("Unexpected geographic extent")
    if int(r.get("valid_pixels",0))<=0:raise SystemExit("Empty pixels")
    filename=r["image"]
    path=source/filename
    if path.suffix!=".png" or not path.is_file():raise SystemExit("Missing image")
    out.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,out/filename)
    numeric_file=r.get("numeric_file")
    if not numeric_file or not (source/numeric_file).is_file():
        raise SystemExit("Missing validated sampled numeric raster")
    if int(r.get("raster_grid_width",0))*int(r.get("raster_grid_height",0))<=0:
        raise SystemExit("Missing raster grid size")
    shutil.copyfile(source/numeric_file,out/numeric_file)
    layers[key]={
      "image":"data/preview/"+filename,
      "bounds":[[south,west],[north,east]],
      "source":r["source_url"],
      "source_crs":r["source_crs"],
      "display_crs":"EPSG:3857",
      "valid_preview_pixels":r["valid_pixels"],
      "value_scale":"Red to black, relative 2nd-98th percentile of sampled source values; grey is source NoData",
      "numeric_file":"data/preview/"+numeric_file,
      "raster_grid_width":r["raster_grid_width"],
      "raster_grid_height":r["raster_grid_height"],
      "raster_grid_crs":r["raster_grid_crs"],
      "raster_grid_bounds_m":r["raster_grid_bounds_m"],
      "raster_grid_nodata":r["raster_grid_nodata"],
      "sample_type":r["sample_type"],
      "raw_pixel_q02":r["raw_pixel_q02"],
      "raw_pixel_q98":r["raw_pixel_q98"],
      "raw_pixel_median":r["raw_pixel_median"],
      "raw_pixel_mean":r["raw_pixel_mean"],
      "raw_pixel_min":r["raw_pixel_min"],
      "raw_pixel_max":r["raw_pixel_max"],
      "raw_pixel_histogram":r["raw_pixel_histogram"],
      "null_inside_pixels":r["null_inside_pixels"],
      "municipal_preview_pixels":r["municipal_preview_pixels"],
      "physical_units_verified":False,
      "total_tonnes_C":None,
      "area_integral":False
    }
(out/"preview_layers.json").write_text(json.dumps({"kind":"unverified_units_visual_preview","layers":layers},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(out/"preview_statistics.json").write_text(json.dumps({
   "data_type":"raw_source_samples_in_reprojected_preview_grid",
   "physical_units_verified":False,
   "scope":"Luleå working municipality geometry; grid pixels are not source 10-m cells",
   "layers":{k:{
      "source":v["source"],
      "raster_grid_width":v["raster_grid_width"],
      "raster_grid_height":v["raster_grid_height"],
      "valid_preview_pixels":doc["files"][k]["valid_pixels"],
      "municipal_preview_pixels":v["municipal_preview_pixels"],
      "null_inside_pixels":v["null_inside_pixels"],
      "min_raw":v["raw_pixel_min"],"max_raw":v["raw_pixel_max"],
      "p02_raw":v["raw_pixel_q02"],"median_raw":v["raw_pixel_median"],
      "mean_raw":v["raw_pixel_mean"],"p98_raw":v["raw_pixel_q98"],
      "histogram":v["raw_pixel_histogram"],
      "source_crs":v["source_crs"],
      "sample_type":v["sample_type"],
   } for k,v in layers.items()}
 },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Created",len(layers),"SLU visual previews with sampled numeric grid and unverified-unit statistics")
