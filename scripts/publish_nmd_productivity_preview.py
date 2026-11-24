#!/usr/bin/env python3
"""Publish a REAL, explicitly versioned NMD productivity raster on the existing map grid.

Requires a source GeoTIFF, with CRS/NoData, supplied by the operator. Never
substitute dummy cells. The original TIFF is not stored in GitHub Pages.
This display raster is NOT the EPSG:3006 raster used for area calculations.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import tempfile
from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.mask import mask as native_mask
from rasterio.transform import from_bounds
from rasterio.vrt import WarpedVRT
from shapely.geometry import shape, mapping
from shapely.ops import transform as geom_transform
from pyproj import Transformer
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/data/preview"
MANIFEST = OUT / "preview_layers.json"
BOUNDARY = ROOT / "docs/data/lulea_boundary.geojson"
COLORS = {0: (202, 181, 134, 255), 1: (33, 116, 72, 255),
          2: (111, 164, 196, 255)}
NODATA = -9999.0

def run(args):
    if not args.version.strip() or not args.source_url.startswith("https://"):
        raise ValueError("Explicit NMD data version and HTTPS provenance URL required")
    if not args.source.is_file():
        raise ValueError("Real NMD raster file not found")
    if not MANIFEST.is_file():
        raise ValueError("Existing map preview manifest missing")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    base = manifest.get("layers", {}).get("biomass")
    if not base or base.get("raster_grid_crs") != "EPSG:3857":
        raise ValueError("Reference preview grid not yet verified")
    west, south, east, north = base["raster_grid_bounds_m"]
    width, height = int(base["raster_grid_width"]), int(base["raster_grid_height"])
    if min(width, height) <= 0 or max(width, height) > 6000:
        raise ValueError("Unexpected preview resolution")
    transform = from_bounds(west, south, east, north, width, height)
    boundary_json = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    geom = shape(boundary_json["features"][0]["geometry"])
    if not geom.is_valid or geom.is_empty:
        raise ValueError("Invalid municipal working boundary")
    geom3857 = geom_transform(
        Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform, geom)
    inside = geometry_mask([mapping(geom3857)], (height, width),
                           transform, invert=True)
    source_hash = hashlib.sha256()
    with args.source.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            source_hash.update(chunk)
    with rasterio.open(args.source) as src:
        if src.crs is None or src.nodata is None:
            raise ValueError("Source raster must explicitly declare CRS and NoData")
        if args.band < 1 or args.band > src.count:
            raise ValueError("Requested NMD band is absent from source")
        if args.band == 10 and src.count < 10:
            raise ValueError("A 10-band source is required to read band 10")
        if not src.crs.is_projected:
            raise ValueError("Expected projected source raster for native 10m crop")
        # Crop and mask against the boundary IN THE SOURCE CRS before warping.
        geom_native = geom_transform(
            Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform, geom)
        cropped, crop_transform = native_mask(
            src, [mapping(geom_native)], crop=True, indexes=args.band,
            filled=True, nodata=src.nodata)
        if cropped.ndim != 2:
            raise ValueError("Expected one native cropped NMD classification band")
        # Entire cropped pixel grid is then genuinely reprojected to the display CRS.
        with tempfile.TemporaryDirectory() as tmp:
            native_path = Path(tmp) / "lulea_nmd_source_crs_clip.tif"
            with rasterio.open(native_path, "w", driver="GTiff",
                    width=cropped.shape[1], height=cropped.shape[0], count=1,
                    dtype=cropped.dtype, transform=crop_transform, crs=src.crs,
                    nodata=src.nodata, compress="deflate", tiled=True) as dst:
                dst.write(cropped, 1)
            del cropped
            with rasterio.open(native_path) as native_src:
                with WarpedVRT(native_src, crs="EPSG:3857", transform=transform,
                               width=width, height=height,
                               resampling=Resampling.nearest,
                               src_nodata=native_src.nodata, nodata=NODATA) as vrt:
                    sampled = vrt.read(1, masked=True)
        valid_source = ~np.ma.getmaskarray(sampled)
        source_values = sampled.data.astype("float32")
        valid = inside & valid_source & np.isfinite(source_values)
        observed = np.unique(source_values[valid])
        if not observed.size:
            raise ValueError("No valid NMD cells in Lulea grid")
        if not np.all(np.isin(observed, [0, 1, 2])):
            raise ValueError(f"Unexpected NMD category values: {observed[:15].tolist()}")
        # Reject all-zero fields as suspected empty/incorrect input, not a useful mask.
        if int(np.count_nonzero(valid & (source_values == 1))) == 0:
            raise ValueError("No productive forest cells found; verify band and source")
        pixels = np.zeros((height, width, 4), dtype="uint8")
        numbers = np.full((height, width), NODATA, dtype="<f4")
        counts = {}
        for cls, rgba in COLORS.items():
            mask = valid & (source_values == cls)
            counts[str(cls)] = int(mask.sum())
            pixels[mask] = rgba
            numbers[mask] = float(cls)
        # Gray explicitly denotes NoData INSIDE boundary; outside is transparent.
        pixels[inside & ~valid] = (135, 135, 135, 255)
        assert sum(counts.values()) == int(valid.sum())
        OUT.mkdir(parents=True, exist_ok=True)
        image_name = "nmd_productivitet_preview.png"
        numeric_name = "nmd_productivitet_sampled_values.f32.gz"
        Image.fromarray(pixels, "RGBA").save(OUT / image_name)
        with gzip.open(OUT / numeric_name, "wb", compresslevel=6) as fh:
            fh.write(numbers.tobytes(order="C"))
        manifest["layers"]["nmd_productivity"] = {
            "image": "data/preview/" + image_name,
            "numeric_file": "data/preview/" + numeric_name,
            "bounds": base["bounds"],
            "raster_grid_width": width, "raster_grid_height": height,
            "raster_grid_crs": "EPSG:3857",
            "raster_grid_bounds_m": base["raster_grid_bounds_m"],
            "raster_grid_nodata": NODATA,
            "display_crs": "EPSG:3857", "source_crs": src.crs.to_string(),
            "source": args.source_url, "source_sha256": source_hash.hexdigest(),
            "product_family": ("Naturvårdsverket / NMD2018 produktivitet" if "naturvardsverket.se" in args.source_url else "Skogsstyrelsen Skogliga grunddata / NMDproduktivitet"),
            "nmd_version": args.version, "source_band": args.band,
            "source_resolution_m": [abs(src.transform.a), abs(src.transform.e)],
            "source_nodata": src.nodata,
            "color_scale_type": "nmd_productivity_categories",
            "sample_type": "Categorical nearest-neighbour source pixels on full EPSG:3857 grid; not original source cells",
            "class_labels": {"0": "Ej skogsmark", "1": "Produktiv skogsmark",
                             "2": "Improduktiv skogsmark"},
            "class_preview_pixel_counts": counts,
            "valid_preview_pixels": int(valid.sum()),
            "null_inside_pixels": int((inside & ~valid).sum()),
            "municipal_preview_pixels": int(inside.sum()),
            "source_year": None, "physical_units_verified": False,
            "total_tonnes_C": None, "area_integral": False,
            "published_utc": datetime.now(timezone.utc).isoformat(),
        }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Published source-backed categorical NMD overlay:", counts,
          "NMD version:", args.version, "source SHA256:", source_hash.hexdigest())

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--band", type=int, required=True,
                   help="1-based GeoTIFF band; choose 10 only for original 10-band source")
    p.add_argument("--version", required=True, help="Verified data version (not guessed)")
    p.add_argument("--source-url", required=True, help="HTTPS URL identifying the original source")
    run(p.parse_args())
