# Bonitet som bakåtriktad rimlighetskontroll av biomassan 2010

**Status:** Tre illustrativa tillväxtscenarier, inte korrigerade biomassavärden. Modellen jämför på samma verifierade NMD2018-skogsceller utan registrerad avverkning 2011–2018, och kräver ytterligare växtplats- och tillväxtdata innan en biologiskt kalibrerad rekonstruktion kan göras.

## 1. Varför denna kontroll är relevant

Vi har tidigare jämfört biomassa från olika modeller vilket riskerar metodfel. En alternativ kontroll är att beräkna vad 2010 års *levande stående biomassa* kan ha varit utifrån 2015 och 2018, givet realistisk förändring under fem respektive åtta år. Denna metod kan ifrågasätta oförenliga modellnivåer men inte peka ut korrekt modell utan oberoende data.

På det gemensamma urvalet av **101 074,8125 ha (1 617 197 giltiga 25 m-celler, modellerad ålder 2010 minst 20 år)** ger de tre modellrastren:
- 2010: **9 162 434,96 ton TS** (90,65 ton/ha).
- 2015: **8 393 612,06 ton TS** (83,04 ton/ha).
- 2018: **9 124 493,30 ton TS** (90,27 ton/ha).

**Viktigt:** Detta är inte Luleås hela skogsareal. Masken kräver alla tre års biomassa, NMD2018-skog, gran/tall-beräkningsbara celler och ingen *registrerad* 2011–2018-avverkning. 2015 års norra saknade täckning ingår inte. 2010 och 2018 är således i stort sett lika i **totalen på just detta urval**, samtidigt som skillnaderna för äldre och mer grandominerade bestånd är betydande.

## 2. Extern bonitetsreferens

**Verifierat publicerad regional utgångspunkt:** Riksskogstaxeringens *Skogsdata 2024*, tabell 3.11a, anger **3,0 m³sk/ha och år** som medelbonitet på produktiv skogsmark utanför formellt skyddade områden i Norrbotten 2019–2023. Området inkluderar geografiskt mycket mer än Luleå och avser inte det blandade NMD2018-urvalet.

**Bonitet (m³sk/ha/år) är den långsiktiga produktionspotentialen för en växtplats**, inte den observerade årliga nettotillväxten i ett bestånd med given ålder, täthet, skötsel, trädslag och skador. Stamvolym m³sk och torrmassa ton TS är inte samma enhet. Utan oberoende biomassexpansionsfaktorer och tillväxtkurvor går inte bonitet direkt att subtrahera från ett biomassa- eller kolförråd.

Källor:
- SLU Riksskogstaxeringen, *Skogsdata 2024*, tabell 3.11a: https://www.slu.se/globalassets/slu.se/om-slu/organisation/institutioner/skoglig-resurshushallning/riksskogstaxeringen/dokument/skogsdata/skogsdata_2024_web.pdf
- Skogskunskap, *Om Bonitet – Skogshögskolans system*: https://www.skogskunskap.se/rakna-med-verktyg/mata-skogen/bonitet/om-bonitet---skogshogskolans-system/
- Skogsstyrelsen, *Skogsskötselns grunder och samband*: https://skogsstyrelsen.se/globalassets/mer-om-skog/skogsskotselserien/skogsskotsel-serien-1-skogsskotselns-grunder-och-samband.pdf
- Skogsstyrelsen, *Skogliga grunddata*, information om senare ståndortsindexraster: https://skogstyrelsen.se/e-tjanster-och-kartor/karttjanster/skogsstyrelsens-geodata/

## 3. Illustrativa, ej validerade antaganden

| Scenario | Tallbonitet m³sk/ha/år | Granbonitet m³sk/ha/år | Realiserad nettovolymtillväxt som andel av bonitet | Omräkning ton TS per m³sk |
|---|---:|---:|---:|---:|
| Låg | 2,2 | 2,4 | 0,50 | 0,50 |
| Bas | 3,2 | 3,5 | 0,75 | 0,65 |
| Hög | 4,6 | 5,0 | 1,00 | 0,80 |

**Hela tabellen är en explicit antagandemodell, inte lokalt skattade värden.** Nivåerna är valda för att spänna kring Norrbottens offentliga medelbonitet 3,0. Gran/tall-vikten är 2010 års modellerade balansklass, approximativt 10/90 … 90/10. För varje klass beräknas årlig förändring som:

