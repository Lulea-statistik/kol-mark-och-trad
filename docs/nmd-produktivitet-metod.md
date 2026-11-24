# Test: NMDproduktivitet som fast kontrollmask för biomassatrenden

Källa: Skogsstyrelsen, *Skogliga grunddata – teknisk beskrivning*, version 3.1 (2026-05-07), sidan 2 och 5–6.
https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/teknisk-beskrivning/skogliga-grunddata---teknisk-beskrivning.pdf

- Band **10** i den tio-bandiga bilden är **NMDproduktivitet**: 0 = övrig mark, 1 = produktiv skogsmark, 2 = improduktiv skogsmark.
- RasterFunction **Urval** använder **nollbaserade BandIds**, alltså **9** för NMDproduktivitet. GeoTIFF-band i `rasterio.read()` är **ettbaserade**, alltså **10**. Förväxla inte dem.
- Skogsstyrelsen visar att image-tjänsten lägger senaste omdrevet över tidigare år. Lås därför källa/omdrev och dokumentera NMD-version; antag inte att band 10 visar 2010 års marktillstånd.

## Genomförande

Script: `scripts/analyze_nmd_productivity_strata.py`.

Indata (ännu ej inlästa i detta steg):
1. Arkiverade verifierade originalraster-utsnitt för biomassa 2010, 2015 och 2018, **maskade/klippta i respektive original-CRS** (2010 EPSG:3021; 2015/2018 EPSG:3006).
2. Ett verifierat käll-CRS-klippt tio-bandigt SGD/NMD-raster med band 10 och dokumenterad klassningsversion. Kontrollera pixelvärden, NoData och omdrev. **Använd inte TIFF med endast ett band och hävda att band 10 finns.**
3. Ett **befintligt verifierat** 25 m EPSG:3006-maskraster där giltiga celler exakt motsvarar den analysyta som ska jämföras. Den treåriga diagnostiken i PR #70 omfattar 153 525,625 ha; den femåriga huvudserien omfattar 144 800,25 ha. **Välj en population och påstå inte att de är identiska.**

Alla raster reprojiceras som fullständiga rastergrid till analysgrid EPSG:3006; biomassavärden via medel, den kategoriska NMD-masken med **närmaste granne**. Beräkna endast på celler med giltig biomassainformation för alla tre år samt giltig NMD-klass. Redovisa dessutom antal celler med NMD-NoData eller klass utanför 0–2. Ingen uppskattning utanför täckning.

Exempel på körning med **platshållare, inte verkliga resultat**:

```sh
python scripts/analyze_nmd_productivity_strata.py \
  --biomass-2010 /path/2010_source_clip.tif \
  --biomass-2015 /path/2015_source_clip.tif \
  --biomass-2018 /path/2018_source_clip.tif \
  --nmd /path/verified_10band_sgd_source_clip.tif \
  --nmd-year "VERIFIED_NMD_VERSION" \
  --grid-reference /path/verified_three_year_25m_mask_epsg3006.tif \
  --output /path/nmd_productivity_diagnostics.json
```

Utdata: cellantal, hektar, andelar och biomassa-medelråvärden per markklass och år; bidrag till 2010–2015 års summerade skillnad. **Den sista andelen mäter endast deskriptivt bidrag**, inte förklarad kausal variation. Skilj 0 från NoData. Negativa eller icke-finit värden undantas.

## Tolkning

Om även klass 1 (produktiv skogsmark) har högre råvärde 2010 än 2015 visar det att skillnaden **inte kan förklaras enbart av att övrig/improduktiv mark ingår**. Det utesluter inte skilda biomassakomponenter, skötsel, avverkning eller metodskillnader.

**Publiceringsspärr:** inga påstådda NMD-resultat innan riktiga indata har lästs och analyserats. Ändra inte historiska biomassa-värden eller webbsidans siffror i denna PR.

## Vad PR #74 faktiskt gjorde

PR #74 förtydligade endast tabelltext och kolumnrubriker i `docs/biomass-trend.html`. Volymklasserna är **fastställda utifrån 2010 års volym**, och medelbiomassan för 2010/2015/2018 jämförs på **samma celler**; klassernas areal ändras inte mellan kolumnerna. Högvolymklassen (2010 års totalvolym >=200) omfattar 19 768,25 ha och har medelråvärden 156,52 / 98,48 / 98,48. Ingen ny rasterklassning eller datajustering gjordes i PR #74.
