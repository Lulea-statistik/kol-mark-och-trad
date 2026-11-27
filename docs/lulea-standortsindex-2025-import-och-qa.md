# Luleå – ståndortsindex för tall och gran inför rekonstruktion av biomassa 2010

**Status 27 november 2026:** Källprodukterna och deras deklarerade CRS har identifierats. **Rastren för Norrbotten har ännu inte laddats ned eller analyserats; inga lokala ståndortsindex eller bonitetsvärden har verifierats.** Skriptet nedan är förberett för åtkomliga lokala filer och har syntetiska QA-test. Originalbiomassa 2010 ersätts inte.

## Identifierade officiella datakällor

- Skogsstyrelsen, [Ståndortsindex tall – Atom-flöde](https://geodpags.skogsstyrelsen.se/geodataport/feeds/atom-visare.html?url=SISTall.xml) (filnamn för Norrbotten: `sks_SISTall25.zip`).
- Skogsstyrelsen, [Ståndortsindex gran – Atom-flöde](https://geodpags.skogsstyrelsen.se/geodataport/feeds/atom-visare.html?url=SISGran.xml) (filnamn för Norrbotten: `sks_SISGran25.zip`).
- [Skogsstyrelsens nedladdningssida](https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/geodatatjanster/ladda-ner-geodata/), under *Skogliga grunddata – Ståndortsindex SIS Gran/Tall*.
- [Produktbeskrivningar](https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/skogsstyrelsens-geodata/), inklusive *Raster Skogliga grunddata Ståndortsindex 2025*.
- [Riksskogstaxeringens fältinstruktion 2024](https://www.slu.se/globalassets/slu.se/om-slu/organisation/institutioner/skoglig-resurshushallning/riksskogstaxeringen/dokument/faltinstruktioner/ris_fin_24.pdf), tabell 5.1, visar att SI/H100 och bonitet inte har samma enhet och att omräkning beror på trädslag och markförhållanden.

**Källmetadata från Skogsstyrelsens Atom-flöden:** EPSG:3006, länsvisa raster, uppdaterat 14 februari 2025. Källsidan anger **användarregistrering och särskilda avtalsvillkor för vidareförmedling/kommersiell användning**. Bekräfta tillstånd innan filer eller bearbetade raster publiceras i öppen GitHub Pages, även om nedladdning är tekniskt möjlig. En WMS-bild är **inte** ett godtagbart kvantitativt SI-raster.

## Vad som skiljer SI från bonitet

- **Ståndortsindex, SI/H100:** höjd för referensträd vid bestämd referensålder, uttrycks i **meter**. När 2025-produktens filspecifikation kontrollerats måste dess datatyp, skalning, NoData och SI-mått bekräftas; anta inte att pixelvärdena är meter utan kontroll.
- **Bonitet:** långsiktig potentiell virkesproduktion i **m³sk/ha/år**, inte observerad nettoförändring i levande biomassa. Omräkning från SI till bonitet kräver korrekt trädslag och regionala/vegetationsbetingade funktioner. Landskapets bördighet kan vara någorlunda bestående över 2010–2018, men en **modell beräknad 2025** kan innehålla senare skogsstruktur som inte får tolkas som en direkt mätning av historisk bonitet.
- **Biomassa:** ton torrsubstans per hektar är ännu en tredje mätstorhet. Tillväxtfunktioner måste även hantera ålder, trädslag, nettotillväxt, avgång och eventuella uttag.

## Reproducerbar bearbetning när länsfilerna finns

1. Läs villkoren och ladda ned länsarkiven för Norrbotten. Extrahera **originalraster för SIS Tall och SIS Gran** lokalt. Lägg dem inte i ett publikt repository.
2. Verifiera med `gdalinfo` eller rasterio att de faktiska rasterfilerna har dokumenterat CRS, rasterupplösning, NoData, pixelvärdesenhet och eventuell skalfaktor. Kontrollera även årgång och trädslag.
3. Skapa en **Luleå-klippt referensgrid i EPSG:3006, exakt 25 × 25 m**, enligt projektets ordinarie rastermask och gräns. Skapa därutöver en **binär 1/0 skogsmask**; råa NMD2018-klasskoder kan inte användas som 1/0-mask utan separat klassning. Kontrollera källa-CRS för mask och 2010-års åldersraster. Åldersraster 2010 från SLU har original-CRS EPSG:3021 och ska **reprojiceras fullt ut** till analysgrid via närmaste granne.
4. Kör `scripts/prepare_lulea_site_index.py`. Det använder rasterio `WarpedVRT` för full pixelbaserad omprojektion/omsampling till målgrid, bilinjär interpolation av kontinuerligt SI och närmaste granne för mask och ålder. Det använder inte transformerade bounding boxes som rasterersättning.
5. Granska antal giltiga skogsceller samt medelvärde, median och 10:e/90:e percentil för tall och gran, totalt och för respektive åldersgrupp enligt 2010. Alla utfall är **H100 i meter, inte bonitet**. Geografiskt stöd i analyserade raster måste bekräftas med Luleåkommunens faktiska gräns.
6. Om skillnader i skogsmarksklass, datatäckning och trädslag gör lokal omräkning osäker ska dessa redovisas som osäkerheter. Vid framtida biomasstillväxtmodell ska SI konverteras med dokumenterad **regions- och ståndortsberoende** funktion, inte med konstant multiplikator.

### Körning med lokala raster (schematiskt exempel, inga påhittade data)

```bash
python scripts/prepare_lulea_site_index.py \
  --pine /lokal/sks_SISTall25.tif \
  --spruce /lokal/sks_SISGran25.tif \
  --grid /lokal/lulea_25m_grid_epsg3006.tif \
  --forest-mask /lokal/lulea_skog_binart_epsg3006.tif \
  --age /lokal/age_2010_source_epsg3021.tif \
  --si-scale 1 \
  --output metadata/lulea_site_index_qa.json
```

Sökvägarna ovan är **platshållare**, inte verifierade filnamn i det extraherade länsarkivet. Parametern `--si-scale 1` får användas först när metadatan visar att pixelvärdet är H100 i meter. Skriptets `--min-si 5 --max-si 45` är **kvalitetsgränser för att hitta orimliga pixelvärden**, inte källans publicerade värdeintervall eller automatisk korrigering.

## Vad som krävs för ersättningsmodell 2010

Den första egna SI-statistiken ska **inte** utlösa någon justering av 2010. När faktiska data finns:

- Verifiera hur SI Tall/Gran varierar geografiskt i Luleå och mellan åldersklasser; identifiera hav, hyggen, saknade områden och vilka maskandelar som matchar 2010/2015/2018.
- Skapa en validerad omräkning **SI → bonitet** för rätt trädslag, ståndortstyp och geografisk zon.
- Välj dokumenterade ålders- och trädslagsberoende tillväxt- och avgångsfunktioner; kontrollera att dessa arbetar med rätt biomassaandel (ovan jord/helträd).
- Rekonstruera 2010 var för sig utifrån 2015 och 2018 på samma celler och dokumentera hur nära de oberoende rekonstruktionerna hamnar.
- Visa skillnader mot ursprungliga 2010 och fältreferenser, osäkerhetsintervall och rumsligt valideringsurval. Om resultaten är robusta kan ett **separat alternativraster** få bli förvalt analyslager, medan originalrastret förblir tillgängligt och alla antaganden redovisas.

**Viktig begränsning:** I detta steg har ingen källa för faktiska SI-värden i Luleå kunnat öppnas som GeoTIFF. Det vore fel att rapportera ett lokalt medelvärde eller kalibrera en åldersmodell redan nu.


## Senaste åtkomstkontroll (27 november 2026; PR #136)

Skogsstyrelsens officiella sidor visar de två Norrbottensarkiven `sks_SISTall25.zip` och `sks_SISGran25.zip` med deklarerat koordinatsystem EPSG:3006. Skogsstyrelsens geodatatjänster anger dock att **användarkonto behövs för nedladdning eller användning av rasterdata i egna system**. Försök att nå Atom-XML direkt från analysmiljön gav inte tillgång till några rasterfiler. Detta är en **åtkomstbegränsning**, inte belägg för att något länsarkiv saknas.

För att undvika att anta enhet eller käll-CRS från filnamn finns nu `scripts/inspect_sis_zip.py`. När båda originalarkiven laddats ned med ett behörigt konto kan filernas **verkliga rastermetadata** kontrolleras lokalt utan uppladdning eller vidareförmedling:

```bash
python scripts/inspect_sis_zip.py \
  --pine-zip /lokal/sks_SISTall25.zip \
  --spruce-zip /lokal/sks_SISGran25.zip \
  --output metadata/standortsindex_archives_qa.json
```

Skriptet redovisar rasterformat, faktiskt CRS/EPSG, upplösning, NoData, GDAL-skala/offset och rasterutbredning; felaktigt CRS avvisas. Inga fysiska pixelvärden, lokala medelindex eller bonitet beräknas. En syntetisk CI-kontroll verifierar metadatainspektion och osäkra ZIP-sökvägar. **Lägg inte originalarkiven i ett publikt GitHub-repo** innan rättigheterna för vidareförmedling är klarlagda.

När båda filerna finns tillgängliga kan den befintliga rutinen `scripts/prepare_lulea_site_index.py` köras med tillåten lokal åtkomst, Luleå-klippt referensraster och binär NMD-skogsmask. Ett 2025 års ståndortsindex är ett modellunderlag, inte ett lokalt fältmått på bonitet kring 2010. Den biologiska tillväxtmodellen och eventuell substitutserie för 2010 är därför fortfarande **inte validerade**.
