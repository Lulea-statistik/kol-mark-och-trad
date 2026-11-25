# Nästa kontroll: historisk SMD2000-markklass mot spegelvänd 2010-mask

## Varför denna kontroll behövs

Den verifierade spegelvända jämförelsen i PR #105, där **2010 års modellerade virkesvolym ≥50** används som mask, gav **−14,98 %** i summan av biomassaråvärden 2010–2018 på samma **1 897 060 celler**, 118 566 ha. Med skog enligt NMD2018 var förändringen endast **−0,29 %** på **1 705 502 celler**, 106 594 ha. Dessa är olika geografiska urval, inte samma skogsmask.

Flera 2010-volymceller ligger i NMD2018-vatten, och 2010-masken är inte observerad skog. Innan vi försöker dra slutsatser om verklig skogsförlust ska vi jämföra med en **oberoende äldre marktäckeskälla**.

## Verifierade tillgängliga historiska SMD-underlag

De lokala arkiven är redan inventerade i `docs/smd2000-historiskt-marktacke-biommassa-metod.md`. **Primär:** `50000148_110002_2012-01-16.zip`, `data/mdv2580.shp`, verklig `.prj` **EPSG:3006**, 44 908 polygoner, SHA256 `d85f88e4dcf97a9758c31cbd90ed2681d5d0b5ba62f32d773d59111225fb92f2`. Andra två leveranser använder sannolikt EPSG:3017 men saknar `.prj`; använd inte dessa utan oberoende CRS-verifiering. Alla avser SMD2000 (i huvudsak ca år 2000) – nedladdningarna från 2012 är **inte observationsår**.

Produktbeskrivningen anger generalisering till minsta ytenheter mellan **1 och 25 ha** och övergripande tematisk noggrannhet ca **75 %**, beroende på klass. SMD2000 ensamt kan inte fastställa vad som var skog i varje **25 m-cell 2010**.

SMD-klasser i tidigare verifierad kod:
- Historisk **skog**: 40, 41, 43–49.
- **Ungskog** 55 – särredovisas och erbjuds som utvidgad proxy; **hygge** 54 är separat kategori.
- **Vatten**: 80–86.
- Övrig mark, eller helt oklassade celler, särredovisas.

## Ny reproducerbar känslighetsanalys

`scripts/compare_smd2000_reverse_2010_mask_private.py` tar samma kommungräns och samma 2010/2015/2018-raster som PR #105. De ursprungliga datagridden verifieras **EPSG:3021** (2010 biomassa + volym, 25m) och **EPSG:3006** (2015 biomassa 12,5m, 2018 biomassa/NMD 10m), och rastergridden reprojiceras i sin helhet till **25m EPSG:3006** innan join och mask.

Fasta 2010-definierade urval:
1. **Kontroll:** modellerad 2010-volym ≥50, utan SMD-filter, precis som PR #105.
2. Volym ≥50 **och historisk SMD2000-skog**.
3. Volym ≥50 **och SMD2000 skog eller ungskog**.
4. Volym ≥50 och SMD2000-klass **inte vatten och inte oklassad**.
5. Volym ≥100 och SMD2000-skog (ytterligare urvalskänslighet).
6. All SMD2000-skog, utan villkor om 2010-modellerad volym.

I varje urval summeras biomassa 2010, 2015 och 2018 på **samma celler**. Dessutom delas varje urval upp i NMD2018 skog, temporärt ej skog, vatten och annan mark. Kontroller kräver exakt **2 456 410** gemensamma giltiga biomassaceller, fullständig partition utan dubbelräkning, samt att hela gruppens tre års råsummor bevaras.

**Särskilt viktigt:** Om volym≥50 avlägsnas från SMD2000-vatten kan förändringen i råsumman minska. Men det är inte bevis för att alla bortfiltrerade celler var vatten 2010; SMD2000 och NMD2018 är äldre respektive senare klassning. Testa helst både historisk skog och skog+ungskog och analysera osäkerhet i kartering och beståndsförändring.

## Praktisk lokal körning (licensierade data)

Ladda inte upp någon SMD-SHP, DBF, ZIP eller återpubliceringsbar derivatraster till publika GitHub. Analysen är därför avsedd att köras **lokalt** med den redan identifierade privata ZIP-filen:

```bash
python scripts/compare_smd2000_reverse_2010_mask_private.py \
  --smd-shp "/privat/SMD2000/data/mdv2580.shp" \
  --smd-epsg 3006 \
  --biomass-2010 release-biomass/lulea_biomass_2010_source_crs_clip.tif \
  --biomass-2015 release-biomass/lulea_biomass_2015_source_crs_clip.tif \
  --biomass-2018 release-biomass/lulea_biomass_2018_source_crs_clip.tif \
  --volume-2010 release-volume/lulea_total_volume_2010_source_crs_clip.tif \
  --nmd nmd-input/NMD2018bas_BD.tif \
  --output "/privat/resultat/smd2000_reverse_2010_private.json"
```

Outputen måste ligga **utanför** det publika repositoriet. Den innehåller endast statistiska summeringar, klassfrekvenser och metodmetadata, aldrig koordinater eller geometrier, men är fortfarande märkt **privat** i väntan på licensgranskning. Inga privata filer läggs i GitHub Actions. CI testar endast kod, syntetiska små exempel och säkerhetsspärrar.

### Vad som är klart och vad som återstår

**Klart:** källinventering, 2010-referens, reproducerbar privat klassificerings- och jämförelsekod, formella avstämningskontroller. **Inte klart:** verklig SMD2000-överläggning mot originalpolygonerna. Den förutsätter tillgång till just det lokala SMD-arkivet i ett privat körningsutrymme. Inga hypotetiska resultat ska ersätta denna mätning.

Även efter genomförd överläggning gäller enhetsspärren från PR #104: 2010 års enhet och biomassa­komponenter är inte slutligt verifierade; summerade värden får inte presenteras som ton biomassa eller kol.
