# Känslighet hos vattenklasserna: NMD2018 10 m → gemensamt 25 m-grid

## Syfte
Testa om NMD2018-klassningen vatten (61 sjö/vattendrag, 62 hav) ändras beroende på hur det ursprungliga 10 m-märktäckesrastret reprojiceras till det gemensamma **25 m-gridet i EPSG:3006**. Detta är en klassningskänslighet, **inte** en förändring av 2010 års biomassaraster eller ett bevis för varför 2010 har höga råvärden över vatten.

## Metod
Analysens ursprungliga 10 m NMD2018-källa kontrolleras för CRS och reprojiceras som **fullständigt raster** till samma 25 m EPSG:3006-grid på två sätt:
1. **Närmaste granne (nearest):** en källcell bestämmer målcellens klass. Denna metod används i vår publicerade klassanalys.
2. **Typvärde/modal klass (mode):** vanligaste källvärdet i målcellens område bestämmer klassen. Detta är ett alternativt marktypstest och ger inte en faktisk 2010-strandlinje.

För identiska positioner med giltiga biomassaråvärden 2010/2015/2018 och NMD-klass i **båda** varianterna redovisas fyra grupper: vatten enligt båda, vatten bara enligt nearest, vatten bara enligt mode och icke-vatten enligt båda. Antal celler, areal samt medelråvärden för 2010 respektive 2018 beräknas på identiska positioner i varje grupp.

För jämförbarhet bevaras övriga beräkningar i PR #85–86, inklusive 106 594 ha NMD2018-klassad skog, avstånd till icke-vatten och fördelning på trädslag. Datamasken ändras inte i ursprungliga jämförelser.

## Beslutslogik
- Stora värden och stor areal *bara* i en av klassningsvarianterna stärker hypotesen om att omsampling/strandklassning är viktig.
- Lika höga värden på ytor där **båda** metoderna säger vatten ger skäl att granska källmask, modellskattad biomassa, CRS och klipplogik ytterligare.
- Skillnaden mellan 2010 års 25 m biomassa och 2015/2018 års finare biomassa går **inte att isolera** genom detta enda test, eftersom både produktmetod och år skiljer sig.

## Källor och reservationer
Original NMD2018: Naturvårdsverkets raster i 10 m, SWEREF99 TM (EPSG:3006). Biomassa 2010: SLU Skogskarta 25 m, RT90 2,5 gon V (EPSG:3021); 2015: 12,5 m (EPSG:3006); 2018: 10 m (EPSG:3006). Alla tre biomassarastren reprojiceras fullt med medelvärdesomsampling före gemensam celljämförelse.

Data publiceras i arbetsflödets JSON-artefakt efter godkänd körning. Ingen faktisk biomassaförändring eller biomassaenhet anses verifierad genom detta känslighetstest.
