# Steg 2: datatäckning och NoData i 2010 års originalraster

## Utgångspunkt
Den godkända PR #94-körningen visar ett starkt samband mellan 2010 års biomassaråvärden och modellerad virkesvolym, även inom ytor som **NMD2018 klassar som vatten**. Ett samband styrker inte att skog fanns där 2010, eftersom modellerna kan ha gemensamma källdata.

Nästa fråga är om skillnaden beror på **vilka källceller som behandlas som giltiga**, och i vilken utsträckning tidigare studier selekterat vattenytorna genom att kräva giltiga biomassavärden även 2015 och 2018.

## Analysens fyra oberoende rastergiltigheter
I det verifierade EPSG:3006-griddet med 25 m sida testar vi separat:
1. SLU biomassa 2010, original EPSG:3021 och 25m.
2. SLU virkesvolym 2010, original EPSG:3021 och 25m.
3. Biomassa 2015, original EPSG:3006 och 12,5m.
4. Biomassa 2018, original EPSG:3006 och 10m.

Ur NMD2018 (original EPSG:3006, 10m) väljs skog, vatten (61–62) och övrig mark. **Detta är 2018 års marktäcke**, inte 2010 års historiska skogs-/vattenmask.

Alla käll-CRS kontrolleras med metadata och tolerans för äldre WKT. Kontinuerliga rastern omprojiceras fullt till gemensam EPSG:3006 25m med `WarpedVRT(Resampling.average)`. Markklasskartan omprojiceras som kategori med `Resampling.nearest`. Geografiska gränser omvandlas till EPSG:3006 innan rastermaskning.

För varje markklass och större marktäckegrupp räknas 16 möjliga kombinationer av giltiga/ogiltiga värden för de fyra rastren. Dessutom särredovisas:
- Hur många celler som är giltiga enligt **båda 2010-produkterna**, oavsett år 2015/2018.
- Hur många av dessa som även har giltiga biomassavärden 2015 och 2018 – ett urval som bör överensstämma exakt med PR #94:s 2 456 410 celler.
- Hur många datagiltiga celler som faktiskt har **nollvärde**. Noll är inte samma sak som `NoData`.
- Originalens deklarerade NoData, pixelstorlek, CRS, antal band och rastermask-flaggor.

## Metodkritik
`WarpedVRT` ger **effektiv giltighet efter reprojicering**, inte alltid exakt samma sak som masken hos originalrastercellen. Vid gränser kan ett medelvärde få giltig täckning även om bara en del av målcellens yta täcks av källdata. För slutligt bevis om den historiska masken krävs granskning av originalets ursprungliga grid och produktens framställningsdokumentation.

En **giltig 2010-biomassacell som NMD2018 klassar som vatten** bevisar varken felaktigt vattenfilter eller faktisk skog 2010. Vi känner ännu inte den exakta historiska markavgränsningen.

## Beslutsstöd
- Om 2010-produkterna har nästan samma effektiva giltighet över dagens vatten, kan detta indikera gemensamt källurval eller mask.
- Om vattenpopulationen krymper mycket när 2015/2018 krävs, är de tidigare 2010-vattenmedelvärdena starkt selekterade.
- Om biomassa och volym skiljer sig i datatäckning behövs en produktspecifik analys av NoData och möjlig rumslig förskjutning.

Resultatet sparas i GitHub Actions-artefakten `metadata/biomass_source_coverage_2010.json`. Alla originalraster är oförändrade.
