# SMD2000 som historiskt marktäcke – metod och datalicens

## Verifierat källunderlag (lokalt tillhandahållet 2026-11-25)
Tre arkiv från lokal GIS-server innehåller **GSD-Marktäckedata/Svenska Marktäckedata (SMD), vektordata**:

| Fil | Polygoner | CRS | Status |
|---|---:|---|---|
| `50000148_110002_2012-01-16.zip` | 44 908 | **EPSG:3006**, verifierad `.prj` | Primärt underlag, `data/mdv2580.shp` |
| `50000148_110002_2012-04-17.zip` | 45 095 | **EPSG:3017**, härlett ur `sw99-2145` och koordinater; ingen `.prj` | Alternativ leverans, `data/sw99-2145/Lulea.shp` |
| `lulea.zip` | 45 079 | **EPSG:3017**, härlett ur `2145` och koordinater; ingen `.prj` | Alternativ leverans, `2145/Lulea.shp` |

Alla tre har 49 förekommande `GRIDCODE`-klasser. De skiljer sig i antal polygoner, alltså får de **inte** behandlas som byte-identiska eller antas visa tre olika observationsår. Kontrollera deras spatiala täckning och klassificeringsöverensstämmelse innan någon sammanslagning.

Källornas SHA-256 (ZIP):
- 2012-01-16: `d85f88e4dcf97a9758c31cbd90ed2681d5d0b5ba62f32d773d59111225fb92f2`
- 2012-04-17: `dc32745f2273d8180a2771b9ab354bc1f493da1b6d77fe7cb3d68dc762089098`
- lulea.zip: `057bb69bca2268b3d62c3f158a2bb6ae518b475d8bcf750d878c667d7c44cb7f`

### Översikt av polygonernas areal (källgeometri, ej kommunmaskad 2010-grid)

Area summerad direkt från samtliga SMD-polygoners planarea i respektive källa. **Observera:** Detta är en första inventering av de levererade polygonerna (inklusive havs-/vattenutbredning), inte Luleås administrativa landareal eller ett mått på areal med giltig biomassa.

| SMD-arkiv | Vatten (ha) | Skog (ha) | Övrigt (ha) | Summa polygonarea (ha) |
|---|---:|---:|---:|---:|
| 2012-01-16, EPSG:3006 | 213 383,2 | 127 902,9 | 158 379,9 | 499 666,0 |
| 2012-04-17, angivet lokalt EPSG:3017 | 213 200,3 | 128 063,1 | 158 398,8 | 499 662,3 |
| lulea.zip, angivet lokalt EPSG:3017 | 213 130,0 | 128 240,5 | 158 314,8 | 499 685,2 |

Skillnaderna mellan arkiven är relativt små i aggregerad yta, men skillnader i polygonindelning och strandgeometri kan vara viktiga nära de 22 avvikande 2010-cellerna. **Areor i olika kartprojektioner kan skilja något även vid identiskt innehåll.** Det får inte tolkas som förändring mellan observationsår, eftersom alla leveranser avser SMD2000.

### Referensår och kvalitet
Bifogad `dokument/md_prod.pdf` (Lantmäteriet, 2010-03-26, version 1.2) anger **referensår 2000**, i huvudsak Landsat-satellitdata samt flera kompletterande källor. Originalets pixelunderlag hade 25m grid; dessa uppladdade **vektordata är generaliserade** till minsta ytenheter **1, 2, 5 eller 25 hektar** beroende på klass. Uppgiven sammanlagd tematisk noggrannhet är **cirka 75 %**, men varierar mellan klasser. Det innebär att SMD2000 inte får utges för att vara ett precist facit för enskilda 2010-rasterceller.

Nedladdningsdatumen 2012 är **inte** observationsår.

