# Kolförråd i mark och träd – Luleå kommun

GitHub Pages har två sidor: **Karta** (`docs/index.html`) och **Diagram och tabeller** (`docs/statistics.html`). Båda redovisar enbart rasterceller inom Luleå kommuns gräns. Endast ytan inom kommunpolygonen ingår vid summering. Delsummor för bristfälligt rastertäckt del redovisas inte som totalsiffror för hela kommunen.

Första etappen: GitHub Pages-karta, geometri, kontrollerad modell för omräkning och lokal rasterpipeline. **Inga simulerade eller påhittade koldensiteter publiceras.** Kartan visar kommungränsen tills granskade källraster har importerats.

## Källor och avgränsningar

1. **Träd ovan mark**: i första hand Skogsstyrelsens **Skogliga grunddata – Biomassa**, aktuell lämplig omdrevsprodukt, alternativt SLU Skogskarta Biomassa. Produkt, år och enhet måste granskas i metadata. Biomassa är inte samma sak som totalt kol i ekosystemet.
2. **Volym som reserv**: Skogsstyrelsens **Volym** eller SLU Skogskarta Volym bara där giltigt biomassaunderlag saknas. Omvandlingen kräver verifierad trädslags-/region-/produktspecifik faktor från m³sk till ton torr biomassa. Det är ett modellantagande, inte en observation; hög korrelation räcker inte för en universell omräkningsfaktor. Ingen implicit volymfaktor finns i koden.
3. **Markkol**: SLU Kolkartor **Stock_SOC**; totalt markförråd **Stock_All** inkluderar redan **Stock_DOM**. Dessa är två alternativa redovisningslager, aldrig två kolpooler som ska adderas. SLU:s 10 m raster bygger delvis på regionala skattningar, inte 10 m lokala jordprover.

Källor:
- https://gis.slu.se/data/slu_forest_map
- https://www.skogsstyrelsen.se/laddanergeodata
- https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/geodatatjanster/
- https://www.slu.se/miljoanalys/statistik-och-miljodata/miljodatakatalogen/slu-kolkartor/

Skogsstyrelsens raster kan kräva registrerad åtkomst. Lagra inte personliga inloggningsuppgifter i detta repo. Inhämtning av raster och kontroll av licens sker separat.

## Koordinatsystem

`docs/data/lulea_boundary.geojson` är en **arbetsgeometri** hämtad från det befintliga väderprojektet. Koordinaterna ligger i **EPSG:4326** (lon, lat), verifierade mot geografisk utbredning; exakt administrativ gräns ska ersätta arbetsgeometrin före officiell kommunstatistik. Originalrastrets CRS läses och **krävs** i filen; inget implicit EPSG antas. Klippning/mask görs i **originalrastrets CRS**, därefter beräknas förråd som ungefärlig ytintegral i **EPSG:3006** (meter), och slutligen reprojiceras hela pixelgridet till **EPSG:3857** för Leaflet. Enbart transformerad bbox används aldrig som georeferering.

## Exempel på körning

Installera beroenden (Python 3.11+):

```sh
pip install -r requirements.txt
```

Kontrollera GeoTIFF-enheter, NODATA, produkttyp och CRS **innan** körningen. Exempel (hypotetiska filnamn, inga verkliga värden):

```sh
python scripts/process_carbon_raster.py /lokal/skog_biomassa.tif --layer biomass --units tonnes_dry_per_ha --source "Skogsstyrelsen biomassa, omdrev X" --source-year "20XX"
python scripts/process_carbon_raster.py /lokal/markkol.tif --layer soil --units tonnes_C_per_ha --source "SLU Stock_SOC" --source-year "2000-2020"
```

För att använda volym ska dokumenterad trädsammansättning, biomassafunktion och kalibrerad faktor finnas:

```sh
python scripts/process_carbon_raster.py /lokal/virkesvolym.tif --layer volume --units m3sk_per_ha --tonnes-dry-per-m3sk <VERIFIERAD_FAKTOR> --calibration "<KÄLLA OCH METOD>" --source "Skogsstyrelsen Volym, omdrev X" --source-year "20XX"
```

