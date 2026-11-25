#!/usr/bin/env python3
"""Separate mass-unit conversion from area harmonization, with explicit gates.

The exact 2010 SLU TIFF's dry matter tonnes per hectare and biomass
components were confirmed directly by SLU via correspondence 2026-11-25.
The three products have source-supported mass units, but identical tree
components and model definitions across years are not established. This script cannot be used to infer that
a similar number of raw values implies equivalent physical stock.
"""
from __future__ import annotations
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

SRC={
 "2015":{
  "category":"SLU Skogskarta 2015 biomass",
  "unit":"tonne dry matter per hectare (tTS/ha)",
  "components":"stem wood, branches and tops; no stumps or roots; inclusion of needles and deciduous leaves not explicitly established",
  "height_zero_rule":"ground-area-weighted mean tree height below 3 m is set to zero in all product rasters",
  "needles_included":None,"deciduous_leaves_included":None,
  "estimation_basis":"SLU NFI field plots + stereo aerial photo surface models + Sentinel-2 imagery; imagery dates may vary",
  "evidence_url":"https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/raster-slu-skogskarta---produktbeskrivning.pdf",
  "evidence_page":3,
  "status":"DOCUMENTED_PRODUCT_DEFINITION_WITH_UNRESOLVED_FOLIAGE_RULE"},
 "2018":{
  "category":"Skogliga grunddata 2018 biomass (omdrev 2)",
  "unit":"tonne dry matter per hectare (tTS/ha)",
  "components":"stem wood, branches and tops; no stumps or roots; inclusion of needles and deciduous leaves not explicitly established",
  "height_zero_rule":"ground-area-weighted mean tree height below 3 m is set to zero in product rasters; verify transfer to exact SGD2 10m omdrev-2 raster",
  "needles_included":None,"deciduous_leaves_included":None,
  "estimation_basis":"SLU NFI field plots + national laser scanning; acquisition date varies spatially",
  "evidence_url":"https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/skogliga-grunddata/skogliga-grunddata-220701---produktbeskrivning.pdf",
  "evidence_page":3,
  "status":"DOCUMENTED_PRODUCT_DEFINITION"},
 "2010":{
  "category":"SLU Skogskarta 2010 exact BIOMASS_XX_P_10.tif",
  "unit":"tonne dry matter per hectare (tTS/ha)",
  "components":"whole tree above stump cut incl. branches; conifer needles included; deciduous leaves excluded; no stumps or roots",
  "source_raster":"https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/BIOMASS_XX_P_10.tif",
  "evidence_kind":"direct source producer response quoted by project user 2026-11-25; Mats, SLU",
  "method_reference":"Marklund, L.G. (1988). Biomassafunktioner för tall, gran och björk i Sverige. SLU, Institutionen för skogstaxering, Rapport 45.",
  "needles_included":True,"deciduous_leaves_included":False,
  "height_zero_rule":None,
  "estimation_basis":"SLU forest map 2010; modelling and zero rule not established equivalent to later products",
  "evidence_url":None,
  "evidence_page":None,
  "status":"SOURCE_PRODUCER_CONFIRMED_EXACT_RASTER_2026_11_25"}
}

