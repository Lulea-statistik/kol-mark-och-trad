#!/usr/bin/env python3
"""Derive a public, provenance-checked 2015 NoData biomass cohort report.

Based on an actual native-CRS audited comparison, NOT guessed pixel totals.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from compare_nmd2018_landcover_biomass_volume import group

YEARS=("2010","2015","2018")
AREA=.0625
def build(d):
    if d["status"]!="EFFECTIVE_VALID_DATA_MASK_AUDIT_NOT_HISTORICAL_LANDCOVER":
        raise ValueError("Unexpected audit source")
    if d["analysis_crs"]!="EPSG:3006" or d["pixel_size_m"]!=25:
        raise ValueError("Unexpected grid")
    cohort=d["coverage_cohorts"]
    shared=cohort["all_three_years_valid_cells"]
    missing=cohort["biomass_2010_and_2018_valid_biomass2015_nodata_cells"]
    positive=cohort["biomass2010_positive_2015_nodata_2018_valid_cells"]
    if shared!=2456410 or missing!=264484 or not 0<positive<=missing:
        raise ValueError("Unverified historical cohort sizes")
    rows=[]
    for name,values in d["class_rows"].items():
        code=int(name);label=group(code)
        common=values.get("pattern_1111",0)
        absent=values.get("pattern_1011",0)
        positive2010=values.get("pattern_1011_positive_2010_cells",0)
        positive2018=values.get("pattern_1011_positive_2018_cells",0)
        if absent<positive2010 or absent<positive2018:
            raise ValueError("Positive cell count exceeds valid cohort")
        rows.append({
            "nmd_code":code,"group":label,
            "common_cells":common,"missing_2015_cells":absent,
            "positive_biomass_2010_missing_2015_cells":positive2010,
            "positive_biomass_2018_missing_2015_cells":positive2018,
            "missing_2015_tonnes_TS":{"2010":values.get("pattern_1011_2010_tonnes_TS",0.),
                                       "2018":values.get("pattern_1011_2018_tonnes_TS",0.)},
            "common_tonnes_TS":{year:values.get("pattern_1111_"+year+"_tonnes_TS",0.) for year in YEARS},
            "year_valid_cells":{year:values.get("biomass_"+year+"_valid",0) for year in YEARS}
        })
    if sum(r["common_cells"] for r in rows)!=shared or sum(r["missing_2015_cells"] for r in rows)!=missing:
        raise ValueError("Cell count mismatch across NMD classes")
    if sum(r["positive_biomass_2010_missing_2015_cells"] for r in rows)!=positive:
        raise ValueError("Positive 2010 count mismatch")
    grouped=[]
    for label in sorted(set(r["group"] for r in rows)):
        selected=[r for r in rows if r["group"]==label]
        summary={"group":label}
        for attr in ("common_cells","missing_2015_cells",
                     "positive_biomass_2010_missing_2015_cells",
                     "positive_biomass_2018_missing_2015_cells"):
            summary[attr]=sum(r[attr] for r in selected)
        summary["missing_2015_tonnes_TS"]={y:sum(r["missing_2015_tonnes_TS"][y] for r in selected) for y in ("2010","2018")}
        summary["common_tonnes_TS"]={y:sum(r["common_tonnes_TS"][y] for r in selected) for y in YEARS}
        summary["year_valid_cells"]={y:sum(r["year_valid_cells"][y] for r in selected) for y in YEARS}
        source=d["group_rows"][{"Vatten":"Water_NMD2018",
          "Skog utanför våtmark":"Forest_NMD2018","Skog på våtmark":"Forest_NMD2018"}.get(label,"Other_NMD2018")]
        # Original three-way group counts are coarser; checks below use class rows.
        grouped.append(summary)
    for year in YEARS:
        mass=sum(r["common_tonnes_TS"][year] for r in rows)
        expected={"2010":11804189.7704,"2015":9938103.599,"2018":10643793.3499}[year]
        if not math.isclose(mass,expected,abs_tol=2):
            raise ValueError("Common mass changed for "+year)
    return {
       "status":"VERIFIED_COVERAGE_2015_NODATA_AND_POSITIVE_2010_MASS",
       "source_workflow":"https://github.com/Lulea-statistik/kol-mark-och-trad/actions/workflows/compare-biomass-nmd2018-landcover.yml",
       "source_script":"scripts/audit_biomass_source_coverage_2010.py",
       "analysis_crs":"EPSG:3006","cell_m":25,
       "area_ha_per_cell":AREA,
       "cover_reference":"NMD2018 landcover, same class assigned to each 2010/2015/2018 pixel",
       "common_cells":shared,
       "missing_2015_valid_2010_2018_cells":missing,
       "positive_2010_missing_2015_valid_2018_cells":positive,
       "year_valid_cells":cohort["year_valid_cells"],
       "classes":sorted(rows,key=lambda x:x["nmd_code"]),
       "groups":grouped,
       "cautions":[
        "2015 NoData is absence of raster coverage, not zero tonnes or observed logging",
        "2010 positive biomass is modelled and may include water or misclassified nonforest",
        "NMD2018 is not historical landcover 2010",
        "2010 and 2018 mass on 2015-NoData cells is NOT comparable with the 2015 series",
        "Per-year coverage includes 0 biomass if it is a valid cell, not merely forest",
        "WarpedVRT effective 25m validity may differ from original native-grid edge masks",
        "2010/2015/2018 biomass model methods and foliage components are not harmonized",
        "Working polygon is not necessarily official municipal boundary",
        "No 2015 biomass was estimated, imputed or replaced with zero"
       ]}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,default=Path("metadata/biomass_source_coverage_2010.json"))
    p.add_argument("--output",type=Path,default=Path("docs/data/biomass_coverage_nmd2018_2010_2018.json"))
    a=p.parse_args();result=build(json.loads(a.source.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("COVERAGE_FINAL_SUMMARY",json.dumps({
       "common_cells":result["common_cells"],
       "missing_2015_cells":result["missing_2015_valid_2010_2018_cells"],
       "positive_2010_missing_2015":result["positive_2010_missing_2015_valid_2018_cells"],
       "year_valid_cells":result["year_valid_cells"],
       "groups":result["groups"]},ensure_ascii=False))
if __name__=="__main__":main()
