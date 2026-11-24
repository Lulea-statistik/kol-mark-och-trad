# Geografisk kontroll av de 115 isolerade vattenklassade cellerna

## Bakgrund och avgränsning

I den godkända [PR #91-körningen](https://github.com/Lulea-statistik/kol-mark-och-trad/actions/runs/45419066760) återfanns **115** 25-metersceller (7,1875 ha) med giltiga biomassaråvärden från alla år, som är minst **99,9 % vatten enligt NMD2018:s ursprungliga 10m-basskikt**, med minst 99,9 % källtäckning och utan markandel hos någon av de åtta omedelbara granncellerna. Alla 115 hade 2010 års skattade volymråvärde minst 100; de kan inte tolkas som bevis på observerad skog där vatten nu finns.

## Kontroll av 2010 års publicerade originalfiler

SLU:s server: https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/

Den listade **Rt90-katalogen** innehåller AGE, BIOMASS, HEIGHT, TOTALVOL samt trädslagsvolymer. Den listar **inte något separat vatten-, skogs- eller markmaskraster**. Detta bevisar inte att ingen mask användes för att skapa produkten, eller att ingen sådan finns i andra dokument eller kataloger. Vi bör inte härleda 'skog år 2010' ur höga modellerade biomassa-/volymvärden.

Enligt [SLU:s datakatalog](https://www.slu.se/miljoanalys/statistik-och-miljodata/miljodatakatalogen/slu-skogskarta/) gäller skattningarna för skogsmark med rutstorlek 25 × 25 meter till och med 2010, men den sidan anger inte hur ursprungliga land-/vattenmasker avgränsades i den exakta rasterfilen för Luleå.

## Ny verifierbar kontroll

Analysprogrammet `scripts/compare_nmd2018_landcover_biomass_volume.py` sammanför cellerna från testet 'helt vatten, ingen landgranne bland åtta' och identifierar **8-sammanhängande grupper** i samma 25m EPSG:3006-rastergrid. Resultatfältet `pure_water_no_eight_land_neighbour_clusters` omfattar antal grupper, största grupp, totalsumman 115 celler samt som mest 30 största gruppers centroid, rutornas yttre rektangel och medelråvärden 2010/2018 och 2010 års virkesvolym.

Centroid och avgränsning har **EPSG:3006**, inte latitud/longitud eller färdiga webbkartskoordinater. Om en senare webbkomponent behöver EPSG:3857 måste koordinater transformeras korrekt. **Detta är en diagnos över historiskt osäkra celler, inte underlag för att ändra biomassan.**

## Hur resultatet bör användas

- Om grupperna ligger i ett fåtal geografiska områden kan dessa granskas särskilt mot historiska flygbilder, Lantmäteriets historiska kartor, vägar, sjöreglering och tillgängliga vattenmasker kring 2010.
- Om grupperna ligger spridda stärker det i stället behovet av att förstå SLU:s käll- och NoData-mask generellt.
- Urvalet är **inte** en slumpmässig inventering av alla vattenytor. Det förutsätter giltiga biomassavärden **2010, 2015 och 2018**, vilket starkt gynnar strandnära/täckta ytor.
- NMD2018 är inte 2010 års markklassning. Kontakta SLU för exakt originalmask, NoData-definition och eventuell klassning av vatten/skogsmark som användes för `BIOMASS_XX_P_10.tif`.

Körningen sparar resultat i workflow-artefakten `nmd2018-landcover-biomass-volume-diagnostics`; den ersätter inte originalserien.
