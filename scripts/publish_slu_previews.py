#!/usr/bin/env python3
"""Publish existing generated SLU preview images and metadata, never carbon totals."""
import json
import shutil
from pathlib import Path
from pyproj import CRS

root=Path(__file__).resolve().parents[1]
source=root/"metadata"/"lulea_carbon_preview"
out=root/"docs"/"data"/"preview"
doc=json.loads((source/"preview_audit.json").read_text(encoding="utf-8"))
if doc.get("source_units_verified") is not False or doc.get("no_carbon_totals_computed") is not True:
    raise SystemExit("Unexpected audit flags; no publication")
layers={}
for key in ("biomass","soil","stock_dom","soil_all","change_soc","change_dom","change_all"):
    r=doc["files"][key]
    if r.get("status")!="visual_preview_created" or r.get("units_verified") is not False:
        raise SystemExit(f"Invalid source preview {key}")
    # Each product may use a DIFFERENT, valid source CRS. Rasterio's WarpedVRT
    # already resamples the entire pixel grid into EPSG:3857 (not just bounds).
    # Check actual CRS, not a hard-coded EPSG assumption.
    crs_text=r.get("source_crs")
    try:
        src_crs=CRS.from_user_input(crs_text)
    except (ValueError, TypeError) as exc:
        raise SystemExit(f"{key}: missing or invalid source CRS {crs_text!r}: {exc}")
    if not src_crs.is_projected:
        raise SystemExit(f"{key}: expected a projected source CRS; got {crs_text}")
    if not src_crs.axis_info or any(abs(ax.unit_conversion_factor-1)>1e-7 for ax in src_crs.axis_info[:2]):
        raise SystemExit(f"{key}: source CRS axes must be in metres; got {crs_text}")
    if r.get("raster_grid_crs")!="EPSG:3857":
        raise SystemExit(f"{key}: map raster not fully reprojected to EPSG:3857")
    if not r.get("source_url","").startswith("https://gis.slu.se/data/"):
        raise SystemExit(f"{key}: unexpected source host")
    print(f"{key}: source CRS={src_crs.to_string()}, map grid=EPSG:3857, source pixels={r.get('valid_pixels')}",flush=True)
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
      "product_family":r["product_family"],
      "source_resolution_m":r["source_resolution_m"],
      "source_unit_tag":r["source_unit_tag"],
      "source_band_scale":r["source_band_scale"],
      "source_band_offset":r["source_band_offset"],
      "display_crs":"EPSG:3857",
      "valid_preview_pixels":r["valid_pixels"],
      "value_scale":("Beige true zero; positive-only log1p scale yellow to orange/red to dark brown; grey NoData" if key=="biomass" else "Blue negative, white zero, red positive; grey NoData" if key.startswith("change_") else "Red low, black high; grey NoData"),
      "biomass_positive_source_p02":r.get("biomass_positive_source_p02"),
      "biomass_positive_source_p98":r.get("biomass_positive_source_p98"),
      "color_scale_type":r.get("color_scale_type"),
      "signed_color_scale_max_abs_p98":r.get("signed_color_scale_max_abs_p98"),
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
      "raw_pixel_sum":r["raw_pixel_sum"],
      "raw_pixel_negative_count":r["raw_pixel_negative_count"],
      "raw_pixel_positive_count":r["raw_pixel_positive_count"],
      "raw_pixel_zero_count":r["raw_pixel_zero_count"],
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
      "mean_raw":v["raw_pixel_mean"],"sum_raw":v["raw_pixel_sum"],"p98_raw":v["raw_pixel_q98"],
      "histogram":v["raw_pixel_histogram"],
      "negative_preview_pixels":v["raw_pixel_negative_count"],
      "positive_preview_pixels":v["raw_pixel_positive_count"],
      "zero_preview_pixels":v["raw_pixel_zero_count"],
      "color_scale_type":v["color_scale_type"],
      "source_crs":v["source_crs"],
      "product_family":v["product_family"],
      "source_resolution_m":v["source_resolution_m"],
      "source_unit_tag":v["source_unit_tag"],
      "sample_type":v["sample_type"],
   } for k,v in layers.items()}
 },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Created",len(layers),"SLU visual previews with sampled numeric grid and unverified-unit statistics")
