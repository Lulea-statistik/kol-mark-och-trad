# Fast NMD2018-klassning för biomassa 2010–2018

## Analysupplägg

Den produktiva skogsmarken (NMD2018 klass 1) är huvudpopulation. Klasserna 0 (ej skogsmark) och 2 (improduktiv skogsmark) särredovisas, inte exkluderas ur täckningskontrollen.

`scripts/compare_nmd2018_biomass_fixed_classes.py` använder Luleås befintliga arbetsgräns och skapar **samma 25 m EPSG:3006-grid** som `compare_biomass_native_area.py`. Rastren från SLU 2010, 2015, 2018 laddas från verifierade GitHub Release `biomass-source-clips-lulea-v1`, som är klippta i respektive käll-CRS. Naturvårdsverkets NMD2018 v1.1 läses från originaltiff i EPSG:3006 (10m) och samplas med närmaste granne till 25m-grid; biomassa omsamplas med medelvärde. Gränsmask och jämförelse görs i EPSG:3006. **Webbpreview i EPSG:3857 används aldrig som analysindata.**

Redovisa:
- Totala 2010/2015/2018-giltiga celler före NMD och förlorade celler på grund av NMD-NoData/okänd klass.
- Antal celler, hektar och andel inom **samma cellpopulation** för varje klass.
- Biomassans medelråvärden per klass och år, differenser och andel av summerad råvärdesskillnad.
- Andel celler med positivt biomassavärde per klass och år.
- Främst klass 1: kvarstår 2010 års högre råvärde inom produktiv skogsmark?

## Viktiga reservationer

1. NMD2018 är en **fast referens** för 2010, 2015 och 2018; inte dokumentation av att historisk markanvändning saknat förändringar. Skogsproduktivitet kan vara stabil även när biomassa förändras.
2. NMD2018 kan vara delvis beroende av tidigare SLU Skogskarta. Detta är en kontrollklassning, inte helt oberoende validering.
3. Skogskarta 2010 och biomassaprodukterna 2015/2018 kan ha olika biomassa-komponenter, kalibrering och modeller. Differenser mellan **råvärden är inte verifierad biologisk tillväxt eller avverkning**.
4. Arbetets kommunpolygon är inte verifierad officiell administrativ gräns. Visa inga officiella skogsmarksarealer utifrån dessa utan avstämning.
5. NMD2018 klass 0 ”ej skogsmark” omfattar många marktyper och är inte jämförbar med en enhetlig skogstyp.

## Körning

GitHub Actions: `.github/workflows/compare-biomass-nmd2018-classes.yml`, vid PR eller manuellt. Resultatet sparas som körningsartefakt `nmd2018-fixed-classes-biomass-2010-2015-2018`, inklusive SHA256 för nedladdad NMD ZIP och biomassaarkivets validering.

**Status:** analyskoden och arbetsflödet finns i denna PR. Nya resultat ska inte beskrivas som uppmätta förrän GitHub Actions faktiskt slutfört med godkänd status och JSON-resultatet kontrollerats. Om resultatet godkänns kan det därefter publiceras på biomassatrendsidan i separat PR.