Ersätt de markerade platshållarna före körning. Resultaten blir `docs/data/{layer}.png` och uppdaterat `docs/data/layers.json`. Kontrollera kartans overlay, pixeltäckning och total mot oberoende arealstatistik innan merge. PNG innehåller inga negativa värden eller NODATA som noll.

## Kolenheter

För källvärden i **ton torr biomassa/hektar** används den **preliminära** faktorn `C = 0.5 × biomassans torrvikt`. Molmassomräkning: `CO₂ = C × 44/12`. Detta ger **lagrad mängd omräknad till en CO₂-massa**, inte ett årligt klimatupptag eller ett observerat utsläpp.

**Viktiga återstående arbeten:** verifiera nedladdningsadresser och rastermetadata; ersätta kommunarbetsgeometri med officiell gräns; maskera NODATA och säkra att biomassa avser rätt träddelar; göra trädslagsanpassad volymkalibrering; granska upplösning och marktäckning; ladda in verkliga raster och först därefter publicera kommunala totalsiffror. Behåll rasterår separata så att olika omdrev inte redovisas som en gemensam tidpunkt.

GitHub Pages: välj **Settings → Pages → Deploy from a branch → main /docs** efter att första PR har slagits samman.

## Diagram och tabeller

Sidan `docs/statistics.html` läser samma `docs/data/layers.json` som kartan. Den visar en tabell per produkt med ton C, motsvarande ton CO₂ (lagrad massa, ej utsläpp), täckt yta, geografisk täckning och källår. Diagram skapas bara av verifierade data. SOC och Stock_All redovisas som alternativa marklager utan dubbelräkning; volymreserven särredovisas. Rasterbearbetningen skriver `covered_hectares`, `municipality_hectares` och `coverage_pct_of_municipality` så att felaktigt extrapolerade totalsummor kan undvikas. Inga grannkommuner eller ytterligare buffertzoner räknas med i kommunresultatet.

## Inventera direkta SLU-rasterfiler

Flödet [Inventory SLU carbon and forest raster sources](../../actions/workflows/inventory-slu-sources.yml) kan startas manuellt i GitHub Actions efter sammanslagning. Det går igenom publika kataloglistningar för `gis.slu.se/data/carbon/`, SLU Skogskarta 2015 och Skogliga grunddata utan att hämta stora GeoTIFF-filer. Rapporten `slu-carbon-source-inventory` sparas som körningsartefakt och innehåller möjliga nedladdningsadresser, genomsökta kataloger och källfel.

**Kritisk begränsning:** en katalogträff är inte en importerad/validerad karta. Filformat, koordinatsystem, numeriska enheter, omdrevsår, rättigheter och Luleå-täckning måste fortfarande granskas. Att publika kataloger innehåller gigabyte-stora Sverigeraster innebär inte att de går att lägga direkt i GitHub-repot. När korrekta adresser identifierats bör vi föredra serverbaserad utskärning/raster-COG-fönsterhämtning och bearbeta enbart Luleås yta.


## Inventeringen #1: direkta Norrbottensraster identifierade (2026-11-13)

