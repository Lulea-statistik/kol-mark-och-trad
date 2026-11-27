#!/usr/bin/env python3
"""Explicit illustrative Lulea site-productivity backward scenarios.

NOT an actual age- and site-index-calibrated growth model. Uses real verified
same-cell biomass aggregates (2010, 2015, 2018) and externally framed but
assumed stand productivity, species/site factors, plus assumed dry-mass
conversion. Neither the 2010 biomass raster nor year 2010 is recalibrated.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path

# Illustrative, NOT empirically calibrated for Lulea stands.
SCENARIOS={
 "low":{"pine_bonitet_m3sk_ha_year":2.2,"spruce_bonitet_m3sk_ha_year":2.4,
        "realized_fraction_of_bonitet":.5,"tTS_per_m3sk":.50},
 "central":{"pine_bonitet_m3sk_ha_year":3.2,"spruce_bonitet_m3sk_ha_year":3.5,
        "realized_fraction_of_bonitet":.75,"tTS_per_m3sk":.65},
 "high":{"pine_bonitet_m3sk_ha_year":4.6,"spruce_bonitet_m3sk_ha_year":5.0,
        "realized_fraction_of_bonitet":1.0,"tTS_per_m3sk":.80}
}
# The fraction is an explicit scenario for actual net standing-biomass gain,
# NOT bonitet as annual realized growth; disturbances can invalidate it.

def build(src):
    assert src['analysis_crs']=='EPSG:3006' and src['cell_m']==25
    rows={}
    for key,c in src['cohorts'].items():
        n=c['col_2010_cells']; ha=c['area_ha']
        assert sum(n)==c['cells']
        actual={year:sum(c['2010_balance_class_mass_tTS'][year]) for year in ('2010','2015','2018')}
        assert ha>0 and all(v>=0 for v in actual.values())
        scenarios={}
        for name,p in SCENARIOS.items():
            inc=0
            for i,number in enumerate(n):
                frac_spruce=(i+1)/10
                bonitet=frac_spruce*p['spruce_bonitet_m3sk_ha_year']+(1-frac_spruce)*p['pine_bonitet_m3sk_ha_year']
                inc+=number*.0625*bonitet*p['realized_fraction_of_bonitet']*p['tTS_per_m3sk']
            # All biomass estimates on exact same valid cells; annual positive
            # increment assumption and ZERO unregistered disturbance.
            scenarios[name]={
              "assumed_annual_net_gain_tTS":inc,
              "2010_backcast_from_2015_tTS":actual['2015']-5*inc,
              "2010_backcast_from_2018_tTS":actual['2018']-8*inc,
              "2010_model_minus_2015_backcast_tTS":actual['2010']-(actual['2015']-5*inc),
              "2010_model_minus_2018_backcast_tTS":actual['2010']-(actual['2018']-8*inc),
              "2015_to_2018_observed_model_mean_increment_tTS_year":
                  (actual['2018']-actual['2015'])/3
            }
        rows[key]={
            "cell_count":c['cells'],"area_ha":ha,
            "modeled_mass_tTS":actual,
            "modeled_mean_density_tTS_ha":{y:actual[y]/ha for y in actual},
            "scenario_backcast":scenarios,
            "cohort_note":"Age>= thresholds overlap: only age_ge20 represents full comparison population."
        }
    return {
      "status":"ILLUSTRATIVE_NOT_FIELD_CALIBRATED",
      "crs":"EPSG:3006",
      "cell_m":25,
      "same_cell_forest_mask":src["forest_mask"],
      "site_productivity_reference":"Norrbotten mean approx 3.0 m3sk/ha/year (Skogsdata 2024 table 3.11a); Lulea/species ranges assumed, not municipality-estimated.",
      "species_weight_definition":"2010 SPRUCEVOL/(SPRUCEVOL+PINEVOL) balance-class midpoint 0.1..0.9, not an observed trädslag distribution.",
      "biomass_conversion_caveat":"tTS per m3sk is assumed scenario conversion; source-specific biomass definitions must be validated before applying.",
      "assumptions":"Fixed stand species/site productivity, no mortality/harvest/thinning/recruitment and constant net gain each year. BONITET IS POTENTIAL LONG-RUN YIELD, NOT REALIZED GROWTH. Do not use for corrections.",
      "scenario_parameters":SCENARIOS,
      "cohorts":rows
    }

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--input',type=Path,default=Path('docs/data/gran_tall_balans_2005_2010.json'))
 p.add_argument('--output',type=Path,default=Path('docs/data/bonitet_bakatrakning_scenarier.json'))
 args=p.parse_args()
 d=build(json.loads(args.input.read_text(encoding='utf-8')))
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
 main=d['cohorts']['age_ge20']
 print("BONITET_BACKCAST_SCENARIO",main['area_ha'],main['modeled_mass_tTS'])
 for name,x in main['scenario_backcast'].items():
  print(name,x['2010_backcast_from_2015_tTS'],x['2010_backcast_from_2018_tTS'])
if __name__=='__main__':main()
