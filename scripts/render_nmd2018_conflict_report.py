#!/usr/bin/env python3
"""Build an aggregated diagnostic map and Markdown report from NMD/SGD2 QA JSON.

Map shows totals per original 512x512-pixel processing tile (approx 5.12 km),
not precise conflict locations. Original imagery, biomass and NMD untouched.
"""
from pathlib import Path
import json
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import shape
from shapely.ops import transform as shp_transform
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"metadata/nmd2018_biomass_lulea_audit.json"
OUTPUT=ROOT/"metadata/nmd2018_conflict_overview.png"
REPORT=ROOT/"metadata/nmd2018_conflict_report.md"
COLORS={"water_inland":"#147cbd","water_sea":"#193f8f","buildings":"#ad3350","roads":"#e38a19","other_developed_review":"#8f55a6"}
NAMES={"water_inland":"Inlandsvatten","water_sea":"Hav","buildings":"Byggnader","roads":"Vägar","other_developed_review":"Annan anlagd mark"}
def outlines(ax,geom):
    if geom.geom_type=="Polygon": regions=[geom]
    elif geom.geom_type=="MultiPolygon": regions=geom.geoms
    else: raise ValueError("Unexpected municipality polygon geometry")
    for g in regions:
        x,y=g.exterior.xy
        ax.plot(x,y,color="#555555",linewidth=0.6,zorder=2)

def main():
    payload=json.loads(INPUT.read_text(encoding="utf-8"))
    p=payload["results"]
    tiles=p.get("spatial_tiles")
    if not tiles:raise ValueError("Missing aggregate spatial tile output. Rerun NMD QA.")
    if p["metadata"]["crs_sgd2"]!="EPSG:3006":
        raise ValueError("Expected EPSG:3006 native SGD2 grid")
    boundary=json.loads((ROOT/"docs/data/lulea_boundary.geojson").read_text(encoding="utf-8"))
    poly=shape(boundary["features"][0]["geometry"])
    projected=shp_transform(Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,poly)
    fig,axes=plt.subplots(2,3,figsize=(13,11),constrained_layout=True)
    fig.suptitle("SGD2 2018 – möjliga biomassakonflikter mot NMD2018 i Luleå",fontsize=14,fontweight="bold")
    classes=list(COLORS)
    for ax,name in zip(axes.flat,classes):
        outlines(ax,projected)
        t=[item for item in tiles if item["positive_by_class"].get(name,0)>0]
        if t:
            values=np.asarray([i["positive_by_class"][name] for i in t],dtype=float)
            sizes=10+125*np.sqrt(values/max(float(values.max()),1))
            ax.scatter([i["x"] for i in t],[i["y"] for i in t],s=sizes,
                       color=COLORS[name],alpha=0.65,edgecolors="none",zorder=3)
        stat=p["categories"][name]
        ax.set_title(f"{NAMES[name]}: {stat['positive_pixels']:,} positiva celler".replace(",", " "))
        ax.set_aspect("equal",adjustable="box");ax.tick_params(labelsize=7)
        ax.set_xlabel("Östlig koordinat, EPSG:3006",fontsize=8)
        ax.set_ylabel("Nordlig koordinat, EPSG:3006",fontsize=8)
    ax=axes.flat[-1];ax.axis("off")
    water=sum(p["categories"][k]["core_positive_pixels"] for k in ["water_inland","water_sea"])
    text=("Kartans prickar visar summerade avvikelser per cirka 5 km-ruta,\n"
          "inte individuella 10 m-pixlars läge. Storlek ≈ relativt antal\n"
          "positiva celler inom rutan. Kartan är endast en diagnos.\n\n"
          f"Positiva vatten-celler i 3×3-kärnor: {water:,}\n"
          "Originalraster har inte modifierats.\n"
          "Arbetsgeometri – inte officiell kommungräns.")
    ax.text(0,0.95,text.replace(",", " "),ha="left",va="top",fontsize=10,linespacing=1.7)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(OUTPUT,dpi=160)
    plt.close(fig)
    area=p["native_cell_area_ha"]
    rows=[]
    for name,stat in p["categories"].items():
        pos=stat["positive_pixels"];total=stat["eligible_pixels"];core=stat["core_positive_pixels"]
        rows.append(f"| {NAMES[name]} | {total:,} | {pos:,} | {pos/total*100 if total else 0:.2f} % | {core:,} | {stat['edge_positive_pixels']:,} | {pos*area:.2f} |".replace(",", " "))
    waterkeys=("water_inland","water_sea")
    core=sum(p["categories"][k]["core_positive_pixels"] for k in waterkeys)
    raw=sum(p["categories"][k]["core_raw_positive_sum"] for k in waterkeys)
    content=f"""# NMD2018 kontra SGD2: avvikelsediagnos för Luleå

Körning: {payload['checked_at_utc']}. Avser **SGD2-originalraster, 10 m, EPSG:3006**, korsklassat med NMD2018 v1.1 i motsvarande grid. Luleåavgränsning är en arbetsgeometri.

| Marktäckeklass | Matchade celler | Positiv biomassa | Andel | 3×3-kärna | Klassgräns | Positiv cellarea (ha) |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## Konservativt scenario, enbart analys

En möjlig första maskningskandidat är **positiva SGD2-celler inom sammanhängande NMD-vattenklass (61 eller 62) med samtliga åtta grannceller i samma vattenklass**.

- Kandidater: **{core:,} celler** (= {core*area:.2f} ha, baserat på rastercellernas nominella area).
- Sammanlagda **råvärden** i dessa celler: {raw:.0f} (ingen verifierad fysisk massenhet).
- **Ingen mask har lagts på och inget originalraster har ändrats.**
- Ingen biomassatotal i ton TS/ha/ton TS har beräknats; detta är ett hypotetiskt kvalitetsurval.
- Även vattenkärnor måste granskas mot ortofoto, strandlinjegeometri, NMD-klassningsnoggrannhet och källrastretes lägesprecision före eventuell korrigering.

## Tolkningsrisker

- Klass 51/53 kan innehålla träd, kantzoner och blandpixlar; maska inte per automatik.
- NMD och SGD2 delar 10 m rasterupplösning men kan ha olika cellgränser; nearest resampling och 3×3-kärnkontroll minskar men eliminerar inte osäkerheten.
- Förhandskartan är **aggregerad per 512×512 originalceller (~5 km)** och visar inte exakt konfliktcell.
- Projektets polygon är inte officiell kommungräns.
- Särredovisa alla ändringar som ett eget kvalitetssäkrat alternativ efter en separat beslutad validering.

Källresultat: `nmd2018_biomass_lulea_audit.json`. Kartbild: `nmd2018_conflict_overview.png`.
"""
    REPORT.write_text(content.replace(",", " " if False else ","),encoding="utf-8")
    print("Created",OUTPUT,REPORT,flush=True)

if __name__=="__main__":main()
