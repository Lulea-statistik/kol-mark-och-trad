# Kvalitetskontroll SGD2 2018 mot NMD2018 – körbart flöde

Ny GitHub Actions-workflow: [Audit SGD2 biomass vs NMD2018 Norrbotten](../../actions/workflows/audit-biomass-nmd2018.yml), manuellt på main efter merge.

## Verifierat ingångsunderlag

- NMD2018 **ogeneraliserat basskikt v1.1**, filen `BD_lan_nmd2018bas_ogeneraliserad_v1_1.zip` (~237 MB) från [Naturvårdsverket](https://geodata.naturvardsverket.se/nedladdning/marktacke/NMD2018/bas_lan_ogen/), län BD (Norrbotten).
- Verifierade NMD2018-koder enligt [Naturvårdsverkets produktbeskrivning](https://geodata.naturvardsverket.se/nedladdning/marktacke/NMD2018/NMD_Produktbeskrivning_NMD2018Basskikt.pdf):
  - 61 inlandsvatten, 62 hav.
  - 51 exploaterad mark / byggnad, 53 väg (inklusive vissa andra trafikytor enligt produktdefinition).
  - 52 annan exploaterad mark, **endast granskning**, inte maskning.
- SGD2 `SGD2_BIO.tif` med verifierat skanningsår 2018 för Luleås arbetsgeometri.
- Arbetsgränsen `docs/data/lulea_boundary.geojson` har EPSG:4326, är **inte** verifierad officiell kommungräns.
- Källraster måste i körningens metadata ha faktiskt verifierade EPSG:3006 och 10 m upplösning; annars avbryts kontrollen.

## Metod

GitHub Actions laddar ner länsfilen i stället för Sverigerastret. Länkens faktiska GeoTIFF och CRS verifieras direkt. NMD2018:s **hela rastergrid** transformeras och kategorier överförs med nearest-neighbour till *originalrastret* SGD2:s faktiska 10 m-grid i EPSG:3006. Polygonmask används därefter vid analys. **Inga kart- eller rastervärden publiceras/ändras**.

För varje NMD-klassgrupp redovisas:
- NMD-överlagrade celler med giltigt originalbiomassavärde, inklusive nollor.
- Antal originalceller med positiv biomassa, andel potentiellt motstridiga celler samt råvärdessumma (ej ton torrsubstans).
- Hur många konflikter som är i ett NMD-kärnområde med samma klass i alla åtta närmaste grannceller och hur många som är nära klassgränser.

Resultatet är en **diagnos**. Positiv biomassa över klass 51 (byggnader) eller 53 (vägar) och 61/62 (vatten) bör undersökas, men bara stabila inre klassceller är rimliga första korrigeringskandidater. Även dessa kan innehålla käll- eller klassningsfel. NMD2018 är inte en samtida marktäckeskälla för biomassarastren från 2010 och 2015; kontrollen gäller därför primärt SGD2 2018.

### Efter körningen

Ladda ner artefakten `sgd2-nmd2018-lulea-audit` och granska `nmd2018_biomass_lulea_audit.json`. Ta sedan ställning till en separat validerad mask (och en reproducerbar skillnadsrapport) utan att skriva över källraster. En fysisk totalsumma i ton TS kräver verifierad numerisk produktskala och korrekt arealintegrering.


## Utökad avvikelsekarta och konservativt vattenscenario (PR #27)

Vid ny körning skapar samma arbetsflöde numera också `nmd2018_conflict_overview.png` och `nmd2018_conflict_report.md` som Actions-artefakter. Kartan visar antal positiva biomassapixlar per ursprunglig bearbetningsruta om upp till 512×512 originalceller (cirka 5 km); prickarna representerar aggregerade rutor och **inte** enskilda avvikelsepixlar. Sammanställningen redovisar för varje klass antal giltiga celler, andel med positiv biomassa samt 3×3-kärna kontra klassgränser.

Rapporten gör också ett **icke-destruktivt testscenario**: sammanlagd cellarea och summa ursprungliga råvärden i positiva biomassa-pixlar där NMD klassar samma och alla åtta grannceller som inlandsvatten respektive hav. Detta är **inte en applicerad mask**, och råvärdessummorna är **inte ton TS**. Byggnader, vägar och annan exploaterad mark markeras enbart för granskning; ingen automatisk nollning. Även sammanhängande vattenområden kräver manuell geodata- och ortofotokontroll innan maskningsbeslut.


## Stegvis uppföljning av kvalitetskontroller (PR #29)

Efter varje ny körning skapas ytterligare två artefakter: `nmd2018_quality_steps.md` och `nmd2018_quality_steps.png`. Det är **hypotetiska känslighetsscenarier** på samma samlokaliserade, giltiga originalceller i SGD2 och NMD2018:

1. Nolläge – inga värden borttagna.
2. Separat exkludering av NMD2018-vattenkärnor (klass 61/62, alla åtta grannar med **samma** klass).
3. Separat extremvärdeskontroll med tröskel **råvärde >1000**.
4. Kombinerat vattenkärnor + råvärde >1000, räknar överlapp en gång.
5. Separat och kombinerad känslighetskontroll med råvärde >500.

För varje alternativ jämförs behållna och exkluderade 10 m-celler och cellareal, behållen och exkluderad **råvärdessumma**, procentuell skillnad samt antal kvarvarande positiva värden i sammanhängande NMD-vatten och antal råvärden över tröskeln. Enheterna för råvärdena är ännu inte slutverifierade; dessa värden får inte betecknas ton torrsubstans.

**Viktigt:** Mindre summa eller färre flaggade celler visar inte nödvändigtvis bättre kvalitet – en filterregel tar definitionsmässigt bort de celler den flaggar. En verklig kvalitetsvinst kräver oberoende validering (ortofoto, bättre vatten- och byggnadsgeometrier, rimlighetsprövning mot kända skogstyper, samt eventuell stickprovsvalidering). Trösklarna 500 och 1000 är valda enbart för att analysera känsligheten; de är **inte verifierade felgränser** och ska inte tillämpas som permanenta maskningar utan separat beslut. Alla scenarier kan jämföras både med och utan respektive filter. Inga originalraster eller publicerade biomassavärden ändras.
