# Metodgranskning av arkiverade biomassaraster: Luleå

Senast granskad: 2026-11-23. **Detta är en datakvalitets- och jämförbarhetsnotering, inte ett verifierat resultat om biomassa eller kolförråd.**

## Arkiverade källor

Release: https://github.com/Lulea-statistik/kol-mark-och-trad/releases/tag/biomass-source-clips-lulea-v1

| Skikt | Produkt | Lokalt utdrag | Förväntat käll-CRS | Pixelstorlek |
| --- | --- | --- | --- | --- |
| 2010 | SLU Skogskarta, `BIOMASS_XX_P_10.tif` | `lulea_biomass_2010_source_crs_clip.tif` | EPSG:3021 (RT90 2,5 gon V) | 25 m |
| 2015 | SLU Skogskarta, `Biomass_leaf.tif` | `lulea_biomass_2015_source_crs_clip.tif` | EPSG:3006 | 12,5 m |
| 2018 | Skogliga grunddata omdrev 2, `SGD2_BIO.tif` | `lulea_biomass_2018_source_crs_clip.tif` | EPSG:3006 | 10 m |

Varje GeoTIFF är ett avgränsat, maskat utdrag i **ursprungligt CRS** med bevarade källvärden, **inte** en komplett originalfil. Metadata och SHA-256 följer med. Jämförelseflödet läser enbart dessa releasefiler; inga fjärranrop till SLU ingår i analysen.

## Spårbarhet och teknisk kontroll

`scripts/verify_biomass_release.py` validerar för varje år:
1. Alla tre releasefiler finns och är icke-tomma.
2. SHA-256 över faktisk TIFF och proveniens stämmer med `SHA256SUMS.txt` och metadata.
3. Proveniensens registrerade fjärrkäll-URL motsvarar projektets källregister.
4. Projektgränsens SHA-256 är oförändrad sedan utdragen skapades.
5. TIFF:ens band, CRS, rasterupplösning, cellformat, NoData, dimensionsstorlek och antal giltiga celler stämmer.
6. Rastervärden som inte är NoData är finita och icke-negativa; råmedel, råmin/max, andel noll och antal positiva celler dokumenteras.

**Återstående begränsning:** Det finns ingen SHA-256 av **rikstäckande SLU-original**; en faktisk likhet mellan utdragets giltiga cellvärden och en separat, ny originalhämtning kan därför inte verifieras genom dessa arkivfiler ensamma.

## Geografisk jämförelse

- Projektets arbetsgräns läses som GeoJSON i **EPSG:4326** (kontrollerad mot befintlig konvention; inte verifierad officiell kommunpolygon).
- Maskning av källutsnitten skedde i respektive käll-CRS. Vid beräkning reprojiceras hela rastergridet genom Rasterio WarpedVRT till ett **gemensamt grid i EPSG:3006**, upplösning 25 m.
- Råa täthetsvärden omräknas till 25 m med `Resampling.average`; därefter multipliceras med cellarean **0,0625 ha**. Råa pixeltotaler från olika cellstorlekar summeras **inte**.
- Den viktigaste jämförelsen avser **endast samma giltiga celler för alla tre år**. Detta behövs bland annat eftersom 2015 års källdata saknar täckning i delar av norra Luleå.
- Separata totalsummor för respektive årgångs egen täckning är **inte** jämförbara som en tidsserie.
- Där giltig pixel är noll behandlas den som **0**, inte som saknad; en nolla bevisar dock varken avsaknad av skog eller att skog saknats i alla perioder.

## Biomassadefinition, enhet och källa

- [Skogsstyrelsen: Raster SLU Skogskarta – produktbeskrivning](https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/raster-slu-skogskarta---produktbeskrivning.pdf) beskriver biomassa som ton torrsubstans per hektar av stamved inklusive grenar och toppar, utan stubbar och rötter.
- [SLU: Utvärdering av SLU Skogskarta 2015](https://gis.slu.se/data/slu_forest_map/2015/docs/EvaluateSLUSkogskarta.pdf) förknippar filen `Biomass_leaf` med total biomassa **ovan jord**, inte enbart lövbiomassa. Detta måste särskilt beaktas vid tolkning av det missvisande filnamnet.
- [Skogsstyrelsen: Skogliga grunddata](https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/skogliga-grunddata/) anger biomassa i ton torrsubstans/ha men påpekar att rastervärdena är **modellskattningar** som beskriver förhållandena kring laserskanningstillfället, inte nödvändigtvis exakt produkt-/publiceringsår.
- Produkten för 2018 måste identifieras med sin specifika omdrev-/skanningstid i Luleå. Blandade skanningsår ska inte behandlas som en enda faktisk observationsdag.

**Metodreservation:** Att produktbeskrivningar anger ton TS/ha innebär inte att den råa TIFF-bandets tal redan är korrekt kalibrerade för fysisk massberäkning. Bandets skalfaktor/offset, produktgeneration, skattningsmetod och vad som ingår i definitionen ska verifieras mot produktspecifik metadata. Därför märks beräknade integraler fortfarande `raw_density_times_hectares_UNVERIFIED_units`. Ingen omräkning till ton kol eller CO₂ görs.

## Analytiska kvalitetskontroller

Resultatet innehåller:
- medelråvärde på gemensam yta och egen giltig yta;
- giltig areal per år och gemensam giltig areal;
- andel noll- respektive positiva värden på gemensam yta;
- parvis Pearson-korrelation på gemensamma celler och andel celler där det äldre rastervärdet är högre.

**Varning för ekologisk slutsats:** Korrelation och råa skillnader mellan 2010, 2015 och 2018 skiljer inte mellan skoglig förändring, förändrat modellunderlag, skiftande satellit-/laserdata, skogsmarksavgränsning eller historiskt avverkad skog. Ingen retrospektiv korrigering av 2010 års höga värden görs automatiskt.

## Fortsatt granskning efter första körningen

1. Läs `metadata/biomass_release_validation.json`; säkerställ att alla kontroller passerar.
2. Läs `metadata/biomass_native_area_comparison.json`; granska gemensam yta och råmedelvärden, jämförbar geografisk täckning och alla nollandelar.
3. Om 2010 fortsatt avviker: stratifiera efter verifierad skog/icke-skog, trädslag, beståndsålder, avverkningsindikatorer och delområden; låt testet särskilja systematiskt nivåskifte från lokala uteliggare. Först därefter prövas korrektion eller regressionsmodell.
4. Ingen uppdatering av publicerad biomassatrend eller kolförråd görs förrän analysens metodreservationer hanterats och resultaten granskats.

Den här rapporten beskriver **en planerad och körbar kontroll**, inte att jämförelsen redan har genomförts.
