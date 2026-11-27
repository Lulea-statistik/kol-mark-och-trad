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
