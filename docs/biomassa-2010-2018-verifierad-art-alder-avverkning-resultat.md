# Resultat: trädslag, ålder och registrerad avverkning i biomassamodellerna 2010–2018

## Datakälla och verifiering, 25 november 2026

**Faktisk datakörning** [GitHub Actions #45636754940](https://github.com/Lulea-statistik/kol-mark-och-trad/actions/runs/45636754940) har status **success**, baserad på PR #112 (merged). Resultat är läst direkt från dess artefakt **`biomass-2010-species-age-harvest-2018-comparison`**, id **15034486809**, fil **`biomass_species_age_harvest_2010_2018.json`**. Alla tabeller nedan kommer från denna faktiska JSON, inte simulering eller förväntade tal.

Källornas original-CRS har kontrollerats av analysen: **EPSG:3021** för biomassamodell 2010, modellerad 2010-trädslagsvolym och ålder; **EPSG:3006** för 2015, 2018 och NMD2018. Alla rastergridden har reprojicerats fullt till **EPSG:3006 25 × 25 m**, med **0,0625 ha per cell**. Skogsstyrelsens daterade avverkningspolygoner 2011–2018 hanteras i samma mål-CRS. **Gemensamt giltig ursprungspopulation: 2 456 410 celler.** Samma celler följs mellan biomassamodellerna inom varje mask; NoData ersätts inte med noll.

Enhet: **ton torrsubstans per hektar (ton TS/ha)**, vilket bekräftats direkt av SLU för exakt 2010-raster. Summerad ton TS är varje biomassamodells skattning inom en bestämd geografisk mask, **inte en fältvaliderad förändring av verklig biomassa**. Exakta jämförbarheten i barr-/lövandelar och olika modell-/höjdtrösklar är inte verifierad.

## Huvudresultat 1: skog enligt NMD2018, utan registrerad avverkning 2011–2018

Totalt **1 694 808 celler, 105 925,5 ha**, med modellskattade torrmassor **9,347 Mton TS 2010**, **8,619 Mton TS 2015**, **9,382 Mton TS 2018**: modellkvot **+0,37 % 2018/2010**. Detta är dock starkt heterogent mellan modellerad 2010-trädslagsdominans:

| Dominans 2010 (volymmodell) | Antal celler | 2010 ton TS/ha | 2018 ton TS/ha | 2015/2010 | 2018/2010 |
|---|---:|---:|---:|---:|---:|
| Tall | 606 638 | 84,3 | 79,5 | −7,3 % | **−5,6 %** |
| Gran | 43 861 | 149,3 | 110,0 | −32,2 % | **−26,3 %** |
| Bland | 208 908 | 138,6 | 115,7 | −22,3 % | **−16,5 %** |
| Löv | **1** | 62,9 | 120,6 | Ej tolkningsbart | **Ej tolkningsbart** |
| Oklassad | 835 400 | 75,3 | 87,2 | +1,1 % | **+15,8 %** |

**Viktigt metodproblem:** Lövklassningen är praktiskt taget oanvändbar. En enda cell hamnar i ren `DECIDUOUSVOL`-dominans, medan **835 400 celler (49,3 %)** är oklassade. Klassifikationen kräver minst 60 % av `PINEVOL`, `SPRUCEVOL` eller `DECIDUOUSVOL`, minsta totalvolym 20 och högst 20 % komponentavvikelse. **`BIRCHVOL` inkluderas inte separat**, eftersom definitionen av `DECIDUOUSVOL` i relation till björk inte är verifierad och riskerar dubbelräkning. Trädslagssiffror avser bara klasser som passerat urvalet, inte all granskad skog; en slutsats om lövskog eller total kommunal andel tall/gran är inte tillåten.

## Huvudresultat 2: stark åldersgradient, även utan registrerad avverkning

Nedanstående är **2018/2010-kvot mellan modellerad biomassa** i samma celler, i NMD2018-skog med ingen registrerad avverkning. Ålder avser **2010 års SLU-modell**, inte fältmätt beståndsålder.

| Modellerad ålder 2010 | Tall (celler) | Tall, 2018/2010 | Gran (celler) | Gran, 2018/2010 |
|---|---:|---:|---:|---:|
| 20–39 år | 30 432 | **+54,0 %** | 792 | **+45,4 %** |
| 40–59 år | 103 207 | **+21,9 %** | 646 | **−9,4 %** |
| 60–79 år | 180 066 | **−1,4 %** | 2 503 | **−13,7 %** |
| 80–99 år | 200 802 | **−11,7 %** | 17 057 | **−13,2 %** |
| 100–139 år | 87 611 | **−17,3 %** | 17 516 | **−27,7 %** |
| 140–499 år | 1 715 | **−30,5 %** | 5 286 | **−56,3 %** |

**Mönstret:** äldre modellerat 2010-bestånd samvarierar med lägre skattad 2018-biomassa relativt 2010. Skillnaderna är särskilt stora i äldre grandominerade celler. Det är förenligt med flera alternativa hypoteser, som ska hållas separata: faktisk gallring/avverkning som saknas i registret, modellernas varierande funktioner i åldrande/volymrika bestånd, felaktig 2010-skogsmask, skilda 3m-/nollregler, mätår, nedgång i skogens hälsa, eller kNN-modellernas variation med ålder och täckning. Det är **inte** ett belägg för att en viss Marklund- eller Petersson-funktion överskattar biomassan eller att 2010-rastret behöver en viss procentuell korrektion.

För gran är **40–59 årsgruppen liten (646 celler)** och bör inte ges större tolkningsvikt än de större 80–139-årsgrupperna. För 140–499 år behöver fördelning och rimlighet hos 2010 års modellerade ålder granskas, liksom vilka extrema biomassa-/volymceller som påverkar medelvärdet.

## Huvudresultat 3: samma 2010-volymmask visar större negativ skillnad

Om masken i stället utgår från **2010 års modellerade totalvolym ≥50** och ingen registrerad avverkning ( **1 792 332 celler, 112 020,75 ha** ) är totalsummorna **10,382 Mton TS 2010**, **8,705 Mton TS 2015**, **9,402 Mton TS 2018**. Den modellerade 2018/2010-kvoten är **−9,43 %**.

Inom denna mask är den modellerade skillnaden:
- Tall, **700 760 celler**: **−14,3 %**.
- Gran, **52 428 celler**: **−36,2 %**.
- Bland, **232 113 celler**: **−22,1 %**.
- Oklassad, **807 030 celler**: **+4,1 %**.
- Löv: **1 cell**, **ej tolkningsbar**.

Masken kan bevara faktiska kalavverkningsområden som inte registrerats, men kan även inkludera mark där 2010 års modell felaktigt fördelat virkesvolym (bland annat vatten). Vi kan därför inte direkt tillskriva de **9,43 procenten** antingen en modellbias eller faktisk förlust. NMD2018-skogsmark är ett efterhandsurval från 2018 och kan omvänt utesluta verkligt avverkad skog från 2010.

## Huvudresultat 4: registrerade avverkningar ger ett helt annat mönster

Inom 2010 års volym≥50-mask överlappar **104 728 celler (6 545,5 ha)** registrerad avverkning 2011–2018. Torrmassaskattningarna där är **790 195 ton TS 2010** och **95 732 ton TS 2018**, modellkvot **−87,88 %**.

I samma 2010-mask, men **utan registrerad avverkning**, är modellkvoten endast **−9,43 %**. Den stora skillnaden stödjer att avverkningar har en väsentlig roll i den tidigare observerade minskningen, men innebär **inte** att avverkning ensam kausalt förklarar varje ändrad rastercell: tidpunkter, överlappskvalitet, andra skogsåtgärder och metodskillnader kan påverka.

## Uppföljning PR #119 – sammanvägda äldre bestånd, verifierad 26 november 2026

Körning [#45838159388](https://github.com/Lulea-statistik/kol-mark-och-trad/actions/runs/45838159388) slutfördes med **success**. Resultatet avser **samma celler** inom NMD2018-skog, med **ingen registrerad avverkning 2011–2018**, och stratifiering efter *modellerad* ålder 2010. Åldersurvalen är **nästlade**, inte separata åldersklasser; minst 100 år ingår även i minst 80, 60 och 20 år.

| Modellerad ålder 2010 | Celler | Areal ha | 2010 ton TS/ha | 2015 ton TS/ha | 2018 ton TS/ha | Modellskillnad 2018/2010 |
|---|---:|---:|---:|---:|---:|---:|
| ≥20 år | 1 649 647 | 103 102,94 | 90,40 | 82,82 | 90,06 | −0,37 % |
| ≥60 år | 1 029 451 | 64 340,69 | 111,29 | 91,97 | 97,95 | −11,99 % |
| ≥80 år | 582 663 | 36 416,44 | 125,40 | 99,83 | 103,91 | −17,14 % |
| ≥100 år | 177 484 | 11 092,75 | 134,24 | 102,28 | 103,59 | −22,83 % |

För ≥100 år är delgruppens relativa modellskillnad **−17,54 % för tall** och **−36,32 % för gran**, utifrån 2010-modellerad trädslagsdominans. För ≥60 år är dessa −9,83 % och −26,86 %. Lövdominans är fortfarande i praktiken oklassificerbar med nuvarande komponenttolkning; tall/granresultaten representerar bara sina respektive klassificerade urval.

**Tolkning:** Skillnaden ökar när urvalet begränsas till äldre bestånd. Det är förenligt med en modellrelaterad ålders-/volymeffekt men också med oregistrerad gallring/avverkning, skillnader i mätår och återstående klassningsproblem. Ålder, volym och 2010-biomassa har inte oberoende modellunderlag. Inte heller garanterar NMD2018-skog att området var skog 2010. **Resultatet får inte beskrivas som verifierad faktisk biomassaminskning eller användas för att korrigera 2010 års raster.**

**Nästa test:** För att minska risken att trädslagsbyten och 2010 års klassningsfel driver mönstret samkörs modellen för *2005 och 2010 års trädslagsdominans* med 2010/2018-biomassa, NMD2018 och daterade avverkningar. Stabil **modellerad** dominans är fortfarande inte fältverifierad oförändrad skog.

## Förslag till nästa analys

1. **Åtgärda trädslagsklassificeringen.** Granska originalbetydelsen av `DECIDUOUSVOL` kontra `BIRCHVOL`, samt komponenternas summering mot `TOTALVOL` för 2010. Genomför en diagnostik som visar *varför* så många celler blir oklassade (låg volym, överlappande fraktioner, saknade värden, summeringsgap, ingen art når 60%). Korrigera först efter källverifiering; aldrig hitta på björk- eller lövandelar.
2. **Robusthet för äldre gran.** Åldersklasser 80–99 och 100–139 och 140+ ska granskas med medel/median per cell för 2010/2015/2018, 2010 års modellerade volym, kvalitetssignal och spatial spridning. Kontrollera avverkning enligt uppdaterad historik och 2018 års NMD-klasser. Ålder på 2010-rastret är sammodellerad med volym och kan inte betraktas som oberoende förklaringsvariabel.
3. **Separera mekanismer:** Testa skog äldre än 60 år som 2005–2010 hade stabil trädslagsdominans, och kontrollera både modellerad 2010-ålder och daterade avverkningar 2011–2018. Skog utan *registrerad* avverkning kan fortfarande ha avverkats/gallrats.
4. **Funktionernas roll:** Petersson (1999) och Marklund (1988) är relevanta metodreferenser, men deras faktiska implementering i `Biomass_leaf.tif` och `SGD2_BIO.tif` är inte fullständigt källverifierad. **Ingen automatisk %-korrigering** av 2010 eller 2018 tillåts.

**Slutsats:** De faktiska resultaten stärker misstanken om betydande *systematiska modellskillnader i äldre bestånd*, särskilt gran, men medger ännu inte att de kvantifieras separat från verkliga skogsförändringar eller historiska urvalsproblem. Summorna är modellerad torrmassa, inte en oberoende uppmätt stockförändring.
