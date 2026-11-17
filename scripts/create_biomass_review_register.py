#!/usr/bin/env python3
"""Create a reproducible, evidence-first inspection register from SGD2 QA.

This produces an EMPTY adjudication form, not asserted confirmations. Repeated
coordinates can enter through multiple risk rules: use a single cell ID to
avoid double-counting during manual adjudication. CRS is verified EPSG:3006.
"""
import argparse
import csv
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"metadata/biomass_review_candidates_epsg3006.csv"
OUTPUT=ROOT/"metadata/biomass_independent_review_register.csv"
FIELDS=("cell_id","east_epsg3006","north_epsg3006","nmd_code",
        "raw_biomass","flag_rules","sampling_method","review_status",
        "independent_source","source_date","source_crs_epsg",
        "location_uncertainty_m","land_cover_observed",
        "biomass_plausibility","reviewer","review_date","reasoning",
        "proposed_action")

def make_id(east,north):
    return "SGD2_2018_"+hashlib.sha256(f"{east:.2f},{north:.2f}".encode()).hexdigest()[:14]

def create_register(source=SOURCE,output=OUTPUT):
    rows={}
    with Path(source).open(newline="",encoding="utf-8") as handle:
        for r in csv.DictReader(handle):
            east,north=float(r["east"]),float(r["north"])
            key=make_id(east,north)
            if key not in rows:
                rows[key]={"cell_id":key,"east_epsg3006":f"{east:.2f}",
                    "north_epsg3006":f"{north:.2f}",
                    "nmd_code":r["nmd_code"],"raw_biomass":r["raw_value"],
                    "flag_rules":set(),"sampling_method":"risk_ranked_not_random",
                    "review_status":"not_reviewed","independent_source":"",
                    "source_date":"","source_crs_epsg":"",
                    "location_uncertainty_m":"","land_cover_observed":"",
                    "biomass_plausibility":"","reviewer":"","review_date":"",
                    "reasoning":"","proposed_action":"no_change"}
            else:
                if rows[key]["nmd_code"]!=r["nmd_code"] or float(rows[key]["raw_biomass"])!=float(r["raw_value"]):
                    raise ValueError("Conflicting original values for same EPSG:3006 cell center")
            rows[key]["flag_rules"].add(r["rule"])
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    with Path(output).open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=FIELDS);writer.writeheader()
        for row in sorted(rows.values(),key=lambda r:r["cell_id"]):
            row["flag_rules"]=";".join(sorted(row["flag_rules"]))
            writer.writerow(row)
    print(f"Review register created with {len(rows)} unique cells: {output}")

def validate_register(path):
    """Read manually adjudicated entries; count decisions without false QA claims."""
    allowed={"not_reviewed","confirmed_error","plausible_biomass","uncertain"}
    actions={"no_change","zero_in_derived_product","nodata_in_derived_product"}
    counts={k:0 for k in allowed}
    with Path(path).open(newline="",encoding="utf-8") as handle:
        for r in csv.DictReader(handle):
            status=r["review_status"]
            if status not in allowed:raise ValueError(f"Unrecognized status: {status}")
            if r["proposed_action"] not in actions:
                raise ValueError(f"Unrecognized action: {r['proposed_action']}")
            if status!="confirmed_error" and r["proposed_action"]!="no_change":
                raise ValueError("No exclusion without independent confirmed_error")
            if status=="confirmed_error":
                if not (r["independent_source"] and r["source_date"] and r["source_crs_epsg"]
                        and r["reviewer"] and r["reasoning"] and r["review_date"]):
                    raise ValueError("Confirmed error lacks independent evidence and provenance")
            counts[status]+=1
    print("Reviewed outcomes:",counts)
    print("Not a representative sample: do NOT report these ratios as population error rates.")
    return counts

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--validate",help="Validate a manually completed review register, no raster writes")
    args=parser.parse_args()
    if args.validate:validate_register(args.validate)
    else:create_register()
