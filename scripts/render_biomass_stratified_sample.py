#!/usr/bin/env python3
"""Export the reproducible sample and its auditable design, no raster mutation."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"metadata/nmd2018_biomass_lulea_audit.json"
OUT=ROOT/"metadata/biomass_stratified_validation_sample_epsg3006.csv"
REPORT=ROOT/"metadata/biomass_stratified_sample_design.md"
FIELDS=("stratum","east_epsg3006","north_epsg3006","nmd_code","raw_biomass",
        "random_key","population_n","sample_n","inclusion_probability",
        "sampling_method","review_status","independent_source","source_date",
        "source_crs_epsg","observed_landcover","independent_verdict","notes")
p=json.loads(SOURCE.read_text(encoding="utf-8"))
sample=p["results"]["stratified_validation_sample"]
pop=sample["populations"]; rows=sample["rows"]
if sum(pop.values())!=p["results"]["valid_joint_pixels"]:
    raise ValueError("Strata must partition the matched valid SGD2/NMD population")
if len(rows)!=sum(min(n,sample["per_stratum_target"]) for n in pop.values()):
    raise ValueError("Incorrect stratified sample size")
OUT.parent.mkdir(parents=True,exist_ok=True)
with OUT.open("w",newline="",encoding="utf-8") as file:
    writer=csv.DictWriter(file,fieldnames=FIELDS,extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({**r,"independent_source":"","source_date":"",
                         "source_crs_epsg":"","observed_landcover":"",
                         "independent_verdict":"","notes":""})
names={
 "water_core_positive":"Vatten 3x3-karna, positiv biomassa",
 "water_edge_positive":"Vattenkant, positiv biomassa",
 "building_positive":"Byggnadsklass, positiv biomassa",
 "road_positive":"Vagklass, positiv biomassa",
 "developed_positive":"Annan exploaterad mark, positiv biomassa",
 "high_other_positive":"Andra klasser, ravarde over 500",
 "ordinary_positive":"Oflaggade positiva celler",
 "zero_control":"Giltiga nollceller - kontroll"
}
lines=[
 "# Stratifierat kontrollurval - SGD2 2018",
 "",
 "Detta ar ett forregistrerat sannolikhetsurval. Ingen cell har verifierats",
 "oberoende och inga rastervarden har andrats.",
 "",
 "Samtliga celler kommer fran samma gemensamma giltiga originalgrid",
 "10 x 10 meter i EPSG:3006. Luleas polygon ar en arbetsgeometri.",
 "",
 "Slumpfro: {}. Maxantal per stratum: {}.".format(sample["seed"],sample["per_stratum_target"]),
 "Klasserna ar omesidigt uteslutande, med prioritetsordningen nedan.",
 "Inom varje stratum har varje cell lika inklusionssannolikhet.",
 "",
 "| Stratum | Population | Stickprov | Inklusionssannolikhet |",
 "|---|---:|---:|---:|"]
for name in sample["strata"]:
    n=pop[name]; k=min(n,sample["per_stratum_target"])
    lines.append("| {} | {:,} | {:,} | {} |".format(names[name],n,k,
                "{:.9f}".format(k/n) if n else "-"))
lines+=["",
 "De oflaggade positiva cellerna och nollcellerna utgor kontrollgrupper.",
 "De ar inte oberoende sanningsdata forran marktacket granskats.",
 "",
 "## Granskning",
 "Kontrollera koordinater i EPSG:3006 mot ortofoto med dokumenterat",
 "fotodatum samt vatten- och byggnadsgeometrier fran oberoende kallar.",
 "Verifiera kallsystem och valj status efter faktisk granskning.",
 "Automatisk klassning ar inte bevis for fel.",
 "",
 "## Analys efter manuell granskning",
 "Vikta inom varje stratum med populationsantalet, redovisa osakerhet",
 "och andel falskt positiva. PR #32 riskprioriterade urval ar inte",
 "representativt och far inte anvandas for populationsskattningar.",
 "",
 "Ingen maskning och ingen andring av originalraster.",
]
REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(f"Exported {len(rows)} sampled cells from {sum(pop.values())} eligible pixels")
