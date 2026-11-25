# SGD2 Luleå 2018: undersökning av laserskanning med och utan löv

## Viktig källskillnad – 2026 års beskrivning blandar inte ihop årgångarna

Användaren har påpekat fältet `Lov_Avlov` i [Skogsstyrelsens produktbeskrivning via `geodatatjanster/produktbeskrivningar/raster-skogliga-grunddata---produktbeskrivning.pdf`](https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/raster-skogliga-grunddata---produktbeskrivning.pdf). Den versionen är daterad **2026-04-01** och har förändringsförteckning med **SGD3**. Vi analyserar däremot exakt `SGD2_BIO.tif` från **omdrev 2** med laserskanning i Luleå **2018**.

Det relevanta äldre dokumentet [Skogliga grunddata – produktbeskrivning 2025-12-09, sidan 6](https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/skogliga-grunddata/raster-skogliga-grunddata---produktbeskrivning.pdf) har redan motsvarande fält i ESRI-shapefil per **2,5 × 2,5 km**: `Lov_Avlov` anger **1=med löv, 2=utan löv**. Datum kan anges som **sista datumet** när en ruta skannats flera gånger. Det beskriver skanningsförhållanden, inte om lövmassan ingår i skattningens definierade biomassa.

Produktbeskrivningens kvalitetsavsnitt anger att skanning med löv **kan riskera överskattning** av volym, biomassa och grundyta eftersom fler laserreturer registreras högt i lövkronorna; skanning utan löv kan ge **underskattning**. Detta är risker, inte kalibrerade felkoefficienter.

## Det finns redan en källkontrollerad 2018-datumbas

`docs/data/sgd2_lulea_scan_years.json` (sökt 2026-11-17) har **540** verifierade omdrev-2-skanningsrutor som omfattas av Luleås arbetsgräns, samtliga med **2018** som år. Månadsdatumen finns i denna inventering (bland annat juli, augusti och september), men datumen får **inte** automatiskt översättas till lövstatus; det är just vad `Lov_Avlov` ska pröva.

## Ny verifierbar källkontroll

`scripts/audit_sgd2_leaf_conditions.py` frågar direkt samma originaltjänst
`https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSkogligaGrunddataMetadata/MapServer/0`
som redan använts till den tidigare skanningsårsrevisionen. Skriptet:
1. Verifierar kommunens arbetsgräns i **EPSG:4326**, ArcGIS returnerar geometrier i EPSG:4326 och filtrerar omdrev **2**, kommun Luleå samt geografisk överlapp.
2. Kontrollerar att faktiskt fält `Lov_Avlov` **finns på just den här gamla SGD2-tjänsten**. Om det saknas blir samtliga status **okänt**, inte antagen "med löv" för juli–september.
3. Klassar endast koder **1=med löv**, **2=utan löv**, och övriga eller tomma värden till **okänt**.
4. Korsar skanningsmånad med fältstatus och kontrollerar att rutor och månadssummor stämmer.
5. Behåller ursprungliga attribut-ID, datumets månad och lövstatus i GitHub Actions-**artefakt**, och gör **inte** ännu några påståenden om täckning i hektar eller ton TS.

Artefakten är en källmetadata-inventering, **inte en geografisk polygonkarta** och **inte ett rastercellsviktat biomassaresultat**. GitHub Actions kör inte `git push` och ändrar inte webbplatsens biomassasummor.

## Följande steg: faktiskt biomassaöverlägg

För analys av biomassavärden och fördelningen mellan tall/gran/löv krävs därefter att metadata **per indexruta** matchas till original-SGD2-biomassa i **EPSG:3006, 10m** och trädslagsskiktets bekräftade källa, upplösning och CRS. Rasterceller i kommunens arbetsgräns måste maskas och viktas **i källrastretd faktiska CRS**, och varje pixel får högst en fastställd indexruta; överlappande rutor ska flaggas. Därefter kan ton TS per lövstatus jämföras med samma 2010- och 2015-celler efter **full omprojicering** till den avsedda analysgridden. Enbart datum eller ett generiskt SGD3-dokument räcker inte.

**Vetenskaplig begränsning:** Löv-/avlövad skanning kan vara geografiskt sammanblandad med växtplats, trädslag, skogsbeståndets ålder, avverkning och höjd. En skillnad mellan grupperna bevisar inte skanningseffekt. Om nästan hela Luleå skannats under en lövstatus saknas en meningsfull lokal kontrollgrupp och någon kausal "lövkorrektion" ska inte konstrueras.
