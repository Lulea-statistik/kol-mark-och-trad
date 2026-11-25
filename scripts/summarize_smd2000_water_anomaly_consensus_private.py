#!/usr/bin/env python3
"""Aggregate three licensed SMD2000 deliveries for the historic 579-cell QA subset.

Never export coordinates, cellwise labels or geometries. Counts describe a
preselected anomaly subset, NOT the prevalence of model errors municipality-wide.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from collections import Counter
from pathlib import Path
EXPECTED=("jan2012","april2012","lulea")
CLASSES=("skog","vatten","övrigt")
def run(csv_path):
    per={}
    with csv_path.open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f,delimiter=";")
        required={"variant","row3021","col3021","neighbour","centre_class",
                  "pixel_area_water_fraction","pixel_area_coverage"}
        if not required.issubset(reader.fieldnames or []):raise ValueError("Missing required licensed input columns")
        for r in reader:
            variant=r["variant"]
            if variant not in EXPECTED:raise ValueError("Unexpected SMD delivery")
            key=(int(r["row3021"]),int(r["col3021"]))
            cls=r["centre_class"]
            if cls not in CLASSES:raise ValueError("Unexpected SMD class")
            neighbour=int(r["neighbour"])
            if neighbour not in (1,2,3):raise ValueError("Unexpected NMD2018 neighbour class")
            water=float(r["pixel_area_water_fraction"])
            cov=float(r["pixel_area_coverage"])
            if not 0<=water<=cov<=1.00001:raise ValueError("Invalid SMD polygon area fractions")
            if key not in per:per[key]={}
            if variant in per[key]:raise ValueError("Duplicate cell and SMD delivery")
            per[key][variant]=(cls,neighbour,water,cov)
    if not per:raise ValueError("No input cells")
    for key,variants in per.items():
        if set(variants)!=set(EXPECTED):raise ValueError("Missing SMD delivery for matching source cell")
        if len({v[1] for v in variants.values()})!=1:raise ValueError("NMD neighbours differ across same source pixel")
    counts={v:Counter(per[k][v][0] for k in per) for v in EXPECTED}
    neighbour=Counter(next(iter(v.values()))[1] for v in per.values())
    consensus=Counter()
    agreement=0
    for v in per.values():
        classes=[v[y][0] for y in EXPECTED]
        if len(set(classes))==1:
            consensus[classes[0]]+=1
            agreement+=1
    mismatches={}
    for a,b in (("jan2012","april2012"),("jan2012","lulea"),("april2012","lulea")):
        mismatches[a+"__"+b]=sum(per[k][a][0]!=per[k][b][0] for k in per)
    water_fraction_thresholds={}
    for variant in EXPECTED:
        water_fraction_thresholds[variant]={
            "cells_50pct_or_more_water":sum(x[variant][2]>=.5 for x in per.values()),
            "cells_95pct_or_more_water":sum(x[variant][2]>=.95 for x in per.values()),
            "cells_water_at_center":counts[variant]["vatten"]}
    isolated=[v for v in per.values() if v["jan2012"][1]==3]
    stable_isolated_water=sum(all(x[var][0]=="vatten" for var in EXPECTED) for x in isolated)
    results={
        "status":"SELECTED_579_SOURCE_CELLS_PRIVATE_AGGREGATED_QA_NOT_FULL_FOREST_MASK",
        "origin":"Local user-supplied SMD2000 579 native-cell comparison CSV, 3 deliveries",
        "population_description":"SLU 2010 model positive/valid biomass and wood volume, NMD2018 >=99.9pct water, already preselected; not unbiased random sample",
        "source_cells":len(per),
        "deliveries":{v:dict(sorted(counts[v].items())) for v in EXPECTED},
        "nmd2018_neighbour_classes":{str(k):n for k,n in sorted(neighbour.items())},
        "unanimous_class_across_three_deliveries":dict(sorted(consensus.items())),
        "unanimous_total":agreement,
        "any_delivery_disagreement_cells":len(per)-agreement,
        "pairwise_disagreement_cells":mismatches,
        "historical_water_area_fraction":water_fraction_thresholds,
        "isolated_8_neighbour_nmd2018_water_cells":len(isolated),
        "historical_water_class_in_all_deliveries_among_isolated":stable_isolated_water,
        "water_problem_indicated":stable_isolated_water>0,
        "historical_landcover_observation_year":2000,
        "biomass_2010_physical_units_verified":False,
        "municipal_forest_biomass_trend_calculated":False,
        "limitations":[
          "These 579 cells were selected for anomalous high NMD2018 water coverage; percentages are not representative of municipality-wide forest",
          "A SMD2000 water class and a NMD2018 water class do not prove the exact 2010 landcover",
          "Three SMD2000 ZIPs are delivery variants of one approximate time reference, NOT three independent landcover observations",
          "No true 2010 forest mask or year-to-year physical biomass harmonization is inferred",
          "No cell coordinates or licensed geometries are emitted"]}
    return results
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,help="Optional PRIVATE report path outside checkout")
    a=p.parse_args()
    d=run(a.input)
    # Minimal, strictly non-spatial aggregates only.
    print(json.dumps(d,ensure_ascii=False,indent=2))
    if a.output:
        root=Path(__file__).resolve().parents[1]
        if a.output.resolve().is_relative_to(root):raise ValueError("Private derived output cannot be stored in public repository")
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