`antal_celler × 0,0625 ha × (andel_gran × granbonitet + andel_tall × tallbonitet) × tillväxtfraktion × tonTS_per_m³sk`.

Årlig nettotillväxt antas konstant och positiv, utan avverkning/gallring/skador/avgång. Bakåträknad 2010-biomassa från år Y = modellbiomassa Y − (Y−2010) × årlig antagen nettotillväxt. 2015 och 2018 ger **två separata rekonstruktioner** och jämförs mot 2010 som extern kontroll av konsekvens, inte som kalibreringsfacit.

Modellen har **inte** åldersberoende produktionskurvor, cellvis bonitet, spatiala produktionszoner eller verifierade biomassakomponenters konvertering. Framför allt innebär detta att en rekonstruktion med konstant årlig biomassatillväxt över mycket unga och gamla skogar inte är en rigorös biologisk rekonstruktion. Den är en transparent första känslighetskontroll.

## 4. Viktiga nästa steg för en rigorös bakåträkning

1. **Samma biomassakomponenter först:** Kontrollera vad 2010, 2015 och 2018 faktiskt innefattar (stam, barr/löv, grenar, bark, rötter), med originalmetadata. Om komponenterna avviker hjälper ingen bonitetsmodell.
2. **Rumslig bonitet/produktivitet:** Undersök NMD2018 produktivitetsband 10 och eventuellt Skogsstyrelsens ståndortsindexraster 2025 för Luleå. Produktivitet (markklass) och faktisk bonitet (m³sk/ha/år) får inte förväxlas. Verifiera rasterkällans EPSG-kod och datum före transformation till gemensamt analysraster i **EPSG:3006**.
3. **Tillväxt som funktion av ålder, trädslag och ståndortsindex:** Kalibrera en passande produktions-/tillväxtfunktion (exempelvis dokumenterad skoglig tillväxtmodell) snarare än att anta samma årsproduktion oavsett beståndsålder. På mycket gamla bestånd måste nettotillväxt och avgång kunna vara låga eller negativa.
4. **Skogliga uttag:** Komplettera registrerad slutavverkning med gallring, andra uttag, skador och naturlig avgång. Att en yta saknar registrerad avverkning är inte bevis för orörd skog.
5. **Korsvalidering från 2015 och 2018:** Om båda referensåren, med samma bonitet- och tillväxtfunktion, ger en liknande uppskattning av 2010 stärker det rimligheten. Om de skiljer sig, granska metodskillnader mellan biomassamodellerna 2015 och 2018.
6. **Fältreferens:** Kontrollera utfallet mot Riksskogstaxeringens regionala intervall och, om tillgängligt, oberoende provytor och tidssamordnad inventeringsdata innan årsvis korrigering av kolförrådet.

## 5. Bedömning av möjlig korrigering

En osäker framräkning från biomassamodellen 2018 är **inte en extern fältobservation**. Om både 2015 och 2018 bakåträknade värden hamnar under 2010 års modellvärde utgör det en varningssignal, inte en verifierad skalfaktor. Behåll samtliga originalraster och märk modellens alla resultat **scenario**. En eventuell harmoniserad tidsserie behöver dokumentera vilka komponenter, produktionsmodeller, bonitetsantaganden och mätfel som hanteras.


## 6. Åldersstratifierad diagnostik och villkor för en möjlig ersättningsserie (PR #134)

Eftersom syftet kan bli att använda ett rekonstruerat 2010-värde som substitut för dagens modellvärde krävs att metoden **inte** lärs upp för att imitera 2010 års misstänkt avvikande värde. De två möjliga senare referenserna 2015 och 2018 är fortfarande modellprodukter. Det är särskilt viktigt att kontrollera om de överensstämmer *efter* en oberoende tillväxtframskrivning, utan att använda 2010 som styrparameter.

Från samma gemensamma 25-metersraster i EPSG:3006 (NMD2018-skog, ingen registrerad avverkning 2011–2018, giltig gran/tall-balans och ålder ≥20 år) erhålls följande **årsvis normaliserade modellskillnader**, ton TS/ha/år. Det är inte observerad årlig nettotillväxt:

