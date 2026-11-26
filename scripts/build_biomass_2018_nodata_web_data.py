#!/usr/bin/env python3
"""Build NMD2018-classed, positive-2010 biomass cohorts with 2018 NoData."""
import argparse,json,math
from pathlib import Path
from compare_nmd2018_landcover_biomass_volume import group

def build(a):
    if a["status"]!="EFFECTIVE_VALID_DATA_MASK_AUDIT_NOT_HISTORICAL_LANDCOVER" or a["analysis_crs"]!="EPSG:3006" or a["pixel_size_m"]!=25:
        raise ValueError("Wrong source audit/CRS/grid")
    rows=[]
    for code,src in a["class_rows"].items():
        cohorts={}
        for label in ("lost2018_2015valid","lost2018_2015missing"):
            n=src.get(label+"_cells",0)
            cohorts[label]={"cells":n,"area_ha":n*.0625,
                "tonnes_TS_2010":src.get(label+"_2010_tonnes_TS",0.0),
                "tonnes_TS_2015":src.get(label+"_2015_tonnes_TS",0.0) if label.endswith("valid") else None}
            assert cohorts[label]["tonnes_TS_2010"]>=0
        rows.append({"nmd_code":int(code),"group":group(int(code)),"cohorts":cohorts})
    labels=("lost2018_2015valid","lost2018_2015missing")
    totals={label:{"cells":sum(r["cohorts"][label]["cells"] for r in rows),
                  "tonnes_TS_2010":sum(r["cohorts"][label]["tonnes_TS_2010"] for r in rows),
                  "tonnes_TS_2015":sum(r["cohorts"][label]["tonnes_TS_2015"] for r in rows) if label.endswith("valid") else None}
            for label in labels}
    for label in labels:
        for suffix in ("cells","2010_tonnes_TS")+(("2015_tonnes_TS",) if label.endswith("valid") else ()):
            k=suffix if suffix=="cells" else suffix
            calc=sum(v.get(label+"_"+suffix,0) for v in a["group_rows"].values())
            if not math.isclose(calc,totals[label]["cells" if suffix=="cells" else "tonnes_TS_"+suffix[:4]],rel_tol=1e-9,abs_tol=.01):
                raise ValueError("Class and group aggregates disagree")
    if totals["lost2018_2015valid"]["cells"]+totals["lost2018_2015missing"]["cells"]<=0:
        raise ValueError("No 2018 NoData 2010-positive cells")
    return {"status":"VERIFIED_POSITIVE_2010_BIOMASS_2018_NODATA","analysis_crs":"EPSG:3006","cell_m":25,
            "source":"scripts/audit_biomass_source_coverage_2010.py","fixed_landcover":"NMD2018",
            "rows":sorted(rows,key=lambda r:r["nmd_code"]),"totals":totals,
            "cautions":["2018 NoData is not zero biomass","2015 NoData is not zero biomass",
                "2010 positive biomass only; valid zero 2010 values intentionally excluded",
                "Year 2015 mass exists only for the 2015-valid subset",
                "Full source raster reprojection to 25 m EPSG:3006 was performed before counts",
                "NMD2018 landcover is not the historical 2010 cover","Products are not model-harmonized"]}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,default=Path("metadata/biomass_source_coverage_2010.json"))
    p.add_argument("--output",type=Path,default=Path("docs/data/biomass_2018_nodata_nmd2018.json"))
    x=p.parse_args()
    result=build(json.loads(x.source.read_text(encoding="utf-8")))
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("2018_NODATA_POSITIVE_2010",result["totals"])
