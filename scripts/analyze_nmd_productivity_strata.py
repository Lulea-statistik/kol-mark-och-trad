#!/usr/bin/env python3
"""Compare three biomass products within fixed NMD productivity classes.

INPUT CONTRACT: all rasters must be SOURCE-CRS MUNICIPAL CLIPS produced by an
upstream checked source-CRS crop. This script never assumes a CRS or georeferences
from transformed bounds. Full grids are warped to an EPSG:3006 25m analysis grid.

The NMD productivity classification is a present-day STRATIFICATION, not
evidence of historical land class in 2010, 2015, or 2018.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window


def classify_and_summarise(args):
    rasters = {"2010": args.biomass_2010, "2015": args.biomass_2015,
               "2018": args.biomass_2018, "nmd": args.nmd}
    expected_epsg = {"2010": 3021, "2015": 3006, "2018": 3006}
    with ExitStack() as stack:
        sources = {k: stack.enter_context(rasterio.open(p)) for k, p in rasters.items()}
        for year, epsg in expected_epsg.items():
            src = sources[year]
            if src.crs is None or src.crs.to_epsg() != epsg or src.count != 1:
                raise ValueError(f"{year} source metadata/CRS differs from verified raster convention")
            if src.nodata is None:
                raise ValueError(f"{year} has no declared NoData")
        nmd = sources["nmd"]
        if nmd.crs is None or nmd.nodata is None:
            raise ValueError("NMD source CRS and NoData must be explicit")
        if args.nmd_band < 1 or args.nmd_band > nmd.count:
            raise ValueError("NMD band is not present (default requires original 10-band image)")
        grid = stack.enter_context(rasterio.open(args.grid_reference))
        if grid.crs is None or grid.crs.to_epsg() != 3006:
            raise ValueError("Reference analysis grid must use EPSG:3006")
        if abs(grid.transform.a - 25) > 1e-8 or abs(grid.transform.e + 25) > 1e-8 or abs(grid.transform.b) > 1e-8 or abs(grid.transform.d) > 1e-8:
            raise ValueError("Expected aligned 25m square analysis cells")
        vrts = {}
        for name, src in sources.items():
            vrts[name] = stack.enter_context(WarpedVRT(
                src, crs=grid.crs, transform=grid.transform,
                width=grid.width, height=grid.height,
                resampling=Resampling.nearest if name == "nmd" else Resampling.average
            ))
        classes = {"0": "ovrig_mark", "1": "produktiv_skogsmark",
                   "2": "improduktiv_skogsmark"}
        totals = {key: {"cells": 0, "sums": {y: 0.0 for y in expected_epsg}} for key in classes}
        unclassified = 0
        all_cells = 0
        for row in range(0, grid.height, 256):
            for col in range(0, grid.width, 256):
                window = Window(col, row, min(256, grid.width-col), min(256, grid.height-row))
                grid_mask = grid.read(1, window=window, masked=True)
                if not np.any(~np.ma.getmaskarray(grid_mask)):
                    continue
                values = {y: vrts[y].read(1, window=window, masked=True)
                          for y in expected_epsg}
                valid = ~np.ma.getmaskarray(grid_mask)
                for a in values.values():
                    valid &= ~np.ma.getmaskarray(a)
                    valid &= np.isfinite(a.data) & (a.data >= 0)
                nm = vrts["nmd"].read(args.nmd_band, window=window, masked=True)
                valid &= ~np.ma.getmaskarray(nm)
                valid &= np.isfinite(nm.data)
                n = int(valid.sum())
                all_cells += n
                for category in classes:
                    selection = valid & (nm.data == int(category))
                    count = int(selection.sum())
                    totals[category]["cells"] += count
                    for year in expected_epsg:
                        totals[category]["sums"][year] += float(values[year].data[selection].sum(dtype="float64"))
                unclassified += n - sum(int((valid & (nm.data == int(k))).sum()) for k in classes)
        if not all_cells:
            raise ValueError("No jointly valid analysis cells - check clips, grid and source alignment")
    report = {"status": "DESCRIPTIVE_NMD_STRATIFICATION_NOT_HARMONIZED",
              "generated_utc": datetime.now(timezone.utc).isoformat(),
              "source_paths": {k: str(v) for k, v in rasters.items()},
              "nmd_band": args.nmd_band, "nmd_class_year_note": args.nmd_year,
              "analysis_grid": str(args.grid_reference),
              "analysis_crs": "EPSG:3006", "pixel_m": 25, "cell_area_ha": 0.0625,
              "jointly_valid_cells": all_cells,
              "unclassified_nmd_cells": unclassified,
              "strata": []}
    overall_sums = {year: sum(totals[k]["sums"][year] for k in classes) for year in expected_epsg}
    for category, label in classes.items():
        n = totals[category]["cells"]
        means = {year: totals[category]["sums"][year]/n if n else None for year in expected_epsg}
        report["strata"].append({
            "class": int(category), "name": label, "cells": n,
            "area_ha": n * 0.0625, "share_of_joint_cells": n/all_cells,
            "biomass_raw_means": means,
            "mean_2010_minus_2015": means["2010"]-means["2015"] if n else None,
            "share_of_classified_sum_difference_2010_minus_2015":
                (totals[category]["sums"]["2010"]-totals[category]["sums"]["2015"])/
                (overall_sums["2010"]-overall_sums["2015"])
                if overall_sums["2010"] != overall_sums["2015"] else None})
    report["limitations"] = [
        "NMD is a fixed reference classification, not measured 2010 forest productivity",
        "Analysis grid must itself be the verified common-cell 2010/2015/2018 mask",
        "Biomass products have unequal definitions (2010 includes belowground material)",
        "Raster raw values are not yet harmonised physical biomass units",
        "Input source windows must have been clipped in their own validated source CRS",
        "Nearest-neighbour resampling is required for categorical NMD"
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--biomass-2010", type=Path, required=True)
    parser.add_argument("--biomass-2015", type=Path, required=True)
    parser.add_argument("--biomass-2018", type=Path, required=True)
    parser.add_argument("--nmd", type=Path, required=True, help="Preclipped original NMD/SGD multiband raster")
    parser.add_argument("--nmd-band", type=int, default=10, help="1-based TIFF band number; not zero-based ArcGIS BandIds")
    parser.add_argument("--nmd-year", required=True, help="Verified NMD classification version/year")
    parser.add_argument("--grid-reference", type=Path, required=True, help="Validated EPSG:3006 25m 3-year common-cell mask raster")
    parser.add_argument("--output", type=Path, default=Path("nmd_productivity_diagnostics.json"))
    classify_and_summarise(parser.parse_args())
