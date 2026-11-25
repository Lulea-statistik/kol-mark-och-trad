# Kör historisk SMD2000-kontroll privat: 2010-mask jämförd med 2018

## Status och faktiskt verifierat underlag

Den tidigare mottagna primära SMD2000-leveransen **`50000148_110002_2012-01-16.zip`** finns tillgänglig som privat analysunderlag och har här granskats genom att läsa ZIP/Shapegeometrin utan återpublicering. SHA256 stämmer exakt med källinventeringen: `d85f88e4dcf97a9758c31cbd90ed2681d5d0b5ba62f32d773d59111225fb92f2`. Inuti finns **`data/mdv2580.shp` med 44 908 polygoner**, faktiskt angivet CRS i `.prj` **EPSG:3006**, och **49 förekommande GRIDCODE-koder**. Geometrin omfattar omkring Luleå även vatten och ytterområden; den representerar **SMD2000** och inte år 2010.

Vid lokal inventering av klasskoder återfanns **31 612 SMD-skogspolygoner**, **5 081 ungskogspolygoner (55)**, **2 629 hyggen (54)** och **466 vattenpolygoner**; detta är **polygonantal, inte area eller rastercellantal**. Klasskoder och grundförutsättningar stämmer med `docs/smd2000-historiskt-marktacke-biommassa-metod.md`.

**Viktigt:** Inga numeriska resultat för jämförelsen av hela SMD2000-masken med biomassa 2010/2015/2018 har ännu räknats fram. De öppna källrastren i GitHub Releases är inte tillgängliga från den här isolerade analysmiljön, varför det inte är seriöst att ersätta överläggningen med uppskattade procenttal. Äldre resultat om 579 särskilt utvalda vattenpixlar är en separat begränsad undersökning, **inte** resultatet för hela kommunens historiska skogsreferens.

## Kör hela analysen lokalt utan licensrisk

Ny `scripts/run_private_smd2000_reverse_comparison.py` gör de återstående momenten på en dator med internet och GitHub CLI (`gh`). Den:

1. Verifierar **SHA256 på privat originalarkiv** innan dess innehåll används.
2. Extraherar endast de verifierade filerna `mdv2580.shp/.dbf/.shx/.prj/.cpg` till tillfällig **lokal** katalog.
3. Hämtar **öppna och verifierbara biomassaklipp** från GitHub Release `biomass-source-clips-lulea-v1` och 2010-volym från `total-wood-volume-lulea-2000-2010-v1`. Arkiverade biomassafiler och proveniens kontrolleras med befintligt SHA256-verktyg.
4. Hämtar Naturvårdsverkets NMD2018 Norrbotten basraster och verifierar original-CRS EPSG:3006.
5. Kör `scripts/compare_smd2000_reverse_2010_mask_private.py` från PR #106 på fullt omprojicerat **25m EPSG:3006-grid** med tidsserie 2010/2015/2018.
6. Skriver **enbart privat JSON** utanför GitHub-katalogen, utan privata geometrier, koordinater, cellraster eller filuppladdning. Tillfälliga kopior av SMD och öppna raster tas bort efter analysen.

Förbered datorn med Python och dess beroenden:

```bash
python -m pip install -r requirements.txt fiona
gh auth status
```

**Windows PowerShell (exempel)**, kör i projektmappens rot och ändra sökvägarna till den faktiska platsen för din SMD-fil och din privata utmatningsmapp:

```powershell
python scripts/run_private_smd2000_reverse_comparison.py `
  --smd-zip "C:\PrivatGIS\SMD2000\50000148_110002_2012-01-16.zip" `
  --output "C:\PrivatGIS\Resultat\smd2000_reverse_2010_private.json"
```

Observera att `C:\PrivatGIS` är **exempelsökvägar**, inte påståenden om var någon faktiskt har lagt filerna. JSON-utdata behöver hållas privata tills licensvillkoren för SMD-derivat har kontrollerats.

## Analysgrupper och tolkning

- **2010 volym ≥50** – exakt samma proxy som PR #105, förväntas reproducera 1 897 060 celler och −14,98 % innan SMD-filter används.
- **2010 volym ≥50 och SMD2000-skog** – historiskt skogsklassat urval; uppföljning 2010, 2015 och 2018.
- **2010 volym ≥50 och SMD2000-skog/ungskog** – inkluderar fler äldre historiska skogsytor; känslighetskontroll.
- **2010 volym ≥50 utan SMD2000-vatten** – identifierar om extrema vattenvärden drar upp 2010.
- **2010 volym ≥100 och SMD2000-skog** – hårdare proxy för äldre/högre bestånd.
- **SMD2000-skog oavsett volym 2010** – visar vad en oberoende historisk mask ger, inklusive skog utan hög virkesvolym.

Alla ovanstående tilldelas 2018 NMD-skog, temporärt ej skog, vatten eller övrig mark i en **deskriptiv** korsning. Avverkningar kan förklara en del förändring, men avsaknad av 2018 skog bevisar inte avverkning. SMD2000 är dessutom generaliserat, cirka 75 % tematisk träffsäkerhet totalt, så verklig 2010-markklass är fortfarande osäker.

**Kvarstående fysikaliskt hinder:** 2010-rastrets enhet och biomassakomponenter är ännu inte källspecifikt verifierade. Alla numeriska biomassajämförelser måste beskrivas som **råvärden**; inga ton TS, ton C, CO₂ eller kausala procentandelar publiceras förrän den frågan är löst.

## Kontroll och skydd

GitHub Actions på PR #107 gör **enbart kodkontroll med påhittad SMD-zip utan verkliga geometrier**. Den tidigare privata SHP-filen, ursprungliga ZIP-filen och resultatet överförs **inte** till GitHub; licensvillkoren behöver därför inte kringgås för att testa koden. Kör det verkliga historiska materialet endast i privat lokal miljö.
