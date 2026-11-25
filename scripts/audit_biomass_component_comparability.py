#!/usr/bin/env python3
"""Evidence-based variable crosswalk for biomass 2010, 2015 and SGD2 2018.

This audit evaluates *definitions*, not maps, relative model bias or forest
stock change. An unspecified foliage component must remain UNKNOWN.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from audit_biomass_units_and_mass_gate import SRC

SOURCE_REFERENCE={
 "2010":{"type":"direct SLU source expert correspondence provided by project owner",
  "date":"2026-11-25","exact_file":"BIOMASS_XX_P_10.tif"},
 "2015":{"type":"SLU Skogskarta 2015 product description",
  "url":"https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/raster-slu-skogskarta---produktbeskrivning.pdf",
  "page_1_based":3,
  "specific_layer_identity":"https://gis.slu.se/data/slu_forest_map/2015/data/Biomass_leaf.tif",
  "evaluation":"https://gis.slu.se/data/slu_forest_map/2015/docs/EvaluateSLUSkogskarta.pdf",
  "evaluation_section":"Total biomassa (ovan jord), Biomass_leaf, BiomassAbo"},
 "2018":{"type":"Skogliga grunddata (laser, omdrev 2) product description",
  "url":"https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/skogliga-grunddata/skogliga-grunddata-220701---produktbeskrivning.pdf",
  "page_1_based":3,
  "specific_layer_identity":"https://gis.slu.se/data/slu_skogliga_grunddata/SGD2/data/SGD2_BIO.tif"}
}
def audit(src=SRC):
    expected={"2010","2015","2018"}
    if set(src)!=expected:raise ValueError("Expected exact archived 2010, 2015, 2018 series")
    for year,desc in src.items():
        if desc.get("unit")!="tonne dry matter per hectare (tTS/ha)":
            raise ValueError("Missing physical unit documentation "+year)
        comp=desc.get("components","")
        for keyword in ("branches","no stumps","roots"):
            if keyword not in comp:raise ValueError("Missing explicit above-stump components "+year)
        if desc.get("needles_included") not in (True,False,None) or desc.get("deciduous_leaves_included") not in (True,False,None):
            raise ValueError("Unexpected foliage tri-state "+year)
    if src["2010"]["needles_included"] is not True or src["2010"]["deciduous_leaves_included"] is not False:
        raise ValueError("User provided SLU 2010 response not faithfully represented")
    for year in ("2015","2018"):
        if src[year]["needles_included"] is not None or src[year]["deciduous_leaves_included"] is not None:
            raise ValueError("Later product leaves/needles require exact independent evidence before unblocking")
        if "below 3 m" not in src[year]["height_zero_rule"]:
            raise ValueError("Expected documented 3m height zero rule "+year)
    return {
        "status":"PHYSICAL_UNITS_CONFIRMED_FOLIAGE_AND_MODEL_EQUIVALENCE_UNRESOLVED",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "comparability":{
            "tonnes_dry_matter_per_hectare_same_unit":True,
            "above_stump_wood_branches_tops_common_to_product_descriptions":True,
            "no_stumps_or_roots_common_to_product_descriptions":True,
            "same_conifer_needles_inclusion_all_years":None,
            "same_deciduous_leaves_inclusion_all_years":None,
            "same_height_based_zero_rule_all_years":None,
            "same_estimation_method_all_years":False,
            "same_geographic_sampling_dates_all_years":False,
            "verified_method_harmonized_time_change":False},
        "sources":SOURCE_REFERENCE,
        "records":src,
        "policy":{
          "allow_per_year_masked_tonnes":True,
          "allow_label_2010_2018_percent_as_physically_harmonized":False,
          "allow_2010_or_2018_mass_automatic_correction":False,
          "require_historic_forest_mask_review":True,
          "require_2015_and_2018_foliage_confirmation":True
        },
        "review_questions":[
            "For exact SLU 2015 Biomass_leaf.tif, are conifer needles included and broadleaf leaves excluded? Which biomass functions are used?",
            "For exact SGD2 omdrev-2 SGD2_BIO.tif, are conifer needles included and broadleaf leaves excluded? Which biomass functions are used?",
            "What exactly is 2010 biomass/volume zero rule for heights below three metres, and is it comparable to 2015 and SGD2?",
            "Do 2015 and SGD2 use seasonally different height or deciduous-leaf assumptions affecting sample plots or models?"
        ]}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("metadata/biomass_2010_2015_2018_component_comparability.json"))
    args=p.parse_args()
    result=audit()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"comparability":result["comparability"]},ensure_ascii=False))
if __name__=="__main__":main()
