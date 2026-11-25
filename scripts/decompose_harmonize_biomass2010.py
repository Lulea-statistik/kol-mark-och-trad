#!/usr/bin/env python3
"""Reproducible raw-unit biomass 2010-2018 decomposition and mask-harmonized sum.

This does NOT perform temporal calibration, volume-to-biomass conversion,
physical carbon stock estimation or inferred missing-data imputation.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

YEARS=("2010","2015","2018")
FOREST={"Skog utanför våtmark","Skog på våtmark"}
WATER={"Vatten"}
TEMP={"Temporärt ej skog"}
# Disjoint groups; NMD2018 is a reference classification, NOT year-2010 land cover.
PARTITIONS={
    "Skog enligt NMD2018":FOREST,
    "Temporärt ej skog enligt NMD2018":TEMP,
    "Vatten enligt NMD2018":WATER,
    "Övrig mark enligt NMD2018":{
       "Öppen våtmark","Åkermark","Övrig öppen mark","Exploaterad mark"
    }
}

def group_sum(row,year):
    return float(row["means_raw"][year])*int(row["cells"])

def calc(d):
    if d.get("analysis_CRS")!="EPSG:3006" or d.get("resolution_m")!=25:
        raise ValueError("Expected full raster reprojection to common EPSG:3006, 25m grid")
    rows=d["group_rows"]
    if sum(r["cells"] for r in rows)!=d["matched_cells"]:
        raise ValueError("Group population does not reconcile to shared common mask")
    lookup={r["group"]:r for r in rows}
    if len(lookup)!=len(rows): raise ValueError("Duplicate NMD groups")
    if set(lookup)!=set().union(*PARTITIONS.values()):
        raise ValueError("Unexpected NMD group list; update classification explicitly")
    rows_out=[]
    gross_over=0.
    gross_under=0.
    total_year={year:0. for year in YEARS}
    partition_sums={}
    for partition,names in PARTITIONS.items():
        selected=[lookup[n] for n in sorted(names)]
        count=sum(r["cells"] for r in selected)
        sums={y:sum(group_sum(r,y) for r in selected) for y in YEARS}
        for y in YEARS: total_year[y]+=sums[y]
        delta=sums["2010"]-sums["2018"]
        gross_over+=max(delta,0)
        gross_under+=min(delta,0)
        partition_sums[partition]=sums
        rows_out.append({"category":partition,"cells":count,"area_ha":count*.0625,
              "raw_sums_pixel_units":sums,"raw_delta_2010_minus_2018":delta,
              "mean_raw":{y:sums[y]/count if count else None for y in YEARS}})
    net_delta=total_year["2010"]-total_year["2018"]
    if abs(net_delta-(gross_over+gross_under))>max(1,abs(net_delta))*1e-10:
        raise ValueError("Delta partition mismatch")
    for r in rows_out:
        r["share_of_net_delta_percent"]=100*r["raw_delta_2010_minus_2018"]/net_delta if net_delta else None
        r["share_of_positive_group_delta_percent"]=100*max(r["raw_delta_2010_minus_2018"],0)/gross_over if gross_over else None
    rows_out.sort(key=lambda r:-r["raw_delta_2010_minus_2018"])
    forest=partition_sums["Skog enligt NMD2018"]
    water=partition_sums["Vatten enligt NMD2018"]
    all_without_water={y:total_year[y]-water[y] for y in YEARS}
    raw_common_total={
       "scope":"All common-valid 2010, 2015 and 2018 cells within municipality",
       "cells":d["matched_cells"],"area_ha":d["matched_cells"]*.0625,
       "raw_sums_pixel_units":total_year,
       "comparable_area":True,
       "physical_unit_harmonized":False}
    # This is a legitimate first-step area harmonization: NO MODEL CORRECTION.
    # A physical mass sum remains unavailable without verified units/compartments.
    options={
       "A_common_valid_all_NMD_groups_raw":raw_common_total,
       "B_common_valid_excluding_NMD2018_water_raw":{
           "scope":"Identical common-valid grid excluding NMD2018 water pixels",
           "cells":d["matched_cells"]-lookup["Vatten"]["cells"],
           "area_ha":(d["matched_cells"]-lookup["Vatten"]["cells"])*.0625,
           "raw_sums_pixel_units":all_without_water,
           "comparable_area":True,"physical_unit_harmonized":False},
       "C_common_valid_NMD2018_forest_only_RAW_RECOMMENDED":{
           "scope":"Identical shared-valid forest mask: NMD2018 codes 111-117,121-127 (exclude temporary not forest)",
           "cells":sum(lookup[x]["cells"] for x in FOREST),
           "area_ha":sum(lookup[x]["cells"] for x in FOREST)*.0625,
           "raw_sums_pixel_units":forest,
           "comparable_area":True,"physical_unit_harmonized":False,
           "note":"Comparable raw-value subtotal for reference forest; NOT municipality-wide biomass stock or reconstructed 2010 forest classification."}
    }
    reference=d["forest_only_NMD2018_reference"]
    if options["C_common_valid_NMD2018_forest_only_RAW_RECOMMENDED"]["cells"]!=reference["cells"]:
        raise ValueError("Forest reference count mismatch")
    for y in YEARS:
        ref_from_means=reference["means_raw"][y]*reference["cells"]
        if abs(forest[y]-ref_from_means)>max(1,abs(ref_from_means))*1e-7:
            raise ValueError("Forest subtotals differ from reference means")
    return {
      "status":"RAW_UNIT_COMMON_AREA_HARMONIZATION_ONLY_NO_PHYSICAL_UNIT_CORRECTION",
      "generated_utc":datetime.now(timezone.utc).isoformat(),
      "source_analysis":"metadata/nmd2018_landcover_biomass_volume.json",
      "analysis_crs":"EPSG:3006","pixel_size_m":25,
      "cell_area_ha":.0625,
      "source_original_epsg":{"2010":3021,"2015":3006,"2018":3006},
      "common_population_cells":d["matched_cells"],
      "raw_summation_method":"For each group: NMD2018 fixed-class cell_count * mean_raw; sum disjoint groups, on identical jointly-valid 2010/2015/2018 pixels.",
      "net_raw_delta_2010_minus_2018":net_delta,
      "gross_positive_partitions":gross_over,
      "gross_negative_partitions":gross_under,
      "decomposition_by_fixed_NMD2018_class":rows_out,
      "comparison_sum_options":options,
      "interpretation":{
        "recommended_public_2010_value":"C common-valid NMD2018 forest-only RAW subtotal, only alongside corresponding 2015/2018 sums on identical cells",
        "can_label_metric_carbon_stock_tonnes":False,
        "can_label_metric_total_municipal_biomass":False,
        "can_replace_original_2010_stock":False,
        "causal_attribution_possible":False,
        "next_gate_for_physical_tonnes":"Verify sources' exact physical variable definition, tree components, mass units, hectare basis and preprocessing; only then use units-correct cell-area weighting or separate model calibration.",
        "smd2000_status":"Not intersected with every common-valid raster cell in this artifact. SMD2000 local licensed source needed to identify temporally stable forest and to attribute actual land changes.",
        "caveats":[
           "NMD2018 is a fixed 2018 classification and does not prove 2010 landcover.",
           "Temporary-not-forest is a 2018 snapshot and may include young/regenerating forest, not necessarily a 2010 forest model defect.",
           "Raw 2010/2015/2018 products have not been demonstrated physically unit- and compartment-compatible.",
           "Selection requires valid values all three years, so it is not a complete municipal stock estimate.",
           "Group contribution shares are descriptive net decomposition, not percentages of causal responsibility.",
           "Raster NoData must not be assigned zero; no new missing biomass is imputed.",
           "2010 native raster is EPSG:3021; raw comparison reprojects COMPLETE raster grid to EPSG:3006, never just bounds."
        ]
      }
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("metadata/nmd2018_landcover_biomass_volume.json"))
    p.add_argument("--output",type=Path,default=Path("metadata/biomass2010_harmonized_comparison.json"))
    a=p.parse_args()
    d=json.loads(a.input.read_text(encoding="utf-8"))
    result=calc(d)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Reference population",result["common_population_cells"])
    print("Raw total difference",result["net_raw_delta_2010_minus_2018"])
    for k,v in result["comparison_sum_options"].items():
        print(k,json.dumps(v,ensure_ascii=False))
    for row in result["decomposition_by_fixed_NMD2018_class"]:
        print("PARTITION",json.dumps(row,ensure_ascii=False))

if __name__=="__main__": main()
