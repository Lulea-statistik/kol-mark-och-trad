# Biomassajämförbarhet 2010, 2015, 2018 – käll- och enhetsgranskning

Granskat 2026-11-17. Denna rapport skiljer **dokumenterad produktenhet** från **verifierad numerisk rasterskala** och från **metodjämförbarhet**. Ingen ogrundad omräkning eller biomassatotal görs.

| Årgång | Publicerad fil | Dokumenterad storhet/enhet | Ursprunglig pixelstorlek enligt publicerad previewmetadata | Begränsning |
|---|---|---|---|---|
| 2010 | `BIOMASS_XX_P_10.tif` | SLU Skogskarta: biomassa, ton torrsubstans/ha (produktfamilj) | 25 × 25 m; EPSG:3021 | Behöver direkt fil-/bandverifiering av definition, skala och NoData för exakt arkivfil |
| 2015 | `Biomass_leaf.tif` | SLU: **total biomassa ovan jord**, ton TS/ha (utvärderingen `BiomassAbo`); produktbeskrivningen anger stamved, grenar och toppar, exklusive rötter och stubbar | 12,5 × 12,5 m; EPSG:3006 | Produktmodell baserad på stereomatchade flygbilder och Sentinel-2; kan avvika systematiskt från 2018 |
| 2018 | `SGD2_BIO.tif` | Skogliga grunddata: biomassa, ton TS/ha, stamved, grenar och toppar utan stubbar och rötter | 10 × 10 m; EPSG:3006 | Laserskanning 2018 verifierad via 540/540 metadataobjekt i arbetsgränsen; modell baserad på laser + Riksskogstaxeringen |

## Källor

- [SLU Skogskarta – produktsammanställning, årgångar och upplösning](https://www.slu.se/miljoanalys/statistik-och-miljodata/miljodatakatalogen/slu-skogskarta/).
- [SLU Skogskarta 2015 – produktbeskrivning, sida 3](https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/raster-slu-skogskarta---produktbeskrivning.pdf): ton TS/ha och ingående träddelar.
- [SLU:s utvärdering](https://gis.slu.se/data/slu_forest_map/2015/docs/EvaluateSLUSkogskarta.pdf): `Biomass_leaf.tif` används för *Total biomassa (ovan jord)*, `BiomassAbo`.
- [Skogliga grunddata – produktbeskrivning](https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/skogliga-grunddata/skogliga-grunddata-220701---produktbeskrivning.pdf): biomassa i ton TS/ha.
- [Skogsstyrelsens tekniska beskrivning](https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/teknisk-beskrivning/skogliga-grunddata---teknisk-beskrivning.pdf): biomassa i ton TS/ha, rasterfunktioner och laserskanningsdatum.
- [SGD2-skanningsinventering i Luleå](sgd2_lulea_scan_years.json).

## Konkreta kontroller av redan publicerad data

Previewmetadata anger **skalning 1**, **offset 0** och **saknad band-enhetstagg** för biomassarastren. Detta är uppgifter i vår export och styrker **inte ensamt** den verkliga numeriska enheten för var och en av originalfilerna. På samma sätt är `source_year` för 2010 och 2015 källårgångar, inte verifierad fotograferingsdag per rastercell.

Den publicerade 2015-förhandsgridens maximum är **11821**, medan 98:e percentilen anges till **173**. Skillnaden kräver en rimlighetskontroll av extrema pixlar, NoData-övergångar, skalning och eventuella felsignaler före fysisk summering. Årsprodukterna kan också ha olika skogsmask och olika nollregler.

## Krav innan en trend i ton TS redovisas

1. Öppna original-GeoTIFF och läs `crs`, `transform`, `nodata`, bandbeskrivning, enhet, `scale`, `offset` och värdefördelning på ursprungsupplösning. För 2010 ska den exakta arkivfilens semantik kontrolleras separat.
2. Kontrollera de högsta råvärdena och sätt en **dokumenterad** valideringsregel för avvikare; klipp inte extremvärden på egen hand.
3. Använd en verifierad officiell kommungräns och verifiera käll-CRS. Klipp/maska respektive originalraster i dess faktiska käll-CRS, och gör arealintegrering i en lämplig metriskt projicerad CRS, exempelvis EPSG:3006, med rätt arealtäckning och pixelvikt.
4. Redovisa **gemensam täckning** separat från årsspecifik täckning och modellskattad saknad nordlig yta. Särredovisa 0, NoData och antalet skattade celler.
5. Om rastervärden verifieras som **ton TS/ha**, beräkna `ton TS = summa(densitet_i × täckt_areal_i_ha)`. Använd inte summan av nedskalade EPSG:3857-förhandsvärden som ton TS.
6. Kvantifiera skillnader i modellmetod och träddelsdefinition, och kalla inte serien en observerad tillväxttrend förrän de effekterna har bedömts.

**Status:** Produkternas deklarerade enhet och 2015 års totalbiomassadefinition är källbelagda. Exakt arkivfil 2010, den fysiska skalan i varje nedladdad GeoTIFF samt en jämförbar arealriktig total är **inte** slutverifierade.
