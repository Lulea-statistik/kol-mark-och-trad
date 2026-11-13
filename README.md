# Kolförråd i mark och träd – Luleå kommun

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
