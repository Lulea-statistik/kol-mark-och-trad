#!/usr/bin/env python3
"""Age-stratified consistency checks for a possible alternative 2010 biomass model.

Uses published verified age x 2010 TOTALVOL x species raster aggregates.
Never interprets differences between model generations as measured growth.
"""
from __future__ import annotations
import json,argparse,math
from pathlib import Path

def make(source):
    if source["analysis_crs"]!="EPSG:3006" or source["cell_m"]!=25:
        raise ValueError("Unexpected raster CRS/grid")
    fine=source["fine_volume_control"]
    counts=fine["counts"]
    masses=fine["mass_tTS"]
    out=[]
    total={y:0. for y in ("2010","2015","2018")}
    total_cells=0
    for i,age in enumerate(fine["age_bins"]):
        n=sum(sum(row) for row in counts[i])
        if n==0:continue
        ha=n*.0625
        model={year:sum(sum(row) for row in masses[year][i])
               for year in ("2010","2015","2018")}
        for y in model:total[y]+=model[y]
        total_cells+=n
        # These are increments *required by the models* if every difference
        # were true forest stock change. That premise is NOT accepted as fact.
        rate_2010_15=(model["2015"]-model["2010"])/(5*ha)
        rate_2010_18=(model["2018"]-model["2010"])/(8*ha)
        rate_2015_18=(model["2018"]-model["2015"])/(3*ha)
        implied_backcast_2010_from_2015_using_2015_18_rate=(
            model["2015"]-5*rate_2015_18*ha)
        implied_backcast_2010_from_2018_using_2015_18_rate=(
            model["2018"]-8*rate_2015_18*ha)
        if not math.isclose(implied_backcast_2010_from_2015_using_2015_18_rate,
                            implied_backcast_2010_from_2018_using_2015_18_rate,abs_tol=.01):
            raise ValueError("Anchor projection closure failed")
        out.append({
            "age_2010_bin":age,"cells":n,"ha":ha,
            "modeled_mass_tTS":model,
            "required_annual_change_tTS_ha_if_models_were_true":{
                "2010_to_2015":rate_2010_15,"2010_to_2018":rate_2010_18,
                "2015_to_2018":rate_2015_18},
            "linear_2015_2018_extrapolated_2010_tTS":
                implied_backcast_2010_from_2015_using_2015_18_rate,
            "model2010_minus_extrapolated_tTS":
                model["2010"]-implied_backcast_2010_from_2015_using_2015_18_rate
        })
    ref=source["cohorts"]["age_ge20"]
    if total_cells!=ref["cells"] or not math.isclose(total_cells*.0625,ref["area_ha"],abs_tol=.001):
        raise ValueError("Age strata do not cover same verified population")
    for y in total:
        if not math.isclose(total[y],sum(ref["2010_balance_class_mass_tTS"][y]),
                            rel_tol=1e-9,abs_tol=.01):
            raise ValueError("Age strata biomass does not reconcile")
    return {
        "status":"MODEL_TO_MODEL_AGE_DIAGNOSTIC_NOT_OBSERVED_GROWTH",
        "analysis_crs":"EPSG:3006","grid_cell_m":25,
        "same_cell_population":total_cells,
        "source":"docs/data/gran_tall_balans_2005_2010.json",
        "biomass_definition_caveat":"Only sums of existing modelled dry biomass; unit/biomass component equivalence still needs independent source validation.",
        "critical_method_warning":"2015-2018 linear extrapolation is NOT bonitet-adjusted growth or independently measured biomass. Do not substitute values in maps.",
        "age_group_results":out,
        "total_modelled_tTS":total,
        "eligibility_rules":{
          "current_status":"NO_SUBSTITUTE_APPROVAL",
          "requirements":[
            "Confirm all years compare identical live biomass components and physical units",
            "Obtain spatial site index with verified source CRS, reference date and tree species; validate index for Lulea",
            "Use documented age- and tree-species-dependent net growth model, handling mortality, harvest and thinning",
            "Build cellwise 2010 reconstructed raster based independently on later anchors, with valid 2010 forest mask and NoData handling",
            "Cross-check 2015 and 2018 reconstructions without tuning to match 2010",
            "Validate on independent field/plot data and regional estimates, with uncertainty and spatial holdouts",
            "Record overlap, exclusions and age/species/bonitet error statistics; version method and retain original rasters"
          ],
          "publication_policy":"Separate clearly-labelled alternative scenario layers only. Original 2010 remains default pending independent calibration."}
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("docs/data/gran_tall_balans_2005_2010.json"))
    p.add_argument("--output",type=Path,default=Path("docs/data/bonitet_alder_valideringsdiagnostik.json"))
    a=p.parse_args()
    d=make(json.loads(a.input.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for row in d["age_group_results"]:
        print(row["age_2010_bin"],row["required_annual_change_tTS_ha_if_models_were_true"])
if __name__=="__main__":
    main()
