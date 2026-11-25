# 2010 års biomassa – kontroll av avverkning och känslighetsanalys utan kausal kalibrering

## Verifierat mot föregående körningar

- PR #99/101: **2 456 410** gemensamt giltiga 25m EPSG:3006-celler, summerad råvärdesskillnad 2010–2018 **18 566 342,73**. Fast NMD2018 klass 118/128 omfattar **469 240** celler och står för **10 430 209,96** av nettoskillnaden.
- PR #102, godkänd körning [45621363051](https://github.com/Lulea-statistik/kol-mark-och-trad/actions/runs/45621363051): av NMD118/128-celler med modellerad virkesvolym 2010 minst 100 finns **119 269** celler. Av dessa överlappar **84 819** daterad registrerad avverkning 2011–2018 och **34 450** saknar registrerad överlapp.
- De 84 819 med registrerad avverkning står för **9 666 777,60** råvärdesenheters positiv nettoskillnad. De 34 450 utan registrerad avverkning står för **2 312 077,91**, av totalt **11 978 855,51** för högvolymgruppen. Summorna stämmer med PR #102 och betyder **inte** att avverkningen orsakat 80,7 procent av skillnaden.

## Känslighetsscenarier – uttryckligen inte en korrigerad totalsumma

Analysen gör en enda transparent matematisk intervention: låt `a` vara en *antagen* andel av nettoskillnaden **2 312 077,91** i 34 450 högvolymceller **utan registrerad avverkning** som hypotetiskt är metodavvikelse. `a` = 0, 0,25, 0,50 eller 1,00. Registrerat avverkade celler och alla andra grupper lämnas orörda.

`illustrativ råsumma 2010 = 188 867 036,33 - a × 2 312 077,91`

| Antagen metodandel i denna grupp | Illustrativ 2010-råsumma (gemensamt giltiga celler) | Skillnad från originaljämförelsen |
|---|---:|---:|
| 0 % | 188 867 036 | 0 |
| 25 % | 188 289 017 | −578 019 |
| 50 % | 187 710 997 | −1 156 039 |
| 100 % | 186 554 958 | −2 312 078 |

Alla ovanstående siffror är **råvärdessummor**, inte ton biomassa eller kol. **Ingen av dessa procentsatser har empiriskt skattats.** Tabellens 100 % är en mycket stark hypotetisk förutsättning, **inte ett övre statistiskt konfidensintervall** eller en rekommenderad korrigering. Avsaknad av registrerad avverkning betyder inte att ingen avverkning skett. Att `2018 < 2010` säger heller inte vilken årsmodell som är mer korrekt.

Den maximala hypotetiska justeringen i denna avgränsade delpopulation motsvarar ungefär **1,22 % av 2010 års gemensamma råsumma**, men vi får inte tolka detta som maximal modellbias i hela kommunen. Bias kan också finnas i alla andra cellkategorier, inklusive registrerade avverkningar.

## Viktig utökad källkontroll: 2010:s biomassakomponenter och enhet

De nedanstående källorna beskriver äldre **SLU Skogskarta/kNN 2005/2010** som *annan produktdefinition* än SLU Skogskarta 2015:

1. SCB, **Markräkenskaper för ekosystemtjänster (2017)**, [rapport sid. 45](https://www.scb.se/contentassets/6d29a226fcd34a0fa192c97c8ec339dc/mi1301_2015a01_br_mi71br1701eng.pdf), beskriver biomassa i äldre Forest Map som ovan- **och** underjordisk biomassa, och det variabelmaterial som används anges som **kg biomassa per hektar**.
2. KTH, **Gunnar Wohletz (2011), A GIS-model to estimate a sustainable potential of forest fuel for energy generation in the municipality of Växjö**, [avsnitt 2.4.2](https://static.wm3.se/sites/2/media/24651_GIS-studie_om_biomassapotentialen_i_Vaxjo_kommun.pdf), beskriver kNN-biomassan i **kg/ha**, inklusive stam, grenar/barr och stubbar/rötter >2mm. **Observera:** studien använder äldre kNN-data och bekräftar inte nödvändigtvis exakt variabelinnehåll i vårt arkiverade **2010**-raster.
3. Skogsstyrelsen/SLU:s [produktbeskrivning för 2015 års Skogskarta](https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/raster-slu-skogskarta---produktbeskrivning.pdf), sidan 3, anger **ton torrsubstans/ha, stamved + grenar + toppar, utan stubbar/rötter**.
4. En akademisk [2025-studie, supplement om SLU:s 2010-karta](https://hess.copernicus.org/articles/29/5493/2025/hess-29-5493-2025-supplement.pdf) beskriver **2010 års bio-slu som ovanjordisk biomassa i ton/ha**. Detta står i spänning med de äldre kNN-beskrivningarna och kan bero på skalning, olika derivat eller tolkning.

**Här finns en uppenbar definitionskonflikt som inte får lösas genom antaganden.** Det faktiska projektarkivet är en *klippt derivatfil*, och `cache_biomass_release.py` säger att den behåller pixelråvärden och original-CRS men **verifierar inte fysiska enheter**. Ett äldre nationellt biomassaraster i kg/ha kan ha bearbetats eller normaliserats tidigare i arbetsflödet, och en råvärdesnivå runt 88 i vårt 2010-extrakt är **inte ett bevis** för att detta raster mäts i ton/ha.

Innan publicering av fysisk 2010-summa måste vi fastställa originalets specifika **source_url, band SCALE/OFFSET, råvärdesfördelning, eventuell applikationsnormalisering och om rötter ingår**. Kontrollera `lulea_biomass_2010_provenance.json` samt arkiveringsskriptet och fråga SLU om det kvarstår oklarheter. Det är inte vetenskapligt försvarbart att enbart välja en kvot mellan 2010 och 2018 för att få deras totalsummor att sammanfalla.

## Publiceringspolicy

- **Original 2010** och **arealharmoniserad skogsreferens från PR #99** behålls oförändrade.
- Scenarioutfall sparas endast som **diagnostik** i GitHub Actions-artefakten, inte som nytt kommunalt biomassaförråd eller granskad trend.
- Ingen licensierad SMD2000-geometri eller källraster distribueras.
- Nästa forskningssteg bör jämföra **verifierade enhetliga biomassakomponenter** på samma celler inom dokumenterat stabil skog samt avverkningsområden, och redovisa tids- respektive metodpåverkan separat.

## Reproducerbarhet

`scripts/biomass2010_nonharvest_sensitivity.py` läser ett låst PR99/101-baslinjedokument och den fullständiga godkända PR102-diagnostiken (körning 45621363051). Det validerar CRS, population, volymstrata och både registrerade/oregistrerade gruppers exakt avstämda raw delta. `.github/workflows/biomass2010-nonharvest-sensitivity.yml` arkiverar den maskinläsbara diagnostiken, och tester spärrar alla numeriska 2010-tonvärden.