def compute(d):
    if d["status"]!="RAW_UNIT_COMMON_AREA_HARMONIZATION_ONLY_NO_PHYSICAL_UNIT_CORRECTION":
        raise ValueError("Unexpected input status: physical unit conversion requires raw, uncalibrated totals")
    if d["analysis_crs"]!="EPSG:3006" or d["pixel_size_m"]!=25:
        raise ValueError("Area summation grid not verified as complete EPSG:3006 25m raster")
    if not math.isclose(d["cell_area_ha"],0.0625,abs_tol=1e-12):
        raise ValueError("Unexpected target pixel area")
    options=d["comparison_sum_options"]
    view={}
    for key,row in options.items():
        if not row.get("comparable_area") or row.get("physical_unit_harmonized"):
            raise ValueError("Only raw common-area options may be considered")
        vals=row["raw_sums_pixel_units"]
        if set(vals)!={"2010","2015","2018"}:raise ValueError("Missing year")
        out_year={}
        for year in ("2010","2015","2018"):
            raw=float(vals[year])
            if not math.isfinite(raw) or raw<0:raise ValueError("Invalid raw pixel sum")
            out_year[year]={
              "raw_pixel_sum":raw,
              "tonnes_dry_matter":raw*d["cell_area_ha"],
              "physical_conversion_status":(
                 "SOURCE_PRODUCER_CONFIRMED_2010_UNIT_ARCHIVED_CLIP_PROVENANCE_CONDITIONAL"
                 if year=="2010" else
                 "DOCUMENTED_PRODUCT_UNIT_CONDITIONAL_ON_ARCHIVED_CLIP_PROVENANCE"),
              "same_component_and_model_as_other_years_verified":False
            }
        view[key]={
            "scope":row["scope"],"cells":row["cells"],"area_ha":row["area_ha"],
            "per_year":out_year,
            "caveat":"Physical 2015 and 2018 figures are 25m-grid pixel-area integrals, not independent field-validated stocks. Include landcover and source coverage in caption."
        }
        for year in ("2010","2015","2018"):
            if not math.isclose(row["cells"]*.0625,row["area_ha"],rel_tol=1e-12):
                raise ValueError("Pixel count and area mismatch")
    return {
      "status":"PHYSICAL_MASS_2010_CONVERSION_SOURCE_CONFIRMED_TEMPORAL_COMPARABILITY_NOT_VERIFIED",
      "created_utc":datetime.now(timezone.utc).isoformat(),
      "source_analysis":"metadata/biomass2010_harmonized_comparison.json",
      "foliage_component_equivalence_verified":False,
      "zero_height_rule_equivalence_verified":False,
      "cross_year_estimation_method_equivalence_verified":False,
      "units_and_components":SRC,
      "candidate_mass_by_common_mask":view,
      "limitations":[
        "2010 physical tTS/ha and above-stump definition confirmed by SLU for exact TIFF on 2026-11-25; archived clip identity and resampling remain required.",
        "2010 conifer needles included, deciduous leaves excluded; the exact leaf rules of 2015 and 2018 and methods have NOT been confirmed equivalent.",
        "2015 SLU Skogskarta uses aerial imagery + Sentinel-2; 2018 SGD2 uses laser scanning; their published product documentation sets values to zero when weighted mean tree height is below 3 m.",
        "2010 height-based zero rule is not confirmed equivalent; 2015 vs 2018 tree needles and deciduous leaves are not explicitly resolved by the cited product summaries.",
        "The 2018 product describes its laser acquisition date, verified locally as 2018, not necessarily 2018-01-01.",
        "Masses for 2015/2018 assume GitHub archived rasters match the named original products and have not been scaled after retrieval; source-provenance audit still needed.",
        "Common-forest NMD2018 mask is 2018 land cover, not an accurate historic forest classification in 2010.",
        "Documented 2015/2018 biomass includes stemwood, branches, tops and excludes stumps/roots; foliage component equivalence remains unknown.",
        "Physical tonnes within a specified common-valid mask are allowed; do not mislabel these as total municipality stock, model-corrected biomass or a verified comparable 2010-2018 physical change.",
        "Do not force 2010 totals to equal 2015 or 2018 or impute missing 2010 pixels by assuming zero."
      ]
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("metadata/biomass2010_harmonized_comparison.json"))
    p.add_argument("--output",type=Path,default=Path("metadata/biomass_unit_mass_gate.json"))
    a=p.parse_args()
    d=json.loads(a.input.read_text(encoding="utf-8"))
    result=compute(d)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for key,row in result["candidate_mass_by_common_mask"].items():
        print(key,json.dumps(row["per_year"],ensure_ascii=False))
    print("2010 tonnes dry mass converted from source-confirmed tTS/ha. Cross-year component and model comparability NOT verified.")

if __name__=="__main__": main()
