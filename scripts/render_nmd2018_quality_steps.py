#!/usr/bin/env python3
"""Render incremental, mutually comparable quality scenarios from original QA JSON."""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"metadata/nmd2018_biomass_lulea_audit.json"
REPORT=ROOT/"metadata/nmd2018_quality_steps.md"
CHART=ROOT/"metadata/nmd2018_quality_steps.png"
LABELS={
    "baseline": "0. Original, ingen exkludering",
    "water_core": "1. Exkludera NMD vattenkärnor",
    "extreme_gt1000": "Alternativ: enbart råvärden >1000",
    "water_then_extreme_gt1000": "2. Vattenkärnor + råvärden >1000",
    "extreme_gt500": "Alternativ: enbart råvärden >500",
    "water_then_extreme_gt500": "Känslighet: vatten + råvärden >500",
}
ORDER=list(LABELS)
def fmt(x,dec=0):
    return f"{x:,.{dec}f}".replace(","," ").replace(".",",")
def main():
    payload=json.loads(DATA.read_text(encoding="utf-8"))
    p=payload["results"]
    scenarios=p["quality_scenarios"]["scenarios"]
    b=scenarios["baseline"]
    if b["retained_pixels"]!=p["valid_joint_pixels"]:
        raise ValueError("Baseline must exactly equal all SGD2/NMD joint valid cells")
    # Cross-check against independently computed existing class QA.
    core=sum(p["categories"][name]["core_positive_pixels"] for name in ("water_inland","water_sea"))
    if core!=b["remaining_water_core_positive"]:
        raise ValueError("Water core positive count must match the pre-existing per-class QA")
    assert scenarios["water_then_extreme_gt1000"]["retained_pixels"]<=scenarios["water_core"]["retained_pixels"]
    assert scenarios["water_then_extreme_gt1000"]["retained_pixels"]<=scenarios["extreme_gt1000"]["retained_pixels"]
    # No double subtraction: both filters remove their UNION; sums must agree
    # in whichever order applied, by construction of the shared mask.
    area=p["native_cell_area_ha"]
    rows=[]
    for key in ORDER:
        s=scenarios[key]
        missing=b["retained_pixels"]-s["retained_pixels"]
        removed=b["retained_raw_sum"]-s["retained_raw_sum"]
        rows.append(f"| {LABELS[key]} | {fmt(s['retained_pixels'])} | "
                    f"{fmt(missing)} ({fmt(missing*area,2)} ha) | "
                    f"{fmt(s['retained_raw_sum'])} | {fmt(removed)} | "
                    f"{fmt(100*removed/b['retained_raw_sum'],4) if b['retained_raw_sum'] else '—'} % | "
                    f"{fmt(s['remaining_water_core_positive'])} | "
                    f"{fmt(s['remaining_extreme_gt1000'])} |")
    water=scenarios["water_core"]
    extreme=scenarios["extreme_gt1000"]
    both=scenarios["water_then_extreme_gt1000"]
    extra_removed_cells=water["retained_pixels"]-both["retained_pixels"]
    extra_removed_raw=water["retained_raw_sum"]-both["retained_raw_sum"]
    overlap_cells=(b["retained_pixels"]-water["retained_pixels"])+(b["retained_pixels"]-extreme["retained_pixels"])-(b["retained_pixels"]-both["retained_pixels"])
    delta_core=b["remaining_water_core_positive"]-water["remaining_water_core_positive"]
    doc=f"""# Stegvis kvalitetssäkring av SGD2 2018 i Luleå – simulerade alternativ

Underlag: NMD2018 v1.1 och original-SGD2, EPSG:3006, 10×10 m, identisk **gemensam giltig pixelpopulation** i alla alternativ (utgångsläge: {fmt(b['retained_pixels'])} celler). Arbetsgeometri, ej verifierad officiell kommungräns. Körning: {payload['checked_at_utc']}.

**Detta är inte en serie uppmätta förbättringar.** Masker simuleras i analysen. Lägre råvärdessumma är i sig inte bevis för bättre datakvalitet. Trösklarna 500 och 1 000 är *godtyckliga känslighetsval i råvärdesenheter*, inte beslutade ekologiska gränser. Ingen ändring har gjorts i originalfilen.

## Jämförelse steg för steg

| Alternativ | Behållna celler | Exkluderade celler (area) | Behållen råvärdessumma | Borttagen råvärdessumma | Förändring av råvärdessumma | Kvar: positiv vattenkärna | Kvar: värden >1000 |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

### Vad tillför varje iteration?

1. **Nolläge:** Alla giltiga SGD2-celler där också NMD2018 har giltig klass, inklusive nollor.
2. **Vattenkontroll:** Endast sammanhängande inlandsvatten/hav (alla åtta grannar samma klass 61 eller 62) exkluderas *hypotetiskt*. Antal kvarvarande positiva vattenkärnceller minskar med **{fmt(delta_core)}** – detta är mekaniskt utfall av urvalet, inte oberoende verifierad träffsäkerhet.
3. **Extremvärdeskänslighet:** Jämför exkludering av värden >1000 **utan** vattenfilter, för att tydliggöra dess fristående effekt.
4. **Kombination i ordning vatten → extremvärde:** Ytterligare **{fmt(extra_removed_cells)} celler** och **{fmt(extra_removed_raw)} råvärdesenheter** exkluderas efter vattensteget. Överlappet mellan kriterierna uppgår till **{fmt(overlap_cells)} celler**; dessa får inte dubbelräknas.
5. **Alternativ gräns >500:** Motsvarande separata och kombinerade känslighetsscenario redovisas för att visa hur starkt resultaten påverkas av ett ogrundat tröskelval.

### Kvalitet eller bara lägre värde?

**Rekommendation:** Ge inga scenarier etiketten 'bättre' innan konfliktceller stickprovskontrollerats mot oberoende ortofoto, högupplöst vatten-/byggnadsgeometri och produktmetadata. Positiv biomassa vid vägkant, gård, park eller brygga kan vara verklig; hög biomassa kan vara ett modellfel men också signalera skal-/produktproblem. Enheten och skalningen i originalraster återstår att slutverifiera.

Beräknade **råvärdessummor är inte ton TS** och arealerna avser nominella hela cellareor, inte fragment över kommungränsen. Källkod ändrar inga raster och maskar inte bort värden från publicerad karta.

Källrapport: `nmd2018_biomass_lulea_audit.json` · diagram: `nmd2018_quality_steps.png`.
"""
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(doc,encoding="utf-8")
    # A separate chart shows sensitivity of raw sum, not absolute "improvement".
    series=["baseline","water_core","extreme_gt1000","water_then_extreme_gt1000","water_then_extreme_gt500"]
    names=["Original","Vattenkärnor",">1000 enbart","Vatten + >1000","Vatten + >500"]
    vals=[100*(b["retained_raw_sum"]-scenarios[k]["retained_raw_sum"])/b["retained_raw_sum"] for k in series]
    fig,ax=plt.subplots(figsize=(9,4.5))
    bars=ax.barh(names,vals)
    ax.invert_yaxis();ax.set_xlabel("Minskning av summerade rasterråvärden jämfört med nolläge (%)")
    ax.set_title("Stegvisa känslighetsscenarier – INTE verifierade kvalitetsvinster")
    ax.set_xlim(0,max(vals)*1.2 if max(vals)>0 else 1)
    for bar,v in zip(bars,vals):
        ax.text(bar.get_width()+0.02,bar.get_y()+bar.get_height()/2,fmt(v,4)+" %",va="center",fontsize=9)
    fig.text(.02,.01,"Samma SGD2/NMD-giltiga pixelpopulation. Trösklar 500/1000 är hypotetiska. Originaldata oförändrade.",fontsize=8)
    fig.tight_layout(rect=(0,.05,1,1));fig.savefig(CHART,dpi=170);plt.close(fig)
    print("Wrote",REPORT,CHART,flush=True)
if __name__=="__main__":main()
