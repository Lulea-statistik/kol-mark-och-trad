#!/usr/bin/env python3
"""Non-destructive NMD2018 x SGD2 native-raster QA for the Lulea working boundary.

Download only Norrbotten's NMD2018 original county file, then compare NMD
classes against native SGD2 data in source CRS with categorical nearest warp.
All counts are diagnostic; raw raster values are NEVER changed. No tonnes
reported until source unit/scale are explicitly resolved.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.request
import zipfile
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window, from_bounds
from shapely.geometry import shape, mapping
from shapely.ops import transform as transform_geometry
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
NMD_URL = "https://geodata.naturvardsverket.se/nedladdning/marktacke/NMD2018/bas_lan_ogen/BD_lan_nmd2018bas_ogeneraliserad_v1_1.zip"
SGD2_URL = "https://gis.slu.se/data/slu_skogliga_grunddata/SGD2/data/SGD2_BIO.tif"
CLASSES = {
    "water_inland": [61], "water_sea": [62], "buildings": [51],
    "roads": [53], "other_developed_review": [52],
}
BLOCK = 512
ENV = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
       "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
       "GDAL_HTTP_MAX_RETRY": "3", "GDAL_HTTP_RETRY_DELAY": "2",
       "GDAL_HTTP_TIMEOUT": "90"}

def download_nmd(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    zippath = out_dir / "NMD2018_Norrbotten.zip"
    if not zippath.exists():
        request = urllib.request.Request(NMD_URL, headers={"User-Agent":"Lulea-statistik-nmd-biomass-audit/1.0"})
        with urllib.request.urlopen(request, timeout=180) as response, zippath.open("wb") as target:
            import shutil
            shutil.copyfileobj(response, target, length=1024 * 1024)
    with zipfile.ZipFile(zippath) as archive:
        tif_names = [n for n in archive.namelist() if n.lower().endswith((".tif", ".tiff")) and not n.startswith("__MACOSX")]
        if len(tif_names) != 1:
            raise ValueError(f"Expected exactly one NMD basskikt TIFF, got: {tif_names[:20]}")
        name = tif_names[0]
        local = out_dir / Path(name).name
        if not local.exists():
            with archive.open(name) as source, local.open("wb") as target:
                import shutil
                shutil.copyfileobj(source, target, length=1024 * 1024)
    return local

def new_counter():
    return {"eligible_pixels": 0, "positive_pixels": 0, "zero_pixels": 0,
            "raw_positive_sum": 0.0, "max_positive_raw": 0.0,
            "core_positive_pixels": 0, "edge_positive_pixels": 0}

def is_epsg3006(crs):
    # Some source GeoTIFFs expose a complete WKT authority EPSG:3006 but
    # rasterio.to_epsg() returns None (observed for SGD2 in the native audit).
    wkt = crs.to_wkt()
    return crs.to_epsg() == 3006 or (
        'AUTHORITY["EPSG","3006"]' in wkt and
        'SWEREF99 TM' in wkt
    )

def evaluate(nmd_path: Path, boundary, sgd2_url: str):
    stats = {name: new_counter() for name in CLASSES}
    seen = Counter()
    with rasterio.Env(**ENV), rasterio.open("/vsicurl/" + sgd2_url) as bio, rasterio.open(nmd_path) as land:
        if not bio.crs or not land.crs:
            raise ValueError("Source CRS missing")
        if not bio.crs.is_projected or not land.crs.is_projected:
            raise ValueError("Both rasters must have projected CRS")
        # Product v1.1 should use EPSG:3006. Fail on unexpected CRS, do not guess.
        if not is_epsg3006(bio.crs) or not is_epsg3006(land.crs):
            raise ValueError(f"Unexpected CRS: SGD2 {bio.crs} / NMD {land.crs}")
        if abs(bio.res[0] - 10) > 0.01 or abs(bio.res[1] - 10) > 0.01:
            raise ValueError("SGD2 native resolution is not 10m")
        if abs(land.res[0] - 10) > 0.01 or abs(land.res[1] - 10) > 0.01:
            raise ValueError("NMD native resolution is not 10m")
        projected = transform_geometry(Transformer.from_crs("EPSG:4326", bio.crs, always_xy=True).transform, boundary)
        w = from_bounds(*projected.bounds, transform=bio.transform).round_offsets().round_lengths()
        w = w.intersection(Window(0, 0, bio.width, bio.height))
        extent = {"crs_sgd2": str(bio.crs), "crs_nmd": str(land.crs),
                  "sgd2_nodata": bio.nodata, "nmd_nodata": land.nodata,
                  "sgd2_scale": bio.scales[0], "sgd2_offset": bio.offsets[0],
                  "sgd2_source_res": list(bio.res), "nmd_source_res": list(land.res),
                  "sgd2_native_window": [int(w.col_off), int(w.row_off), int(w.width), int(w.height)],
                  "nmd_metadata": {"dtype": land.dtypes[0], "tags": land.tags(), "band_tags": land.tags(1)}}
        matched_nmd = 0
        valid_sgd2 = 0
        # Rasterio VRT fully reprojects/resamples the categorical NMD raster
        # onto the *whole native SGD2 grid*, never just transformed corners.
        with WarpedVRT(land, crs=bio.crs, transform=bio.transform,
                       width=bio.width, height=bio.height,
                       resampling=Resampling.nearest) as nmd:
            for row in range(int(w.row_off), int(w.row_off+w.height), BLOCK):
                for col in range(int(w.col_off), int(w.col_off+w.width), BLOCK):
                    h = min(BLOCK, int(w.row_off+w.height)-row)
                    width = min(BLOCK, int(w.col_off+w.width)-col)
                    tile = Window(col, row, width, h)
                    # One-cell halo detects uncertain class boundaries, also
                    # across tile edges. Core means 8 adjacent NMD pixels agree.
                    halo = Window(max(0,col-1), max(0,row-1),
                                  min(bio.width,col+width+1)-max(0,col-1),
                                  min(bio.height,row+h+1)-max(0,row-1))
                    b = bio.read(1, window=tile, masked=True)
                    nm = nmd.read(1, window=halo, masked=True)
                    offy, offx = row-int(halo.row_off), col-int(halo.col_off)
                    a = nm.data[offy:offy+h, offx:offx+width]
                    nmask = np.ma.getmaskarray(nm)[offy:offy+h,offx:offx+width]
                    inside = geometry_mask([mapping(projected)], out_shape=b.shape,
                                           transform=bio.window_transform(tile), invert=True)
                    validbio = inside & ~np.ma.getmaskarray(b) & np.isfinite(b.data) & (b.data>=0)
                    valid = validbio & ~nmask
                    valid_sgd2 += int(validbio.sum())
                    matched_nmd += int(valid.sum())
                    if not valid.any():
                        continue
                    keys,counts = np.unique(a[valid],return_counts=True)
                    seen.update({int(k):int(c) for k,c in zip(keys,counts)})
                    for name,codes in CLASSES.items():
                        hit = valid & np.isin(a,codes)
                        pos = hit & (b.data>0)
                        npos = int(pos.sum())
                        rec = stats[name]
                        rec["eligible_pixels"] += int(hit.sum())
                        rec["positive_pixels"] += npos
                        rec["zero_pixels"] += int((hit & (b.data==0)).sum())
                        if not npos: continue
                        values = b.data[pos]
                        rec["raw_positive_sum"] += float(values.astype("float64").sum())
                        rec["max_positive_raw"] = max(rec["max_positive_raw"], float(values.max()))
                        # For each detected candidate, inspect 8 adjacent NMD
                        # cells. Near file boundaries lack of halo means "edge".
                        stable = np.ones((h,width), dtype=bool)
                        for dy in (-1,0,1):
                            for dx in (-1,0,1):
                                if dy==dx==0: continue
                                ys=offy+dy;xs=offx+dx
                                if ys<0 or xs<0 or ys+h>nm.shape[0] or xs+width>nm.shape[1]:
                                    stable[:] = False
                                    continue
                                neighbour = nm.data[ys:ys+h, xs:xs+width]
                                masked = np.ma.getmaskarray(nm)[ys:ys+h,xs:xs+width]
                                stable &= (~masked) & np.isin(neighbour,codes)
                        core = int((pos & stable).sum())
                        rec["core_positive_pixels"] += core
                        rec["edge_positive_pixels"] += npos-core
    area_ha = abs(bio.transform.a*bio.transform.e - bio.transform.b*bio.transform.d)/10000
    return {"metadata": extent, "valid_sgd2_pixels": valid_sgd2, "valid_joint_pixels": matched_nmd,
            "native_cell_area_ha": area_ha, "nmd_class_counts_on_joint_pixels": dict(sorted(seen.items())),
            "categories": stats}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--nmd",help="Verified local NMD2018 Norrbotten TIFF (skips download)")
    parser.add_argument("--biomass",default=SGD2_URL,help="Original SGD2 GeoTIFF HTTP URL")
    parser.add_argument("--output",default=str(ROOT/"metadata/nmd2018_biomass_lulea_audit.json"))
    args=parser.parse_args()
    fc=json.loads((ROOT/"docs/data/lulea_boundary.geojson").read_text(encoding="utf-8"))
    # GeoJSON without explicit CRS is by convention WGS84; project policy
    # requires the supplied working geometry to explicitly specify EPSG:4326.
    if fc.get("crs",{}).get("properties",{}).get("name")!="EPSG:4326":
        raise ValueError("Boundary CRS not explicitly EPSG:4326")
    boundary=shape(fc["features"][0]["geometry"])
    if not boundary.is_valid: raise ValueError("Boundary geometry invalid")
    nmd_path = Path(args.nmd) if args.nmd else download_nmd(ROOT/"metadata/nmd_source")
    payload={"checked_at_utc":datetime.now(timezone.utc).isoformat(),
             "biomass_source":args.biomass,"nmd_source":NMD_URL if not args.nmd else str(nmd_path),
             "nmd_edition":"NMD2018 ogeneraliserat basskikt v1.1, Norrbottens lan",
             "class_code_source":"Naturvardsverket NMD2018 basskikt produktbeskrivning",
             "class_codes":CLASSES,
             "boundary":"docs/data/lulea_boundary.geojson","boundary_crs":"EPSG:4326",
             "boundary_status":"working geometry, not verified official municipal boundary",
             "no_original_raster_modified":True,
             "no_automatic_masking":True,
             "raw_values_unit_status":"NOT verified as ton TS/ha in exact downloaded GeoTIFF",
             "results":evaluate(nmd_path,boundary,args.biomass)}
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for k,v in payload["results"]["categories"].items():
        print(f"{k}: {v['positive_pixels']} positive, of which {v['core_positive_pixels']} interior; raw sum {v['raw_positive_sum']}", flush=True)
    print(f"Saved report: {output}",flush=True)
if __name__=="__main__":main()