Den lyckade Actions-körningen [Inventory SLU carbon and forest raster sources #1](https://github.com/Lulea-statistik/kol-mark-och-trad/actions/runs/43408212960) genomsökte 35 kataloger och identifierade 365 filadresser. Två specifika länsraster är:

- [SLU SOC 2023 Norrbottens](https://gis.slu.se/data/carbon/2023/Stock_SOC_2023_Lan/SOC_2023_Norrbottens.tif) – markens organiska kolförråd.
- [SLU Stock_All 2023 Norrbottens](https://gis.slu.se/data/carbon/2023/Stock_All_2023_Lan/Stock_All_2023_Norrbottens.tif) – totalt markförråd; **inkluderar** SOC (ska inte adderas till SOC).
- [SLU Biomass_leaf 2015](https://gis.slu.se/data/slu_forest_map/2015/data/Biomass_leaf.tif) är bara blad-/barrbiomassa och duger inte ensamt som total ovanjordisk biomassa.

Kör [Audit SLU Norrbotten carbon raster metadata](../../actions/workflows/audit-norrbotten-carbon-rasters.yml) efter PR #5. Flödet granskar direkt länsrasterformat och **verifierar om läsbara CRS, NoData, bandmetadata och pixelupplösning finns**, utan att försöka hämta hela Norrbottens raster. Artefakten `slu-norrbotten-carbon-raster-metadata` innehåller alla hittade fält och källfel.

**Innan någon skarp import:** verifiera enhet i SLU:s produktdokumentation (det kan vara något annat än ton C/ha), eventuell skalfaktor, koordinatsystem, förväntad täckning och om länsfilen omfattar Luleås hela kommungräns. Raster ska maskas mot kommunpolygon i ursprungs-CRS och *hela rastergridet* reprojiceras till EPSG:3857 före webbkarta. Publicera inte uppskattade förråd som lokalt uppmätta värden.


## Publicering av riktiga rasterförhandskartor utan kolenheter

Körningen [Preview actual SLU carbon rasters in Lulea #1](https://github.com/Lulea-statistik/kol-mark-och-trad/actions/runs/43410956136) lyckades: två bilder med **613 841 giltiga förhandsbildspixlar per lager** skapades, med kommunmask och faktisk rasterreprojektion. Det är *förhandsbildspixlar*, inte originalrasterceller, provpunkter eller en kommunal koltotal.

Efter PR #8 går det att köra [Publish SLU Lulea carbon preview maps](../../actions/workflows/publish-slu-previews.yml) manuellt. Det återkör den källbaserade förhandskarteringen från SLU, kontrollerar EPSG:3006 och kvalitetsflaggar resultatet, och committar två **transparenta PNG-kartor** plus metadata till `docs/data/preview/`. På webbsidan finns separata förhandslager i **Karta**, utan att blanda okända råvärden med kolserierna. Till skillnad från artifact-filer är dessa direkt åtkomliga via GitHub Pages efter lyckad workflow + Pages deployment.

Färgskalan är **relativ och separat per lager**: man kan se geografiska mönster men inte tolka färgerna som ton C/ha eller direkt jämföra SOC-färg med Stock_All-färg. Årlig kolsänka och kommunala koltotaler kan inte utläsas. **Diagram och tabeller** är fortsatt utan kolvärden tills SLU:s fysikaliska enheter verifierats och en area-riktig integral av fullständiga källraster genomförts.

Automatisk publicering kan misslyckas om repositoryts Actions-permissioner inte tillåter `contents: write`; granska då jobbloggen. Källbildens transparens visar kommunens arbetsgräns, som bör bytas mot verifierad officiell geometri före officiell statistik.

## Rasterfärger, baskartor, klickvärden och råvärdestabeller

Efter denna ändring genererar GitHub-flödet `Publish SLU Lulea carbon preview maps` även `docs/data/preview/*_sampled_values.f32.gz` och `docs/data/preview/preview_statistics.json`.

- **Färg:** låg = röd, hög = svart med klippning vid varje rasters 2:a/98:e percentil. **NoData inom kommunpolygonen = grått**; utanför kommunpolygonen = transparent. En rasterfärg säger inte ton kol.
- **Bakgrund:** OpenStreetMap standard eller **Esri World Imagery** (satellit-/flygbild med varierande fotodatum) med källattribuering; SLU:s raster är separat från baskartan.
- **Klick i kartan:** visas med koordinat i EPSG:4326, rad/kolumn och närmaste samplade SLU-råvärde från samma fullständigt reprojicerade **EPSG:3857-förhandsgrid** som visningsbilden. Pixeldata lagras som komprimerade float32-värden och läses vid första klicket i vald källa. Detta är **inte** ett exakt original-10m-pixelvärde, utan närmaste källvärde samplat till förhandsgridets grövre upplösning. NoData är inte noll.
- **Tabellsidan:** för källorna Stock_SOC och Stock_All publiceras antal giltiga förhandsgridpixlar, antal NoData, minimum, median, medelvärde, maximum och histogram av **råvärden med okänd fysisk enhet**. Inga koltotalsiffror, CO₂-ton eller arealintegraler visas från dessa råvärden.
- Råvärdenas fysiska enhet och arbetskommungränsens administrativa giltighet är fortfarande **inte verifierade**. SLU:s kolmodell är regionalt skattad; skarpa kommunenheter kräver källdokumentation och ny maskad ursprungsupplöst arealintegral i EPSG:3006.

**Publicering:** Efter merge måste det manuella flödet `Publish SLU Lulea carbon preview maps` köras igen. En vanlig GitHub Pages-deploy av enbart JavaScript producerar inte de nya `.gz`-filerna eller statistikfilen.

## Tydliga SLU-kategorier och enhetsväxling

SLU:s Kolkartor skiljer på `Stock_SOC` (kolförråd i markkol), `Stock_DOM` (kolförråd i dött organiskt material), `Stock_All` (totalt kolförråd i mark inklusive SOC och DOM), samt separata `Change_SOC`, `Change_DOM`, `Change_All` för förändring/kolsänka. De sistnämnda och Stock_DOM är **ännu inte importerade** och visas därför endast som inaktiva, förklarande alternativ. Stock_All får inte summeras med Stock_SOC.

Tabellsidan har en **summa samplade rasterråvärden** per lager. Summan är matematisk och baserad på pixlar i en nedskalad EPSG:3857-förhandsbild – **inte ton C, ton CO₂ eller en arealriktig stock**. Därutöver finns en separat preliminär totalrad i den verifierade kolmassatabellen som kräver båda icke överlappande poolerna trädbiomassa och Stock_All; annars skrivs **Data saknas**.

Växeln **Kol (ton C) / Koldioxidmassa (ton CO₂)** gäller bara *verifierade* massvärden och använder stökiometriska faktorn 44/12. Råvärdesstatistiken omräknas inte eftersom dess enhet ännu saknar källverifiering. Motsvarande CO₂-massa är inte observerade CO₂-utsläpp eller årlig inlagring.

Efter merge krävs en ny manuell körning av `Publish SLU Lulea carbon preview maps` för att publicera nya råvärdessummor i `preview_statistics.json`.

## Biomasstäckning – prioriterat lager

**Faktisk källfil:** [SLU Skogliga grunddata, SGD2_BIO.tif](https://gis.slu.se/data/slu_skogliga_grunddata/SGD2/data/SGD2_BIO.tif). Enligt Skogsstyrelsens produktbeskrivning avser biomassa **stamved, grenar och toppar**, normalt i ton torrsubstans/ha; **rötter och stubbar ingår inte**. Skogsprodukten modelleras utifrån laserskanning och fältdata och har begränsad geografisk täckning. Den tidigare inventerade filen `Biomass_leaf.tif` är **inte** en validerad total biomassa för detta syfte.

Efter att denna PR sammanslagits kan `Publish SLU Lulea carbon preview maps` skapa ett tredje, faktiskt **kommunmaskat** förhandsraster, `biomass_preview.png`, med klickbara råvärden `biomass_sampled_values.f32.gz` och rådatastatistik i `preview_statistics.json`. `preview_layers.json` dokumenterar även CRS, källupplösning, enhetstagg och bandskala från GeoTIFF; körningen stoppar vid ogiltigt CRS eller uteblivna källvärden.

**Kvalitetsspärr:** inga påståenden om biomassans kolmassor görs från råvärden innan fysisk skala och källår verifierats. Det är ett kartlager för **biomassa** och inte ett direkt lager i ton kol. Rött-svart visar relativa värden inom just detta lager. Grått markerar NoData och inget värde motsvaras inte automatiskt av noll. För att bygga en korrekt total behöver de giltiga originalcellerna maskas och areaintegreras i källans verifierade projektion.

**Övriga lager:** Stock_DOM, Change_SOC, Change_DOM, Change_All och skogsvolym återstår. Ingen av dem ersätts av biomassa eller SOC och de är markerade som ännu inte publicerade. Skogsstyrelsens senare omdrev kan vara ett bättre aktuellt alternativ än SGD2; jämför datum/täckning innan materialet används i en årsanalys.
