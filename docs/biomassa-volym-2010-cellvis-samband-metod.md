# Steg 1 – cellvis samband mellan 2010 års biomassa och virkesvolym

## Fråga
Har 2010 års SLU-biomassa och SLU-virkesvolym ett starkt och likartat samband även på ytor som NMD2018 klassar som vatten? Om ja är höga värden i båda modellerna **inte två oberoende observationer** av att skog fanns på platsen.

## Indata och jämförbar population
- SLU Skogskarta 2010 biomassa, RT90 2,5 gon V (EPSG:3021), 25m.
- SLU Skogskarta 2010 virkesvolym, EPSG:3021, 25m.
- SLU Skogskarta 2015 biomassa, EPSG:3006, 12,5m, och SGD2 2018 biomassa, EPSG:3006, 10m – används här **enbart för att avgränsa det tidigare analyserade gemensamma giltighetsurvalet**.
- NMD2018 basskikt, EPSG:3006, 10m, för klassning i vatten (61/62), skog (111–117,121–127), övrig mark och var och en av NMD:s originalklasser.

Alla ingående GeoTIFF-filers **faktiska käll-CRS och upplösning kontrolleras**. Rasters omprojiceras fullt och blockvis med WarpedVRT till **gemensamt 25m-grid EPSG:3006**: `Resampling.average` för biomassa/volym och `Resampling.nearest` för kategoriska markklasser. Inga transformerade enbart bounding box-ytor används som ersättning för rasterdata.

## Diagnostik
För varje grupp, alla giltiga celler och för varje **10 × 10 km ruta i EPSG:3006** beräknas:
- Antal matchade celler och areal.
- Medelvärde av 2010 års råvolym och råbiomassa.
- Pearsons korrelationskoefficient `r`.
- Minsta-kvadratlinje `biomassa_2010 = intercept + slope × virkesvolym_2010`, med `R²` och residualernas RMSE.
- Medelvärde och standardavvikelse för kvoten `biomassa/volym`, endast för celler med virkesvolym **minst 10**. Dessutom antal med virkesvolym minst 100.

Beräkningarna är **deskriptiva och råvärdesbaserade**. De är inte en verifierad tonomräkning, fysisk densitet eller mekanistisk biomassamodell. Positiv korrelation kan uppstå av gemensamma käll- eller modellingångar, av verklig samvariation, eller av båda. Hög samvariation innebär inte att råvärdena är korrekta på vatten.

## Tolkning
- **Liknande lutning och förklaringsgrad över vatten och skog:** förenligt med en gemensam modellrelation. Vi behöver då granska indata-/landmask, inte bara biomassalagrets rasterupplösning.
- **Annorlunda samband för NMD-vatten:** kan indikera avvikande markförhållanden, pixelklassificering, mask eller urvalseffekter.
- **Regionalt likartade samband:** ger stöd för att mönstret är systematiskt över kommunen snarare än ett fåtal lokaliserade geometriska fel.

**Viktig begränsning:** NMD2018 beskriver *inte* klassningen 2010. Gemensam validitet 2010, 2015, 2018 selekterar studieytan. Källornas biomassaenheter och omfattning av rötter/stubbar är inte slutligt harmoniserade.

## Teknisk spårbarhet
Arbetsflöde `.github/workflows/compare-biomass-nmd2018-landcover.yml` kör `scripts/analyze_2010_biomass_volume_cellwise.py` på samma arkiverade oförändrade källraster som tidigare analyser. JSON-artefakten `metadata/biomass_volume_2010_cellwise.json` innehåller `overall`, `nmd_groups`, `nmd_classes`, `geographic_tiles_by_group`, urvalsräkning och metodreservationer. CI verifierar att cellantal summerar exakt över grupper och 10 km-rutor.

**Steg 2:** när steg 1 är verifierat, jämför underliggande NoData-/markmaskkriterier för de två SLU-produkterna. Ändra inte originalraster före metodverifiering.