### Harmonisering
Markklasskoder från leveransens `GRIDCODE` och namn:
- **Vatten:** 80–86, inklusive vattendrag (80), sjöar/dammar (81–82), laguner/estuarier/hav (83–86).
- **Skog:** 40,41,43,44,45,46,47,48,49 – löv-, barr- och blandskog inklusive myr och berg.
- **Övrig mark:** återstående koder inklusive 54 hygge och 55 ungskog, som redovisas separat från skog. Detta är en **analytisk gruppering**, inte en direkt ekvivalens med NMD:s skogsklass.

### Reproducerbar lokal analys av de 22/579 vattenklassade cellerna
`scripts/analyze_smd2000_vs_native_2010.py` använder:
1. SMD:s **privata vektorpolygoner**. Geometrin omprojiceras från verifierat käll-CRS (EPSG:3006 för primärarkivet) till **den faktiska EPSG:3021 25m-gridden hos biomassa 2010**, och rasteriseras genom cellmitt; originalvektorn ändras inte.
2. SLU:s **originalklipp i EPSG:3021** för både biomassa och virkesvolym 2010, lästa utan rasteromprojicering. Kod stoppar körningen om de båda originalgridden inte stämmer exakt.
3. Original-NMD2018 i **EPSG:3006, 10m**. Den binära vattenandelen och giltiga NMD-källtäckningen beräknas genom **full areaomprojicering** till 2010 års ursprungliga 25m-grid. Ingen NMD-klasskod interpoleras numeriskt.
4. Analyser av de **helt vattenklassade 2018-cellerna**, deras 4/8 grannar, SMD2000:s vatten-/skogsklassning för giltiga 2010-celler samt celler som klassas som skog i både SMD2000 och NMD2018.
5. JSON-redovisning av källklass, antal, andel giltiga 2010-celler och biomassa-/volymråvärden. Koordinater i **EPSG:3021 och transformerade EPSG:3006** redovisas för kvarvarande helt vattenklassade celler utan land bland 8 grannar.

**Förväntat antal kritiska celler:** PR #96 gav 22 när ursprungligt 2010-grid används. En verifierad lokal körning ska kunna kontrolleras mot detta; om antalet avviker krävs spårning av SMD-/NMD-källa och rastermask.

### Exempel på lokal körning
Kör från repositoriets rot och ersätt sökvägarna med dina lokala filer:

```bash
python scripts/analyze_smd2000_vs_native_2010.py \
  --smd-shp /lokalt/smd/data/mdv2580.shp \
  --biomass-2010 release-biomass/lulea_biomass_2010_source_crs_clip.tif \
  --volume-2010 release-volume/lulea_total_volume_2010_source_crs_clip.tif \
  --nmd nmd-input/NMD2018bas_BD.tif \
  --output metadata/smd2000_vs_native_2010_private.json
```

Underliggande källraster kan hämtas från projektets befintliga GitHub-release för 2010 och Naturvårdsverkets öppna NMD2018-arkiv, på samma sätt som PR #96:s workflow. Programmet är tänkt för **lokal körning**, inte för GitHub Actions med privat SMD-geometri.

### Tillstånd och offentlig publicering
Produktbeskrivningen anger uttryckligen att **nyttjandet regleras i licensavtal**. SMD-arkiven levererades från lokal GIS-server. Därför:
- Lägg inte original-SHP, DBF, ZIP, detaljerade återpublicerbara geometrier eller derivatraster som kan rekonstruera SMD i **publikt** GitHub-repo.
- Koden kan vara publik. Data och härledda jämförelser sparas lokalt/privat tills licens- och återpubliceringsvillkoren granskats.
- Begränsa eventuellt offentliga slutsatser till aggregerade, icke-rekonstruerbara statistiska resultat efter kontroll av vad licensen medger.

**Tolkning:** Om SMD2000 och NMD2018 båda säger vatten är det evidens för relativt stabil vattenklassning mellan två tidpunkter; det är fortfarande **inte** direkt dokumentation av vatten 2010. Om SMD2000 säger skog och NMD2018 vatten är det inte bevis för avverkning, utan potentiell verklig marktäckeförändring eller klassificeringsskillnad.
