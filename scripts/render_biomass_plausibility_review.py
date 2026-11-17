#!/usr/bin/env python3
"""Evidence review outputs: class flags, audit queue, no deletion."""
import csv
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=json.loads((ROOT/"metadata/nmd2018_biomass_lulea_audit.json").read_text(encoding="utf-8"))
review=p["results"]["plausibility_review"]
out=ROOT/"metadata/biomass_plausibility_review.md"
csvpath=ROOT/"metadata/biomass_review_candidates_epsg3006.csv"
names={
 "water_core_positive":"Positiv biomassa i sammanhängande vatten",
 "water_edge_positive":"Positiv biomassa vid vattengräns",
 "building_core_positive":"Positiv biomassa i byggnadsklassens kärna",
 "road_core_positive":"Positiv biomassa i vägklassens kärna",
 "developed_core_positive":"Positiv biomassa i övrig exploaterad mark",
 "high_gt500":"Råvärde över 500, alla klasser",
 "high_gt1000":"Råvärde över 1000, alla klasser",
 "high_nonforest_gt500":"Råvärde över 500 i vatten/byggnad/väg"
}
rows=[]
for key,title in names.items():
 m=review["metrics"][key]
 rows.append("| {} | {:,} | {:.2f} | {:,.0f} |".format(title,m["n"],m["n"]*p["results"]["native_cell_area_ha"],m["raw_sum"]))
points=[item for sub in review["review_points"].values() for item in sub]
out.parent.mkdir(parents=True,exist_ok=True)
with csvpath.open("w",newline="",encoding="utf-8") as f:
 writer=csv.DictWriter(f,fieldnames=["rule","east","north","nmd_code","raw_value","status"])
 writer.writeheader();writer.writerows(points)
body="""# SGD2 2018 – rimlighetsbedömning mot marktäcke

Automatiskt identifierade granskningskandidater, inte bekräftade fel.
Ingen rasterändring har gjorts. EPSG:3006, original 10 m, NMD2018
klassificerad till original-SGD2-grid. Kommunavgränsning är arbetsgeometri.

| Granskningsregel | Antal celler | Nominell cellarea (ha) | Summa råvärden |
|---|---:|---:|---:|
"""+"\n".join(rows)+"""

Samma cell kan förekomma i flera grupper. Värden >500 och >1000 är
urvalströsklar, INTE verifierade gränser för biologiskt orimlig biomassa.

## Ordning för oberoende validering

1. Vattenkärnor: jämför positiv biomassa med oberoende ortofoto och vattenlinje;
   beakta vattennivå, bryggor, strandpixlar och georefereringsfel.
2. Byggnader och vägar: avgör om cellen faktiskt motsvarar hus/vägbana eller
   innehåller vegetation på gård, allé eller i vägren.
3. Extremvärden: kontrollera källa, numerisk skala, skogstyp, laser och
   närliggande trädhöjder. Värden över tröskel är inte automatiskt fel.
4. Klassificera granskade fall som confirmed_error, plausible_biomass eller
   uncertain, och spara oberoende källbelägg, datum och motivering.

## Kvalitetskriterium

Mät andelen oberoende bekräftade fel bland föreslagna felceller och andelen
verklig biomassa som skulle försvinna felaktigt. För ett opartiskt
precisionsestimat krävs stratifierat slumpmässigt stickprov. CSV-filen
innehåller prioriterade toppvärdesexempel och är därför inte representativ.

Originalraster och publicerade kartvärden oförändrade. Vid bekräftade fel
måste det beslutas om NoData (ej tillämplig/okänd) eller 0 (verifierad nolla)
ska användas i en separat korrigerad produkt.
"""
out.write_text(body,encoding="utf-8")
print("Wrote",out,csvpath)