| Ålder enligt 2010-modellen | Skillnad 2010–2015 | Skillnad 2015–2018 | Skillnad 2010–2018 |
|---|---:|---:|---:|
| 20–39 år | +3,88 | +3,40 | +3,70 |
| 40–59 år | +1,30 | +2,93 | +1,91 |
| 60–79 år | −2,20 | +2,81 | −0,32 |
| 80–99 år | −4,50 | +1,77 | −2,15 |
| 100–139 år | −5,51 | +0,50 | −3,26 |
| 140 år och äldre | −18,40 | −0,28 | −11,61 |

Att äldre skog modelleras med **kraftig minskning 2010–2015** men samtidigt med betydligt svagare minskning eller ökning 2015–2018 är svårt att tolka som enbart vanlig nettotillväxt i samma beståndspopulation. Det är en stark indikation på behov av modell- och komponentrevision, **inte** tillräcklig grund för att välja vilken av de tre modellerna som är korrekt. 140+-gruppen omfattar bara omkring 404 ha och är särskilt känslig för urval eller modellfel.

**Datakälla för diagnostiken:** `docs/data/gran_tall_balans_2005_2010.json`, under `fine_volume_control`, ursprungligen beräknad direkt från raster i PR #130. Nytt script `scripts/diagnose_age_backcast_consistency.py` verifierar att icke överlappande åldersklasser summerar till exakt samma biomassa och cellpopulation som den redan godkända jämförelsen. Den härledda filen `docs/data/bonitet_alder_valideringsdiagnostik.json` publiceras endast efter körd QA.

### Villkor för att använda rekonstruerad biomassa som alternativ till 2010 års raster

1. **År- och komponentjämförbarhet:** Exakt samma definition av levande biomassa i ton torrsubstans per hektar och kompatibel markmask verifierad för ursprungsmodellerna 2015/2018 och målåret 2010.
2. **Ståndortsindex/bonitet:** Lokalt raster för SI verifierat med trädslag, modellens avsiktsår, raster-CRS och korrekta enheter. 2025 års SI får prövas som tidsstabil ståndortsegenskap men dess källår är inte en historisk skogsinventering.
3. **Tillväxtfunktion:** Dokumenterad biologiskt motiverad tillväxt- och avgångsfunktion som varierar med ålder, trädslag, SI och volym, inte bara en konstant andel av regional genomsnittsbonitet.
4. **Händelser:** Gallring, slutavverkning, naturlig avgång, brand, skador och nyrekrytering hanteras åtminstone som osäkerhets-/exklusionskategori. En mask för *ingen registrerad slutavverkning* betyder inte ingen beståndsförändring.
5. **Tvåankarskontroll:** Rekonstruera 2010 **var för sig** från 2015 och 2018 utan att justera funktioner med hjälp av 2010 års modellvärde. Kvantifiera skillnad mellan ankaren per ålder, SI, trädslag, volym och geografisk zon.
6. **Extern kontroll:** Riksskogstaxeringens regionala biomassastatistik och oberoende provytor (med giltig datamodell/geolokalisering) används för validering och osäkerhet, aldrig för att påstå kommuntotal direkt från ett olämpligt urval.
7. **Versionerad publicering:** Ett godkänt alternativ får en separat 2010-rasterfil, separat metadata, cellvis NoData/urvalsmask och dokumenterade osäkerhetsintervall. Ursprungsrastret bevaras och är standard tills alternativets validitet bedömts.

**Beslut hittills:** Resultaten är fortfarande inte en åldersberoende tillväxtmodell och inget korrigerat raster har skapats. En biologiskt rekonstruerad 2010-serie kan potentiellt ersätta den äldre modellen i en särskilt märkt analysvy, men bara efter stegen ovan. Att flera bakåträknade scenarioresultat ligger under 2010 års originalmodell är inte ensamt ett valideringskriterium.

### Källor till kommande lokala ståndortsindex

Skogsstyrelsen publicerar geodatabeskrivningar för **Ståndortsindex 2025** och skogliga grunddata. Dessa är modellskattningar och behöver vara rätt trädslag samt kompatibel tidpunkt/CRS innan de kan användas.

- https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/skogsstyrelsens-geodata/
- https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/geodatatjanster/ladda-ner-geodata/
- https://www.skogskunskap.se/rakna-med-verktyg/mata-skogen/bonitet/

