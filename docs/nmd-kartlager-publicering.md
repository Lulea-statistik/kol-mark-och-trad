# NMDproduktivitet i kartan - publicering och status

**Status: tekniskt stöd är förberett; verkligt NMD-raster har inte publicerats.**

Skogsstyrelsen: https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/teknisk-beskrivning/skogliga-grunddata---teknisk-beskrivning.pdf

**Lagret** visar kategorierna 0 (övrig mark), 1 (produktiv skogsmark) och 2 (improduktiv skogsmark) som beige/grön/blå. NoData visas grått inom Luleås arbetsgeometri, utanför gränsen transparent. Kategorier är inte numeriska storheter: det finns ingen medelklass, kolmassa eller bonitet att summera.

## Var finns datat?

Publicerade **kartderivat**, inte Sveriges original-GeoTIFF, ska lagras på GitHub Pages:

- `docs/data/preview/nmd_productivitet_preview.png` – färgad rasterkarta.
- `docs/data/preview/nmd_productivitet_sampled_values.f32.gz` – samplade klassvärden för kartklick.
- Posten `nmd_productivity` i `docs/data/preview/preview_layers.json`, inklusive ursprunglig källa, version och SHA-256.

Käll-GeoTIFF lagras separat som release-asset i projektet om den kan hämtas lagenligt och faktiskt verifieras. GitHub Pages visar **inte** automatiskt en TIFF bara för att en arbetsflödeskod finns.

## Publicering när rätt fil finns

1. Identifiera och hämta en verklig NMDproduktivitet GeoTIFF från Skogsstyrelsen med känt datum/version, CRS, NoData och rätt utbredning. Använd ett enbandsraster med band 1 om NMD extraherats eller hela tiobandsprodukten med band 10. ArcGIS `BandIds=9` är nollbaserat och får **inte** användas som `rasterio.read(9)` för band 10.
2. Lägg originalutdraget från Luleå i en GitHub-release som asset; verifiera att innehållet inte innehåller inloggningsuppgifter. För stora original: behåll endast käll-CRS-klippt Luleåutdrag, eller använd legitim åtkomst i Actions utan att offentliggöra autentisering. Underlag ska klippas/maskas i käll-CRS innan eventuell originalanalys.
3. Kör manuellt `Publish verified NMD productivity map preview` med release-tag, exakt asset-filnamn, bandnummer, verifierad NMD-version och offentlig HTTPS-länk till källa/dokumentation.
4. Arbetsflödet kontrollerar rasterfilens CRS, NoData, band, kategoriuppsättning och celltäckning. Det reprojicerar **hela rastergridet** till det redan publicerade kartgridet i EPSG:3857 med närmaste granne och maskar mot arbetsgränsen. Bara efter godkända kontroller läggs PNG, gzip-värden och manifest i GitHub.
5. På kartan aktiveras NMD-alternativet automatiskt när manifestet har ett faktiskt publicerat NMD-lager.

**Viktigt:** Publicerat kartgrid i EPSG:3857 är en visualisering, inte rätt underlag för hektarberäkning. För PR #75:s klassvisa biomassaavstämning behövs en separat, verifierad 25 m EPSG:3006-analys med samma geografiska cellpopulation och korrekt markmask. NMD-klassningen är en **fast referensversion**, inte en observerad klassförändring 2010–2018.

## Åtkomstbegränsningar

Skogsstyrelsen anger att REST/WMS-raster kan kräva användarkonto. Den här implementationen kringgår ingen autentisering och installerar inte lösenord i öppet repo. Om originalfil ännu inte är åtkomlig förblir kartvalet inaktiverat och ingen påhittad NMD-karta publiceras.

**Test:** `.github/workflows/test-nmd-map-layer.yml` skapar ett uttryckligt syntetiskt test-GeoTIFF i Actions och kontrollerar publiceringskoden; dess testdata ska aldrig committas till Pages.
