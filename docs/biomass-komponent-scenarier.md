# Komponentharmonisering av biomassa 2010, 2015 och 2018 – känslighetsscenario

## Verifierade källor och kvarstående uppgift

- SCB:s äldre genomgång av SLU Skogskarta 2005/2010 beskriver biomassa som **över + under mark**, se https://www.scb.se/contentassets/0020464162f64348bb47b3d1b9a1c9a7/mi1301_2015a01_br_mi71br1701.pdf.
- SLU:s utvärdering av `Biomass_leaf` 2015 benämner den **total biomassa ovan jord**, se https://gis.slu.se/data/slu_forest_map/2015/docs/EvaluateSLUSkogskarta.pdf.
- Skogsstyrelsens produktbeskrivning för laserbaserade skogliga grunddata anger **stamved + grenar + toppar, utan stubbar och rötter**, se https://www.skogsstyrelsen.se/globalassets/om-oss/regeringsuppdrag/uppdatering-av-skogliga-grundata/skogliga-grunddata---produktbeskrivning.pdf.
- **Verifiera separat** för just 2010-filens band `BIOMASS_XX_P_10.tif`: exakt biomassakomponent, bandets **lagringsenhet/skala** (SCB beskriver en äldre skogskartvariabel i kg/ha), eventuellt omräknat värde samt giltig skogsmarksmask. Även 2015/2018 behöver enhet och metod kontrolleras, eftersom rastervärdenas jämförbarhet inte har godkänts.

## Formel (syntetisk hypotetisk rot/stubbkvot)

Definiera `r = B_under / B_ovan`. All biomassa för samma definierade växtdelar ges av `B_total = B_ovan * (1 + r)`. Om det **verifieras** att 2010 är total levande biomassa inklusive rötter/stubbar och 2015/2018 avser ovanjordisk trädbiomassa, blir:

- `B_ovan,2010 = B_rå,2010 / (1 + r)`
- `B_ovan,2015 = B_rå,2015`
- `B_ovan,2018 = B_rå,2018`
- `B_total,2010 = B_rå,2010`
- `B_total,2015 = B_rå,2015 * (1 + r)`
- `B_total,2018 = B_rå,2018 * (1 + r)`

**Värdena för r = 0–0,60 är användardefinierade provantaganden**, inte källbaserade faktorskattningar för Luleå. Råvärdena kommer från en enhetligt EPSG:3006-maskad population om 153 525,625 ha, inte från webbkartans EPSG:3857-raster. Inga originaldata eller tidigare tidsserier ändras.

Obs: Rot/skott-kvoten kan variera med art, ålder, ståndort och vilka rötter som ingår. För verklig omräkning krävs art- och storleksberoende biomassafunktioner och verifierade komponent-/enhetsdefinitioner. Det är inte legitimt att välja r så att 2010 års uteliggare försvinner.

## Exempel – r = 0,25 (syntetiskt antagande)

| År | Observerat råmedel | Medel utan stubbar/rötter | Medel inklusive stubbar/rötter |
|---|---:|---:|---:|
| 2010 | 76,89 | 61,51 | 76,89 |
| 2015 | 64,73 | 64,73 | 80,92 |
| 2018 | 69,33 | 69,33 | 86,66 |

Dessa värden är **råvärdesscenarier utan fastställd gemensam fysisk enhet**. Den inbyggda interaktiva kalkylen på `docs/biomass-trend.html` visar hela analysytan och varje NMD2018-klass. De är **inte** en metodharmoniserad historisk trend.

## Prioriterad fortsatt verifiering

1. Leta fram 2010 års originalbandmetod och enhet (kg/ha eller ton/ha) samt kontrollera arkivets ev. skalning.
2. Kontrollera att 2018 års omdrev 2 verkligen har ovanjordisk biomassadefinition.
3. Om 2010 total inkluderar rötter, använd oberoende biomassafunktioner, gärna efter 2010 års trädslag och volym, för att uppskatta kvoten `r` med intervall och osäkerhet.
4. Gör separat korrektionsserie för varje markklass, med originalserien sida vid sida och enhetskontroll innan publicering av fysiska totaler.
