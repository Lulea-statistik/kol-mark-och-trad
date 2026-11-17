# Kvalitetskontroll av biomassa mot NMD2018

**Status 2026-11-17: kontrollkod tillagd, ännu inte körd mot NMD-data.** Uppdatera inte biomassarastrens värden utan beslutad maskningsregel.

## Datakällor och tid
- Naturvårdsverket, [NMD2018 – basskikt och nedladdningar](https://www.naturvardsverket.se/verktyg-och-tjanster/kartor-och-karttjanster/nationella-marktackedata/ladda-ner-nationella-marktackedata/). Raster 10 m, EPSG:3006 enligt produktbeskrivningen; verifiera själva GeoTIFF-filens CRS.
- För 2018 SGD2 används NMD2018 som tidsmässigt mest närliggande marktäckesreferens.
- För 2010 och 2015 är NMD2018 **inte samtidiga observationer**. En konflikt kan därför bero på faktisk markomvandling mellan årgångarna.
- Projektets `docs/data/lulea_boundary.geojson` är arbetsgeometri; ersätt före officiella kommuntotaler.

## Kategorier att kontrollera
- Vatten/hav: positiv biomassa indikativt fel, men gränsceller kräver visuell kontroll.
- Byggnader och väg-/järnvägsytor: sannolik konflikt för positiv biomassa på den **faktiska hårdgjorda ytan**.
- Annan anlagd mark och tätort: **manuell granskning**; parker, trädgårdar, alléer och vägkanter kan innehålla verklig biomassa.
- NMD har både klassificerings- och geolokaliseringsosäkerheter; inga regler bör tillämpas som nollställer alla tätortspixlar.

**Kodlistor får inte antas från versionsobestämda NMD-filer.** Skapa en lokal JSON med klasskoder enligt dokumentationen för just den levererade NMD-versionen, exempel:

```json
{"water": [61, 62], "built": [51], "road": [53], "review": [52]}
```

**Exempel på klasskoder, inte verifierad konfiguration.** Kontrollera kodtabellen i produktbeskrivningen före användning.

## Körning med lokalt originalraster och NMD
```sh
python scripts/audit_biomass_landcover.py --biomass /data/SGD2_BIO.tif --nmd /data/NMD2018bas_ogeneraliserad_v1_1.tif --classes /data/nmd-verified-codes.json
```

Skriptet verifierar att båda källorna har deklarerat projicerat CRS, transformerar kommunarbetsgeometrin till biomassarastrets CRS och lägger NMD-kategorier på **hela biomassarastrets egen pixelgrid** genom nearest-neighbour-reprojektion. Det producerar en korsklassning med antal överlappande celler, antal celler med positiv biomassa och råvärdessumma per vald kategori. **Det skapar inget maskat raster och gör inga tonberäkningar.**

## Före permanent kvalitetsmask
1. Kontrollera originalrastrens NoData, skalning och enheter (se `BIOMASS_COMPARABILITY_AUDIT.md`).
2. Verifiera klasskodlista och NMD-filens metadata; kontrollera missklassningar mot ortofoto/objekthöjd och urval av gränspixlar.
3. Dokumentera vilken mask som avser säkert vatten respektive hårdgjord yta. Redovisa borttagna pixlar/areal och effekt på ton TS när fysisk enhet verifierats.
4. Behåll originalraster och publicera eventuellt separat justerat raster; redovisa osäkerhet även för äldre år.

## Källor
- [Naturvårdsverket: NMD och nedladdningar](https://www.naturvardsverket.se/verktyg-och-tjanster/kartor-och-karttjanster/nationella-marktackedata/ladda-ner-nationella-marktackedata/)
- [NMD2018, ogeneraliserat basskikt, produktbeskrivning](https://www.naturvardsverket.se/contentassets/37e8b38528774982b5840554f02a1f81/produktbeskrivning-nmd-2018-basskikt-v2-2.pdf)
