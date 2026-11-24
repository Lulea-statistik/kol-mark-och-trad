# Strandnära skogsridåer och 2010 års biomassaanomali – kontroll mot NMD2018

## Fråga
En möjlig förklaring är att strandnära skog ofta lämnas kvar av naturvårdsskäl och på grund av begränsad bärighet, vilket kan göra att grövre 2010-celler täcker både land med träd och vatten. Detta är en **hypotes**, inte ett verifierat generellt beteende hos skogsbruk eller skogsmark i Luleå kommun.

## Metod
Använd den befintliga godkända jämförelsen från NMD2018:s klassraster (10 m, EPSG:3006) och biomassarastren (2010 EPSG:3021 25 m, 2015 EPSG:3006 12,5 m, 2018 EPSG:3006 10 m). Kontrollera ursprungligt CRS och reprojicera samtliga rastergrid till samma **EPSG:3006 25-metersgrid** innan jämförelser. Beräkna avstånd med Euklidiskt rasteravstånd mellan cellcentra, inte GIS-bounds.

1. **Från vatten mot land**: För celler NMD2018-klassade som vatten (61/62), klassificera avstånd till närmsta NMD-icke-vattencell: 25–50, 50–100, 100–250 och minst 250 meter. Summera antal, areal, biomassans medelråvärden 2010/2015/2018 och andel med 2010-volym >=100.
2. **Från skog mot vatten**: För celler som NMD2018 klassar som skog (111–117, 121–127), beräkna motsvarande avstånd till närmaste NMD-vattencell och medelråvärden för alla tre år. Detta testar om skogen *närmast* vattnet har högre eller lägre modellskattning än skog längre från vattnet.
3. **Vatten intill skog jämfört med vatten utan närliggande skog**: För vattenklassade celler jämför avstånd **högst 50 m** till NMD2018-skog mot längre avstånd. Det prövar om höga biomassaråvärden i vatten ligger vid skogsklädda stränder, eller även vid åker, bebyggelse och öppna stränder.

Alla resultat avser endast de **2 456 410** gemensamt giltiga 25-meterscellerna (153 525,625 ha) och NMD2018-klasser. Att NMD2018 klassar skog på land 2018 säger inte att samma skog fanns där 2010. Strandavståndet gäller 2018 års rasterklass, **inte historiska strandlinjer**, och vattencellerna inom gemensam biomassadatabredd utgör inte alla kommunens vattenceller.

## Tolkning och risker
- Skillnader mellan modellskattade 2010- och 2018-värden kan bero på verkliga avverkningar, skogsridåer, källans markmask, definitionsskillnader och rumslig förskjutning. Ingen orsak är fastställd på förhand.
- Avståndsklasserna är cellcentrum–cellcentrum; en vattenklassad 25m-cell kan på marken täcka både strand och vatten, och den faktiska strandlinjen är inte automatiskt vid centrumgränsen.
- Analysens vattenpopulation väljs bara där **alla tre biomassaraster har giltiga värden**, vilket sannolikt är starkt selekterat till strandnära vatten. Utvidga inte detta resultat till öppet vatten.
- Eventuell kvarlämnad hänsynsremsa är **inte direkt observerad** i analysen; det behövs oberoende historiska flygbilder eller avverknings-/skogsbruksdata för att verifiera en faktisk skyddad ridå.
- Biomassa anges i oharmoniserade **råvärden**; ingen skattning av ton kol, faktisk beståndsförändring eller omräkning av originalraster görs.

## Spårbarhet
Kör [Compare biomass and 2010 volume by NMD2018 landcover](../.github/workflows/compare-biomass-nmd2018-landcover.yml) i GitHub Actions. Utdata `metadata/nmd2018_landcover_biomass_volume.json` innehåller fältet `nmd2018_riparian_forest_gradient` och artefakten arkiveras av arbetsflödet.
