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
    layers[key]={
      "image":"data/preview/"+filename,
      "bounds":[[south,west],[north,east]],
      "source":r["source_url"],
      "source_crs":r["source_crs"],
      "display_crs":"EPSG:3857",
      "valid_preview_pixels":r["valid_pixels"],
      "value_scale":"Relative coloration per individual raster (2nd-98th percentile)",
      "physical_units_verified":False,
      "total_tonnes_C":None,
      "area_integral":False
    }
(out/"preview_layers.json").write_text(json.dumps({"kind":"unverified_units_visual_preview","layers":layers},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Created",len(layers),"SLU visual previews with explicit unverified-unit metadata")
