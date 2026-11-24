# Metodprövning av biomassatoppen 2010 — status 2026-11-24

## Redan empiriskt belagt på Luleås gemensamma analysyta

Femårig huvudkurva omfattar **2 316 804** giltiga celler = **144 800,25 ha** och ger:

- 2005 års biomassaråmedel **61,0619**, beräknat som virkesvolym **87,3756** × 2010 års kvot **0,6988437**.
- 2010 års biomassaråmedel **75,6569**, faktiskt från arkiverat kNN-biomassaraster.
- Uppgången 2005–2010 **+23,90 %** är exakt identisk med uppgången i virkesvolym och är inte ett separat uppmätt biomassafynd.

Den tidigare analysen PR #70 visar en betydande skillnad även på identiska celler 2010–2015. Skogsstyrelsens registrerade avverkningar 2011–2015 står för cirka **25,3 % av nettoskillnaden** i en separat analys på **153 525,625 ha**. Den beräknade andelen är en beskrivande nettobidragsandel, ingen kausal attribuering, och inte från exakt samma yta som huvudkurvan.

## Originalkällor: metod- och komponentdefinitioner

1. [SLU, *kNN-Sverige – Aktuella kartdata över skogsmarken, årgång 2005 och 2010*](https://gis.slu.se/data/slu_forest_map/2005/Data/SegmentShape/kNN-2005-2010-info.pdf), sida 1–2:
   - 25×25 m kNN-raster med **biomassa summerat över och under mark**, trädbeståndsålder, total- och trädslagsvis virkesvolym.
   - Riksskogstaxeringens stickprov från fem år fram till scenåret skrivs fram med tillväxtfunktioner. Bilderna är främst SPOT-5, men även SPOT-4 och flera bildår.
   - För **2010** användes MODIS spektralkalibrering bara undantagsvis, till skillnad från **2005**. Dokumentet beskriver att **216 av 256** satellitbilder för 2010 hämtar provytor från aktuell scen eller angränsande scener från samma datum; återstående bilder använde MODIS-kalibrering i huvudsak för kust/fjäll där lokala referensytor inte räckte. Skillnaden kan skapa olika modellbias.
   - KNN-rutorna skattas enbart på kartklassad skogsmark; icke-skog och moln markeras NoData. Arbetsytan i projektet är ännu inte en separat verifierad officiell skogsmarksmask.

2. [SLU, *EvaluateSLUSkogskarta* (2019)](https://gis.slu.se/data/slu_forest_map/2015/docs/EvaluateSLUSkogskarta.pdf), avsnitt **Total biomassa (ovan jord)**: 2015 års **Biomass_leaf** utvärderas som **BiomassAbo**, total biomassa ovan jord. 2015 raster har därför **inte verifierat samma biomassakomponenter som kNN 2010**.
3. [SLU, *SLU Skogskarta*](https://www.slu.se/miljoanalys/statistik-och-miljodata/miljodatakatalogen/slu-skogskarta/): alla de fyra äldre referensåren är skattade rasterprodukter. Källornas observationstid varierar.
4. [SLU pressmeddelande Skogskarta 2005 (2010)](https://www.mynewsdesk.com/se/sveriges_lantbruksuniversitet__slu/pressreleases/nya-digitala-skogskartan-klar-398399) anger sattelitbilder **2005–2006**, medan [SLU pressmeddelande 2010 (2012)](https://www.mynewsdesk.com/se/sveriges_lantbruksuniversitet__slu/pressreleases/ny-digital-skogskarta-fraan-slu-734551) anger främst **2010**. Mer precis dokumentation ovan beskriver även några bilder 2004 respektive 2008/2009.
5. [Skogsstyrelsen, Utförda avverkningar, produktbeskrivning 2026](https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/utforda-avverkningar---produktbeskrivning.pdf): vägledande GIS-lager med detekterade avverkningar; ofullständig täckning och osäkra datum, särskilt över långa historiska perioder.

## Kvarstående frågor och prövning

- **Komponentharmonisering 2010→2015/2018:** Är det möjligt att skilja underjordisk från ovanjordisk biomassa i 2010 års arkiv, eller krävs dokumenterad extern arts-/åldersfunktion? Korrigera inte nivåer utan verifierad metod.
- **2005→2010 totalvolym +23,90 %:** Hur mycket är trädslags-/beståndssammansättning, registrerad historisk avverkning, biologisk tillväxt respektive ändrad kNN-kalibrering? Inget av detta har ännu attribuerats kausalt.
- **Trädslagsvolymer 2005/2010:** EIGHT aktuella SLU GeoTIFF-filer har öppnats med verifierad 25m, EPSG:3021, NoData, skala och offset i PR #71. Relativ volymförändring kan testas på samma celler. `BIRCHVOL` kan överlappa `DECIDUOUSVOL`; **summering förbjuden** innan begreppen verifierats.
- **Avverkning 2006–2010:** PR #71 överlagrar daterade Skogsstyrelsen-polygoner med arkiverad totalvolym och ålder för gemensam geografi i EPSG:3006. Avverkningskartan kan inte ensam verifiera faktisk tillväxt eller kartfel.
- **Mål:** redovisa separata hypoteskontroller, källmetadata och effekter på samma geografiska celler. Ingen publicerad ålders-, biomassa- eller koldioxidtrend ändras före metodkontroll.

**Observera:** Äldre biomassaraster kan inte automatiskt anses uttrycka samma ton torrsubstans/ha om olika komponenter (ovan-/underjordiskt) och råskalningar används. Det är möjligt att en förhöjd nivå 2010 delvis är en definitorisk artefakt.
