# Biomassans råvärden per marktäckeklass – NMD2018, Luleå

## Fråga
Vilka marktyper enligt **NMD2018:s basskikt** bidrar till att biomassaråvärdet är högre 2010 än 2015 och 2018, särskilt bland de tidigare observerade cirka 4 993 hektaren med hög virkesvolym 2010?

## Verifierad ny källa
Naturvårdsverkets NMD2018 v1.1 basskikt levereras länsvis i 10 meters raster. För Norrbotten finns ett separat öppet arkiv, [BD_lan_nmd2018bas_ogeneraliserad_v1_1.zip](https://geodata.naturvardsverket.se/nedladdning/marktacke/NMD2018/bas_lan_ogen/BD_lan_nmd2018bas_ogeneraliserad_v1_1.zip) (ca 237 MB). Den produkten skiljer sig från det tidigare använda tilläggsskiktet **NMD produktivitet** med endast klasserna 0, 1, 2. Basskiktet har **25 tematiska klasser**, inklusive skogstyper, temporärt ej skog (118/128), öppen våtmark (2), åkermark (3), öppen mark (41/42), exploaterad mark (51–53), vatten (61/62).

Produktbeskrivning: https://geodata.naturvardsverket.se/nedladdning/marktacke/NMD2018/NMD_Produktbeskrivning_NMD2018Basskikt.pdf. Den anger **EPSG:3006**, **10 m** och att satellitdata övervägande kommer från 2015–2018 medan vissa laserskanningsdata härrör från tidigare år. Det är således **inte ett historiskt 2010-marktäcke**.

## Beräkningsmetod
- Granska original-CRS för både raster och vektor. Arbetsgräns GeoJSON i EPSG:4326 transformeras till EPSG:3006.
- Läs biomassans ursprungliga rasterklipp 2010 (EPSG:3021, 25 m), 2015 (EPSG:3006, 12,5 m) och 2018 (EPSG:3006, 10 m) samt virkesvolym 2010 (EPSG:3021, 25 m).
- Reprojicera **hela inlästa rastergridet** via WarpedVRT till ett gemensamt 25 m EPSG:3006-grid. Medelvärdesomsampling för kontinuerliga råvärden, närmaste granne för kategoriskt marktäcke.
- Beräkna bara celler med giltiga biomassaråvärden från samtliga tre år och gemensam gränsmask, förväntat 2 456 410 celler / 153 525,625 ha.
- Gruppera medelråvärden per var och en av de 25 marktäckeklasserna samt summerat per marktyp; redovisa andel av hela observerade råvärdesskillnaden 2010–2018, och antal celler med **2010 års** virkesvolym minst 100.
- Beräkna den råa kvoten biomassa 2010 / virkesvolym 2010 endast för celler med virkesvolym minst 10. **Ingen biomassakvot för 2015/2018** kan beräknas med 2010 års virkesvolym; den vore inte samtidiga variabler.

## Förväntad tolkning
Undersök särskilt om klasserna **118/128** (temporärt ej skog 2018) har stora positiva skillnader: detta skulle vara förenligt med historisk skog eller föryngring men inte bevisa avverkning. Granska även om produktivitetsklass "ej skogsmark" innefattar NMD-basskiktsklassad trädbärande skog (vilket produktivitetskriteriet kan medge). Ingen 2010-korrigering görs.

## Status
Den nya GitHub Actions-körningen tar fram resultaten som JSON-artefakt. Detta dokument redovisar **metod och plan** tills faktisk körning verifierats, inte påhittade medelvärden.
