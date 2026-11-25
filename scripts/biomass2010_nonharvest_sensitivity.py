#!/usr/bin/env python3
"""Sensitivity only: NO validated correction of 2010 forest biomass.

The intervention domain is *only* 2010 modelled volume >= 100 in
NMD2018 temporary-not-forest 118/128 *without* a 2011-2018 recorded
harvest intersection. Harvest-intersecting cells are explicitly frozen.

The absence of registered harvesting does not prove the absence of harvest.
No physical units, carbon conversion, or reconstructed pixel raster.
"""
from __future__ import annotations
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

FRACTIONS=(0.0,0.25,0.50,1.0)
YEARS=("2010","2015","2018")
def analyze(reference, harvest):
    if reference.get("status")!="VERIFIED_2026_11_25_RAW_REFERENCE_FROM_PR99_PR101":
        raise ValueError("Input reference is not the explicitly verified raw-values baseline")
    if reference.get("analysis_crs")!="EPSG:3006" or reference.get("resolution_m")!=25:
        raise ValueError("Baseline CRS/resolution mismatch")
    if harvest.get("comparison_grid_crs")!="EPSG:3006" or harvest.get("grid_resolution_m")!=25:
        raise ValueError("Harvest CRS/resolution mismatch")
    if harvest.get("nmd_base_codes")!=[118,128]:
        raise ValueError("Target must be NMD2018 BASE 118/128, not productivity=0")
    if harvest.get("focus_cells")!=reference["temporary_not_forest"]["cells"]:
        raise ValueError("Target common-valid population mismatch")
    if not math.isclose(harvest["raw_delta_2010_2018"],
            reference["temporary_not_forest"]["raw_difference_2010_minus_2018"],
            rel_tol=1e-9):
        raise ValueError("Raw delta no longer reconciles with PR101")
    hi=harvest["high_volume_harvest_periods"]
    lo=harvest["low_volume_harvest_periods"]
    keys={"not_recorded","harvest_2011_2015","harvest_2016_2018","both_periods"}
    if set(hi)!=keys or set(lo)!=keys:
        raise ValueError("Harvest flags are not mutually exclusive/complete")
    if sum(v["cells"] for v in hi.values())!=119269:
        raise ValueError("High volume 2010 population differs from PR101")
    if sum(v["cells"] for v in lo.values())+sum(v["cells"] for v in hi.values())+harvest["focus_unmatched_2010_volume_cells"]!=harvest["focus_cells"]:
        raise ValueError("Volume coverage partition mismatch")
    remaining=hi["not_recorded"]
    recorded=[v for k,v in hi.items() if k!="not_recorded"]
    sum2010=sum(v["sum_raw"]["2010"] for v in hi.values())
    sum2018=sum(v["sum_raw"]["2018"] for v in hi.values())
    delta=sum2010-sum2018
    expected=harvest["high_volume_raw_delta_2010_2018"]
    if not math.isclose(delta,expected,rel_tol=1e-9):
        raise ValueError("High volume raw difference not conserved")
    residual=float(remaining["delta_2010_2018"])
    if not math.isclose(residual,remaining["sum_raw"]["2010"]-remaining["sum_raw"]["2018"],rel_tol=1e-9):
        raise ValueError("Unrecorded delta mismatch")
    recorded_delta=sum(v["delta_2010_2018"] for v in recorded)
    if not math.isclose(recorded_delta+residual,delta,rel_tol=1e-9):
        raise ValueError("Harvest overlaps violate conservation")
    if residual<=0:raise ValueError("Expected positive residual, sensitivity needs redesign")
    base=float(reference["raw_pixel_sums"]["2010"])
    out=[]
    for fraction in FRACTIONS:
        removed=fraction*residual
        candidate=base-removed
        out.append({
          "assumed_fraction_of_unrecorded_high_volume_net_raw_difference_treated_as_method_artifact":fraction,
          "sensitivity_removed_raw_pixel_sum":removed,
          "illustrative_2010_common_area_raw_sum":candidate,
          "2010_minus_2018_common_area_raw_delta_after_assumed_removal":candidate-reference["raw_pixel_sums"]["2018"],
          "recorded_harvest_2010_values_untouched":True,
          "can_publish_as_corrected_biomass_stock":False
        })
    return {
      "status":"EXPLORATORY_NONCAUSAL_SENSITIVITY_ONLY_NOT_A_CORRECTED_TOTAL",
      "generated_utc":datetime.now(timezone.utc).isoformat(),
      "source_reference":"metadata/biomass2010_sensitivity_baseline_20261125.json",
      "harvest_source":harvest.get("harvest_layer_rest"),
      "grid":{"crs":"EPSG:3006","pixel_size_m":25,"common_valid_cells":reference["common_cells"]},
      "observations":{
        "2010_common_area_raw_sum":base,
        "2015_common_area_raw_sum":reference["raw_pixel_sums"]["2015"],
        "2018_common_area_raw_sum":reference["raw_pixel_sums"]["2018"],
        "temporary_not_forest_raw_difference":harvest["raw_delta_2010_2018"],
        "temporary_not_forest_high_volume_raw_difference":delta,
        "registered_harvest_high_volume_raw_difference_UNMODIFIED":recorded_delta,
        "no_registered_harvest_high_volume_cells":remaining["cells"],
        "no_registered_harvest_high_volume_area_ha":remaining["cells"]*.0625,
        "no_registered_harvest_high_volume_2010_raw_sum":remaining["sum_raw"]["2010"],
        "no_registered_harvest_high_volume_2018_raw_sum":remaining["sum_raw"]["2018"],
        "no_registered_harvest_high_volume_raw_difference":residual,
        "no_registered_harvest_is_not_proof_of_no_harvest":True,
        "fraction_of_2010_total_raw_at_max_sensitivity_percent":100*residual/base,
      },
      "scenarios":out,
      "biomass_2010_tonnes":None,
      "normalized_biomass_component_comparison_2010_2018":None,
      "scientific_verdict":"No fraction has been identified as a method error; these numbers are sensitivity envelopes, not a best estimate.",
      "methodology_notes":[
        "Neither 2010 vegetation cover nor valid 2010 biomass unit/component has been independently verified for the exact archived TIFF.",
        "A 2011-2018 harvest polygon overlap is associated with change, not proof of causal contribution or 2010 model accuracy.",
        "No registered harvest can mean data omissions, unreported operations, and timing issues; scenario fractions are wholly hypothetical.",
        "Even recorded-harvest locations could have model-method bias; freezing them is a conservative modelling choice, not a proof of absence of bias.",
        "Subtracting group NET differences can conceal positive/negative individual-pixel differences; it is only an aggregate hypothetical, not a cell-level correction.",
        "NoData never converted to zero. 2015/2018 and source forest-only masks remain unchanged.",
        "SLU 2010 historically may report biomass including underground components and in kg/ha, unlike 2015/2018. Verify archived source preprocessing before ANY physical estimate.",
        "No spatial changes to original biomass rasters or logging geometry are undertaken."
      ]
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",type=Path,default=Path("metadata/biomass2010_sensitivity_baseline_20261125.json"))
    p.add_argument("--harvest",type=Path,default=Path("metadata/nmd2018_temporary_not_forest_harvest_2011_2018.json"))
    p.add_argument("--output",type=Path,default=Path("metadata/biomass2010_nonharvest_sensitivity.json"))
    a=p.parse_args()
    d=analyze(json.loads(a.baseline.read_text(encoding="utf-8")),json.loads(a.harvest.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(d,ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":main()
