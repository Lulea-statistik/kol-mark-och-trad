#!/usr/bin/env python3
"""Direct standardization of modeled biomass ratios by age and 2010 volume.

Input is the already-verified aggregated EPSG:3006 25m raster result, not
invented per-cell measurements. The target age-volume distribution is pooled
across ALL nine spruce/pine classes in shared-support strata.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def compute(source: dict, threshold: int = 30) -> dict:
    if not isinstance(threshold, int) or threshold < 1:
        raise ValueError("minimum cell count must be >=1")
    if source["analysis_crs"] != "EPSG:3006" or source["cell_m"] != 25:
        raise ValueError("Verified grid must use EPSG:3006 and 25 m")
    control = source["age_volume_control"]
    counts = np.asarray(control["cells_by_age_volume_balance"], dtype="int64")
    masses = {year: np.asarray(control["mass_tTS_by_age_volume_balance"][year], dtype="float64")
              for year in ("2010", "2015", "2018")}
    if counts.shape != (6, 5, 9) or any(v.shape != counts.shape for v in masses.values()):
        raise ValueError("Unexpected age-volume balance dimensions")
    if (counts < 0).any() or any((v < 0).any() or not np.isfinite(v).all() for v in masses.values()):
        raise ValueError("Invalid raster population or biomass values")
    if int(counts.sum()) != control["population_cells"]:
        raise ValueError("Input population mismatch")
    baseline = source["cohorts"]["age_ge20"]
    if counts.sum(axis=(0, 1)).tolist() != baseline["col_2010_cells"]:
        raise ValueError("Input does not reconcile with 2010 balance groups")
    for year in masses:
        if not np.allclose(masses[year].sum(axis=(0, 1)),
                           np.asarray(baseline["2010_balance_class_mass_tTS"][year]),
                           rtol=1e-9, atol=.02):
            raise ValueError("Input dry-mass totals do not reconcile")
    # Require ALL classes to have positive and sufficient data in the SAME strata.
    common = np.all(counts >= threshold, axis=2)
    supported = np.argwhere(common)
    if len(supported) == 0:
        raise ValueError("No age-volume strata with sufficient shared support")
    weights = counts.sum(axis=2).astype("float64") * common
    weights /= weights.sum()
    standardized = {}
    coverage = []
    for j, label in enumerate(source["axis_classes_gran_tall"]):
        total_n = int(counts[:, :, j].sum())
        shared_n = int(counts[:, :, j][common].sum())
        if shared_n < 1:
            raise ValueError("Missing class support")
        denom = np.where(counts[:, :, j] > 0, .0625 * counts[:, :, j], 1)
        density = {year: float(np.sum(weights * masses[year][:, :, j] / denom))
                   for year in masses}
        raw_mass = {year: float(masses[year][:, :, j].sum()) for year in masses}
        shared_mass = {year: float(masses[year][:, :, j][common].sum()) for year in masses}
        if density["2010"] <= 0 or shared_mass["2010"] <= 0 or raw_mass["2010"] <= 0:
            raise ValueError("Zero denominator in biomass comparison")
        standardized[label] = {
            "total_cells": total_n,
            "shared_cells": shared_n,
            "coverage_percent": 100 * shared_n / total_n,
            "raw_2018_vs_2010_percent": 100 * (raw_mass["2018"] / raw_mass["2010"] - 1),
            "shared_unstandardized_percent": 100 * (shared_mass["2018"] / shared_mass["2010"] - 1),
            "standardized_2018_vs_2010_percent": 100 * (density["2018"] / density["2010"] - 1),
            "standardized_density_tTS_per_ha": density,
        }
        coverage.append(100 * shared_n / total_n)
    return {
        "status": "DERIVED_FROM_VERIFIED_AGGREGATED_RASTER",
        "analysis_crs": "EPSG:3006",
        "cell_m": 25,
        "axis_classes_gran_tall": source["axis_classes_gran_tall"],
        "threshold_min_cells_per_balance_class_in_each_stratum": threshold,
        "common_support_strata_count": int(common.sum()),
        "total_possible_strata": 30,
        "common_support_strata": [
            {"age_2010": control["age_bins"][int(a)],
             "total_volume_2010": control["volume_2010_bins"][int(v)],
             "pooled_cells_all_classes": int(counts[a, v].sum()),
             "standard_weight": float(weights[a, v])}
            for a, v in supported
        ],
        "standard_population_total_cells": int(counts.sum(axis=2)[common].sum()),
        "target_distribution": "Pooled cell-count age × 2010-volume distribution in common-support strata, same target for all 9 balance classes",
        "estimand": "Ratio of standardized mean dry biomass density 2018 versus 2010, not mean of cell ratios and not growth or causal species effect",
        "standardized_by_balance_class": standardized,
        "minimum_coverage_percent": float(min(coverage)),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("docs/data/gran_tall_balans_2005_2010.json"))
    p.add_argument("--output", type=Path, default=Path("docs/data/gran_tall_standardisering_2010_2018.json"))
    args = p.parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8"))
    output = compute(source, 30)
    output["sensitivity"] = {
        str(threshold): compute(source, threshold) for threshold in (10, 100)
    }
    # Sensitivity subreports avoid nested duplication of sensitivity.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("STANDARDIZATION_VERIFIED", output["common_support_strata_count"],
          output["standard_population_total_cells"],
          [(k, round(v["standardized_2018_vs_2010_percent"], 2),
            round(v["coverage_percent"], 1))
           for k, v in output["standardized_by_balance_class"].items()])


if __name__ == "__main__":
    main()
