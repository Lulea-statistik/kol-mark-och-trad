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

## Uppföljning PR #120 – stabil modellerad tall och gran 2005–2010

Analysen från den **godkända** [Actions-körningen #45957345496](https://github.com/Lulea-statistik/kol-mark-och-trad/actions/runs/45957345496) samkör 2005 och 2010 års modellerade `PINEVOL`/`SPRUCEVOL` mot `TOTALVOL`. En cell klassas som **stabil tall** eller **stabil gran** endast om samma trädslag svarar för minst **60 % av totalvolymen i båda årgångarna**. Endast NMD2018-skog utan registrerad avverkning 2011–2018 ingår i tabellen. Samma 25-metersceller jämförs i biomassaraster 2010, 2015 och 2018.

| Minsta modellerade ålder 2010 | Stabil tall: ha | Tall: 2018/2010 | Stabil gran: ha | Gran: 2018/2010 |
|---|---:|---:|---:|---:|
| ≥20 år | 21 790,56 | −4,67 % | 54,63 | −36,18 % |
| ≥60 år | 17 336,44 | −8,40 % | 54,31 | −36,23 % |
| ≥80 år | 11 239,50 | −12,16 % | 54,19 | −36,23 % |
| ≥100 år | 3 414,38 | −15,19 % | 49,31 | −37,75 % |

**Tolkning:** Tallens åldersgradient kvarstår under kravet på stabil modellerad dominans. Äldre gran visar en stark negativ modellkvot men stabilt granurval är mycket litet: vid ≥100 år endast **789 celler**, jämfört med **54 630 tallceller**. Det går inte att avgöra om detta beror på förändrad faktisk skog, modellernas olika fördelning mellan trädslag, dominansgränsen eller bristande additivitet mellan volymkomponenter.

**Uppföljande metodtest PR #121:** Ursprungliga tall-/granvolymer klassificeras var för sig 2005 och 2010 vid gränserna 40, 50, 60 och 70 % av respektive `TOTALVOL`. En fullständig 4×4-matris över tall, gran, varken tall/gran och ogiltig/låg volym beräknas för varje åldersurval. Denna diagnostik får inte tolkas som faktiskt byte av huvudträdslag eller skogsförlust.

## Uppföljning PR #121 – varför få granceller blir stabila

Den [verifierade rasterkörningen #45965534583](https://github.com/Lulea-statistik/kol-mark-och-trad/actions/runs/45965534583) jämförde modellerad trädslagsdominans 2005 och 2010 på exakt samma celler. För NMD2018-skog utan registrerad avverkning och modellerad ålder 2010 **minst 100 år** (172 028 celler) gav försöket följande resultat:

| Dominansgräns | Gran 2005, celler | Gran 2010, celler | Stabil gran, celler | Stabil gran, ha |
|---|---:|---:|---:|---:|
| 40 % | 12 955 | 32 138 | 6 677 | 417,31 |
| 50 % | 12 532 | 27 089 | 7 571 | 473,19 |
| 60 % | 1 704 | 16 294 | 789 | 49,31 |
| 70 % | 165 | 10 107 | 51 | 3,19 |

Vid 60 % hade 13 197 av de 16 294 grandominerade 2010-cellerna klassats som **varken tall eller gran** 2005; 2 180 klassades som **tall** och 128 som låg/ogiltig volym. Det är klassificeringsövergångar i skattade raster, inte verifierade biologiska förändringar. Tall prioriteras om både tall och gran passerar gränsen i samma cell; detta är möjligt särskilt vid trösklar 40–50 % och förklarar varför klassade stabila gran-celler inte måste öka monotont när gränsen sänks.

**Fortsättning i PR #122:** Beräkna parvisa andelar `PINEVOL/TOTALVOL` och `SPRUCEVOL/TOTALVOL` för 2005 och 2010 på identiska celler. Redovisa medel- och absolut förändring i procentenheter, storleksfördelning, närhet till 60 %-gränsen, tröskelpassager samt fall där en komponent överstiger totalvolymen. Modellskillnad och verklig förändring är fortfarande inte identifierade separat.

## Nio balansklasser gran/tall 2005–2010 – PR #123

Ett kompletterande test ersätter hård tall-/grandominans med en parvis **granandel av tall + gran**: `SPRUCEVOL/(SPRUCEVOL+PINEVOL)`, beräknad separat i 2005 och 2010 års raster. Analysen använder **nio gemensamma balansklasser** 10/90, 20/80, 30/70, 40/60, 50/50, 60/40, 70/30, 80/20, 90/10 (gran/tall). Klasserna har gränser 0–15 %, 15–25 %, …, 85–100 % gran. Andelen är inte en andel av all virkesvolym; övriga arter ingår inte i nämnaren. Endast celler med positiv summa tall + gran båda åren används.

**Utdata:** (a) 9×9-matris över 2005-rad/2010-kolumn, viktad i ha, (b) de båda årens arealfördelning över klasserna, (c) modellerad biomassa 2010 och 2018 i ton TS/ha efter **2010 års** balansklass och per avgränsad, geografiskt identisk population. Cellantal och biomassasummor stäms av programmässigt. Urvalet är NMD2018-skog utan registrerad avverkning 2011–2018, separat för modellerad 2010-ålder ≥20/60/80/100 år. Raster-originalens CRS kontrolleras och hela rastergridden reprojiceras till EPSG:3006, 25 m före analys.

**Tolkningsbegränsning:** Balansklassändringar visar olika rastermodellers skattning, inte verifierade faktiska trädslagsbyten eller biomassaförändringar. 2005 och 2010 års volymskattningar kan ha metodskillnader och reella beståndsförändringar. **Inga numeriska balansresultat publiceras förrän resultat-JSON har genererats och verifierats av GitHub Actions.**

## Gran/tall-balans och biomassaskillnad inom balansklass (PR #125)

Den publicerade, verifierade filen `docs/data/gran_tall_balans_2005_2010.json` med rasterresultaten från PR #124 möjliggör jämförelse av modellerad biomassa **2018 relativt 2010**, grupperad efter samma cellers **gran/tall-balans 2010**. För modellerad ålder minst 100 år och NMD2018-skog utan registrerad avverkning 2011–2018 är modellkvoten:

| Gran/tall-balans 2010 | 2018 relativt 2010 |
|---|---:|
| 10/90 | −12,09 % |
| 20/80 | −16,88 % |
| 30/70 | −20,69 % |
| 40/60 | −20,86 % |
| 50/50 | −22,82 % |
| 60/40 | −24,09 % |
| 70/30 | −26,91 % |
| 80/20 | −35,05 % |
| 90/10 | −39,65 % |

Mönstret är starkare negativt för mer grandominerad balans. En sådan relation kan bero på **systematiska skillnader mellan biomassamodellerna**, men är inte ett oberoende mått på modellbias. Balansklasserna skattas av historiska modeller och 2010 års trädslags- och biomassamodeller har inte oberoende fel. NMD2018-klass och registrerade avverkningar är inte fullständigt historiskt beståndsbevis; mellanliggande gallring kan saknas.

**Utvidgat test i PR #125:** På samma 25-metersceller beräknas en separat summa av biomassa 2010, 2015, 2018 för **varje** av matrisens 81 övergångar 2005 → 2010. Därmed kan biomassakvoten jämföras *inom samma 2010-balansklass* mellan celler som enligt modellerad balans rört sig mot mer gran, mot mer tall eller legat kvar på diagonalen. Detta prövar en konkurrerande modellförklaring bättre än att bara jämföra hela balansklasser. Alla 81 matrisceller avstäms mot tidigare publicerad total per 2010-balansklass och mot hela cellpopulationen. Slutsatser om **faktiska trädslagsbyten** är fortfarande inte tillåtna. **Resultat från denna utvidgning ska inte användas innan rasterkörningen har slutförts och resultat-JSON publicerats.**

## Resultat från PR #125 – modellförskjutning och biomassaskillnad

Rasterkörning [#45981899353](https://github.com/Lulea-statistik/kol-mark-och-trad/actions/runs/45981899353) är **godkänd** och har producerat matriser med biomassa 2010/2015/2018 för var och en av de 81 balansövergångarna. Analysens urval avser samma giltiga 25 m-rasterceller i EPSG:3006, NMD2018-skog och **ingen registrerad avverkning 2011–2018**. Gruppnamnen avser *modellerad* balansgranandel 2005 → 2010, där mer gran betyder högre gran/tall-klass 2010.

| Modellerad ålder 2010 | Mot mer tall (ha; 2018/2010) | Samma balansklass (ha; 2018/2010) | Mot mer gran (ha; 2018/2010) |
|---|---:|---:|---:|
| ≥20 år | 36 226,7; **+6,24 %** | 26 643,4; **−0,28 %** | 38 204,7; **−5,42 %** |
| ≥60 år | 20 683,5; **−6,82 %** | 17 456,9; **−9,93 %** | 25 488,4; **−15,39 %** |
| ≥80 år | 9 224,7; **−13,50 %** | 9 727,5; **−14,22 %** | 16 932,6; **−18,94 %** |
| ≥100 år | 2 761,1; **−18,57 %** | 2 778,5; **−17,81 %** | 5 210,9; **−24,39 %** |

**Tolkning:** I samtliga fyra överlappande åldersurval uppvisar gruppen "mot mer gran" en lägre modellerad 2018/2010-kvot än gruppen "mot mer tall". Skillnaden kan delvis bero på att övergångsgrupperna har olika fördelning av 2010 års balansklasser, ålder och volym. **Det är därför inte en kausal effekt av en trädslagsförändring.** För att pröva denna invändning visas även ett separat diagram *inom samma balansklass 2010*, baserat på samma 81 biomassasummor. För mycket små grupper bör resultaten tolkas försiktigt.

**Datapublicering:** Resultat-JSON innehåller `matrix_biomass_tTS` och `matrix_biomass_difference_2018_vs_2010_pct`. Dessa fält kommer från PR #125:s lyckade rasterkörning och ska publiceras på `docs/data/gran_tall_balans_2005_2010.json` efter separat kontroll av de 81 delmassorna mot tidigare klasssummor. Tills dess visar webbplatsen ett informationsmeddelande för det nya detaljdiagrammet.

## Test av gran/tall-balans kontrollerat för beståndsålder och virkesvolym (PR #127)

**Syfte:** Pröva om den negativa skillnaden mellan biomassamodellernas 2018/2010-kvot och en högre modellerad granandel 2010 kvarstår när cellerna jämförs inom avgränsade ålders- och volymgrupper.

**Metod:** Samma 25 m-grid i EPSG:3006 (fullt reprojicerade raster), NMD2018-skog, gemensamt täckta celler, ingen *registrerad* avverkning 2011–2018. Granandel = SPRUCEVOL/(SPRUCEVOL+PINEVOL) i 2010 års modellerade trädbiomassarelaterade virkesvolymer. **Icke överlappande åldersklasser 2010:** 20–39, 40–59, 60–79, 80–99, 100–139, minst 140 år. **Icke överlappande volymklasser 2010:** [0,50), [50,100), [100,200), [200,300), [300,∞) i TOTALVOL-rastrets råskala. Inom varje stratum redovisas samtliga nio gran/tall-klasser, cellantal, summa ton TS 2010/2015/2018 och procentuell kvot 2018/2010.

**Revisionskontroller:** 6 × 5 × 9 grupper är en disjunkt partition av samma NMD2018-urval minst 20 år som PR #125. Summor av cellantal och modellerad biomassa per gran/tall-klass och år måste återge den tidigare publicerade datan, annars avbryts analysen. Diagrammet visar inte numeriska värden innan ny raster-JSON publicerats.

**Tolkning:** Detta kontrollerar grovt för observerbara *modellerade* beståndsegenskaper och förhindrar att överlappande åldersurval blandas ihop. Det är inte en regression eller kausal identifiering. Eftersom 2010 års virkesvolym, ålder, granandel och biomassa är modellbaserade och statistiskt kopplade finns risk för korrelerade modellfel samt selektions-/kontrollbias. 2018 års modellvärden kan ha skilda metodantaganden. Ingen säker slutsats om verkliga biomassaförändringar följer enbart av analysen.


## Direkt standardiserad jämförelse av gran/tall-balans, ålder och virkesvolym (PR #128)

**Källa:** Verifierad rasterbaserad sammanställning från PR #127, `docs/data/gran_tall_balans_2005_2010.json`. Samma cellpopulation NMD2018-skog utan registrerad avverkning 2011–2018, 25 m-grid i EPSG:3006, modellerad ålder, virkesvolym och gran/tall-balans från 2010. Standardiseringen beräknas på redan verifierade stratumvisa cellantal och biomassa, utan att approximera cellfördelning från andra källor.

**Metod för att kontrollera sammansättning:** Välj *gemensamt stöd* där **var och en av nio balansklasser har minst 30 celler** inom samma icke överlappande ålder–volym-stratum. Referenspopulationens vikt i stratum `s` är `w_s = N_s / ΣN_s`, där `N_s` är antalet celler från samtliga nio klasser inom gemensamt stöd. Varje balansklass `k` får samma `w_s` och ett standardiserat medelvärde ton TS/ha för vart och ett av 2010 och 2018: `D_kt = Σ_s w_s * M_kst / (0,0625 * n_ks)`. Modellskillnaden beräknas som `100 * (D_k2018/D_k2010 - 1)`. Detta är inte medelvärdet av individuella cellkvoter och inte ett mått på faktisk skogstillväxt.

**Resultat i publicerat, källverifierat rasterunderlag:** Av 30 möjliga ålder–volymkombinationer uppfyller **10** minimikravet. Den sammanlagda målpopulationen i dessa är **1 446 461 celler**, motsvarande cirka 90 404 ha. Klassvis täckning varierar, vilket är en viktig begränsning.

| Gran/tall 2010 | Ojusterad modellskillnad 2018/2010 | Standardiserad modellskillnad 2018/2010 | Täckningsgrad |
|---|---:|---:|---:|
| 10/90 | +3,99 % | −5,31 % | 75,0 % |
| 20/80 | +9,66 % | +0,80 % | 84,0 % |
| 30/70 | +3,48 % | +0,53 % | 92,9 % |
| 40/60 | −2,19 % | +0,33 % | 95,8 % |
| 50/50 | −5,83 % | −0,55 % | 97,6 % |
| 60/40 | −9,28 % | −2,76 % | 97,9 % |
| 70/30 | −12,51 % | −5,62 % | 97,4 % |
| 80/20 | −20,63 % | −6,62 % | 87,1 % |
| 90/10 | −16,22 % | −7,99 % | 84,1 % |

**Huvudslutsats:** Den starkt negativa gradienten i råa biomassakvoter reduceras avsevärt när de nio balansklasserna ges samma fördelning av modellerad ålder och 2010 års totalvolym inom gemensamt stöd. En mer negativ skillnad finns ändå för flera grandominerade klasser. Detta ger **belägg för att sammansättningsskillnader kan förklara en betydande del av den observerade skillnaden**, men inte för att eventuell kvarvarande skillnad orsakas av trädslag eller är faktisk förändring av biomassa.

**Robusthet och osäkerhet:** Skript `scripts/standardize_gran_tall_biomass.py` redovisar dessutom känslighetsberäkningar med minst 10 respektive 100 celler i varje klass och gemensamt stratum. Urvalskravet 30 celler är ett analytiskt val, inte en inferentiell konfidensgräns. Den standardiserade populationen representerar inte alla bestånd – exempelvis mindre vanliga trädslags-/volymkombinationer faller bort. 2010 års ålder, virkesvolym, gran/tall-balans och biomassa är korrelerade modellprodukter; standardisering eliminerar därför inte gemensamma modellfel eller eventuell selektionsbias.

**Verifiering/publicering:** Datafilen `docs/data/gran_tall_standardisering_2010_2018.json` beräknas från den publicerade rasterfilen, stäms av mot totalsummor och publiceras först efter godkänd GitHub Actions-körning av `.github/workflows/standardize-gran-tall-biomass.yml`. Tabellvärden ovan är en direkt beräkning på det publicerade aggregerade underlaget; diagrammet ska inte visa numeriska värden om den genererade filen saknas.


## Känslighetsanalys av standardiseringens minsta cellantal (PR #129)

**Datagrund:** Redan publicerad och verifierad `docs/data/gran_tall_standardisering_2010_2018.json` (från PR #128), där granandelen 2010 är `SPRUCEVOL/(SPRUCEVOL+PINEVOL)`. Samma fasta 25-metersceller i EPSG:3006, NMD2018-skog och ingen registrerad avverkning 2011–2018. Alla nio balansklasser får samma ålder×2010-volymfördelning *inom vart och ett* av känslighetsscenarierna. Minimikravet gäller varje klass i varje gemensamt stratum, inte totalt antal celler.

| Minsta antal celler per klass | Gemensamma ålder–volym-grupper | Gemensam referenspopulation (celler) |
|---|---:|---:|
| 10 | 11 av 30 | 1 452 890 |
| 30 (huvudanalys) | 10 av 30 | 1 446 461 |
| 100 | 9 av 30 | 1 419 617 |

### Standardiserad modellskillnad 2018/2010 vid olika urvalskrav

| Gran/tall 2010 | Minst 10 celler | Minst 30 celler | Minst 100 celler | Spännvidd |
|---|---:|---:|---:|---:|
| 10/90 | −5,22 % | −5,31 % | −4,73 % | 0,58 procentenheter |
| 20/80 | +0,92 % | +0,80 % | +1,52 % | 0,72 procentenheter |
| 30/70 | +0,69 % | +0,53 % | +1,24 % | 0,71 procentenheter |
| 40/60 | +0,48 % | +0,33 % | +0,99 % | 0,66 procentenheter |
| 50/50 | −0,43 % | −0,55 % | +0,07 % | 0,62 procentenheter |
| 60/40 | −2,70 % | −2,76 % | −2,21 % | 0,55 procentenheter |
| 70/30 | −5,58 % | −5,62 % | −5,10 % | 0,52 procentenheter |
| 80/20 | −6,57 % | −6,62 % | −6,00 % | 0,62 procentenheter |
| 90/10 | −7,96 % | −7,99 % | −7,21 % | 0,78 procentenheter |

**Tolkning:** Den standardiserade skillnaden är tämligen stabil mot just dessa tre krav på minsta antal celler: största spännvidd mellan scenarierna är knappt **0,8 procentenheter**. Det kvarstående mer negativa mönstret i grandominerade klasser försvinner alltså inte bara genom att flytta celltröskeln från 10 till 100. Däremot varierar referenspopulationen något, och standardiserade kvoter är fortfarande beroende av gemensamma modellfel i ålder, virkesvolym och biomassa. Detta är **ingen inferentiell osäkerhetsanalys, inget konfidensintervall och inget belägg för kausal trädslagseffekt**.

**Nästa metodsteg:** Om vi ska kvantifiera återstående trädslagsskillnad mer stringent bör vi även redovisa standardiserad modellskillnad i *enskilda ålder×volym-strata* med gruppstorlek och undersöka påverkan av alternativa volymgränser eller spatialt korrelerade fel. Detta förutsätter att resultaten inte övertolkas som observerad beståndsutveckling.

## Förslag till nästa analys

1. **Åtgärda trädslagsklassificeringen.** Granska originalbetydelsen av `DECIDUOUSVOL` kontra `BIRCHVOL`, samt komponenternas summering mot `TOTALVOL` för 2010. Genomför en diagnostik som visar *varför* så många celler blir oklassade (låg volym, överlappande fraktioner, saknade värden, summeringsgap, ingen art når 60%). Korrigera först efter källverifiering; aldrig hitta på björk- eller lövandelar.
2. **Robusthet för äldre gran.** Åldersklasser 80–99 och 100–139 och 140+ ska granskas med medel/median per cell för 2010/2015/2018, 2010 års modellerade volym, kvalitetssignal och spatial spridning. Kontrollera avverkning enligt uppdaterad historik och 2018 års NMD-klasser. Ålder på 2010-rastret är sammodellerad med volym och kan inte betraktas som oberoende förklaringsvariabel.
3. **Separera mekanismer:** Testa skog äldre än 60 år som 2005–2010 hade stabil trädslagsdominans, och kontrollera både modellerad 2010-ålder och daterade avverkningar 2011–2018. Skog utan *registrerad* avverkning kan fortfarande ha avverkats/gallrats.
4. **Funktionernas roll:** Petersson (1999) och Marklund (1988) är relevanta metodreferenser, men deras faktiska implementering i `Biomass_leaf.tif` och `SGD2_BIO.tif` är inte fullständigt källverifierad. **Ingen automatisk %-korrigering** av 2010 eller 2018 tillåts.

**Slutsats:** De faktiska resultaten stärker misstanken om betydande *systematiska modellskillnader i äldre bestånd*, särskilt gran, men medger ännu inte att de kvantifieras separat från verkliga skogsförändringar eller historiska urvalsproblem. Summorna är modellerad torrmassa, inte en oberoende uppmätt stockförändring.
