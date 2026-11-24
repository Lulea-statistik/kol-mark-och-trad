# Test: helt vattenklassade 25-metersceller och fyra/åtta grannar

## Hypotes
2010 års 25-metersbiomassa kan bli missvisande längs stränder när NMD2018:s finare 10-metersraster redovisar vatten. En större cell kan innehålla både träd och vatten; samtidigt kan 2010 års markmask ha varit annorlunda. **Vi testar det som kan testas med befintliga raster**, utan att likställa NMD2018 med faktisk strandlinje år 2010.

## Rastermetod
1. Läs Naturvårdsverkets **original-NMD2018-basskikt (10 m, EPSG:3006)**. Skapa två **binära** raster i källans eget 10-metersgrid: vatten (61=insjö/vattendrag, 62=hav) och giltig datatäckning. Kategorier får inte medelvärdesinterpoleras direkt.
2. Omprojektera **båda hela relevanta rasterfälten** till analysens faktiska 25-metersgrid i EPSG:3006, genom blockvis ytmedelvärdesomräkning av binära vatten- och giltighetsmasker. Detta ger andelen yta som klassats som vatten och täckningen av giltiga NMD2018-celler för varje 25-meterscell. **Endast transformerade bounds används aldrig som rasterdata.**
3. Avgränsa *helt vattenklassad cell* konservativt till >=99,9 % klassat vatten **och** >=99,9 % giltig ursprungstäckning. Detta är '100 % enligt det ursprungliga klassade 10 m-rastret' inom numerisk tolerans, inte exakt uppmätt fysisk vattenyta.
4. Granska angränsande celler i samma 25-metersgrid. **4-grannar**: markandel i minst en sidocell (N/S/Ö/V). **Endast diagonalgranne**: markandel i minst en diagonalcell men ingen sidocell. **Ingen markgranne bland 8**: inget 25m-grannfält innehåller klassad mark. Grupperna är ömsesidigt uteslutande och bör summera till alla helt vattenklassade celler inom den gemensamma biomassapopulationen.
5. Beräkna biomassamedelråvärden 2010/2015/2018, area, cellantal och antal med 2010 års virkesvolym >=100 för grupperna. För kontext beräknas även blandade mark/vattenceller (vattenandel mellan 0,1 % och 99,9 %) och skillnaderna i vilka celler som den tidigare 25m-NMD-närmaste-granne-metoden klassar som vatten.

## Förväntade slutsatser och begränsningar
Om 2010 års höga biomassaråvärde endast uppstår i blandade strandceller talar det för en stor geografisk gränseffekt. Om höga värden finns även på **helt vattenklassade celler utan någon landgranne bland de åtta närmaste**, är det förenligt med en ytterligare modell-, mask- eller historisk klassningsskillnad – men det bevisar inte att vatten fanns där 2010.

Urvalet avser **endast gemensamt giltiga biomassa-celler** för alla tre år. Det är starkt selekterat och är ingen heltäckande vatteninventering. En 25m-cell bredvid en 25m-cell med markandel påvisar inte att skog växer precis vid strandlinjen. Olika skannings-/modellår och komponentdefinitioner kvarstår. **Inga originalraster eller råvärden justeras.**

## Spårbarhet
Arbetsflödet `compare-biomass-nmd2018-landcover.yml` skriver resultat i `metadata/nmd2018_landcover_biomass_volume.json`, fältet `original_10m_water_fraction_and_4_8_neighbours`. Kontroller kräver att vattenklasserna och grannklasserna summerar utan dubbelräkning. Rasternas käll-CRS kontrolleras innan analys.
