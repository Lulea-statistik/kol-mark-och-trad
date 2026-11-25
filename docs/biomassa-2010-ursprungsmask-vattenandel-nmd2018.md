# Steg 3: ursprunglig 2010-mask mot NMD2018:s vattenandel

## Fråga
2010 års SLU Skogskarta innehåller giltig biomassa och virkesvolym för bara 0,62 procent av de celler som NMD2018 klassar som vatten **på vårt tidigare gemensamma EPSG:3006-grid**. Är de giltiga 2010-cellerna främst sådana som är blandningar av vatten och mark, eller finns giltiga 2010-värden även i 25m-celler som NMD2018 klassar som helt vatten?

## Detta är en ny, självständig analys i 2010 års källgrid
- **Biomassa 2010:** läses direkt från originalklippets **EPSG:3021, 25 m**. Värden och giltighetsmask **omprojiceras inte**.
- **Virkesvolym 2010:** läses från sitt eget **EPSG:3021, 25 m** och krävs ha **exakt samma transform och rutstorlek**. Om källgridden inte är identiska avbryts körningen i stället för att skapa ett falskt cellvist samband.
- **NMD2018:** ursprungligt basskikt **EPSG:3006, 10 m** med kod 61/62 = vatten. Två *binära* källraster beräknas: vattenklass 0/1 och giltig NMD-täckning 0/1. Dessa omprojiceras med **ytmedelvärdesmetod** från det faktiska 10m-källgriddet till **varje pixel i SLU:s ursprungliga EPSG:3021-grid**. Operationen körs på kompletta destinationstiles med rastergeometrin och kan inte ersättas av transformerade bounds/koordinathörn.
- Kommungränsen transformeras till EPSG:3021 och pixelmitten avgör om cellen ligger i kommunen.

### Vattenandel
Endast 25m-celler med minst **99,9 % giltigt NMD2018-källunderlag** ingår i procenternas nämnare. Vattenandel enligt NMD2018 delas in så här:

| Band | Exakt gräns |
|---|---|
| 0 % | Vattenandel högst 0,001 % |
| >0–25 % | Över 0,001 % till och med 25 % |
| >25–50 % | Över 25 % till och med 50 % |
| >50–75 % | Över 50 % till och med 75 % |
| >75–<100 % | Över 75 % men mindre än 99,9 % |
| 100 % | Minst 99,9 % NMD2018-vattenklass inom giltig källtäckning |

Sista klassen representerar *helt vattenklassat enligt NMD2018 inom numerisk tolerans* – **inte** 100 % fysisk vattenyta i verkligheten eller vatten år 2010.

För varje band redovisas **alla** klassade 25m-källceller inom Luleå och separat:
- Hur många som har **giltig biomassa 2010**.
- Hur många som har **giltig virkesvolym 2010**.
- Hur många som har **båda giltiga**, även där 2015 och 2018 saknar data.
- Hur många giltiga 2010-celler som faktiskt har värdet **0**, skilt från NoData.
- Medelråvärde på de **giltiga** cellerna, inte på samtliga NMD-klassade celler.

### Grannskap på helt vattenklassade 2010-källceller
Alla celler i 100 %-bandet partitioneras ytterligare:
1. Minst en **sidogranne** av de fyra grannarna innehåller någon landandel enligt NMD2018.
2. Enbart **diagonal granne** har landandel, ingen sidogranne.
3. **Ingen landandel bland åtta grannar**.

Nämnaren omfattar alla NMD-täckta celler inom kommunens och 2010-rasterfilens utbredning, så att andel giltiga 2010-celler kan beräknas även för öppna vattenytor. Dessa utfall ska jämföras med PR #95 men är **inte exakt samma rutpopulation**, eftersom tidigare analys låg i EPSG:3006 25m och krävde andra giltigheter.

## Vetenskapliga reservationer
- NMD2018 beskriver **2018 års marktäcke**, inte hur vatten, skog och strand såg ut 2010. Analysen kan inte ensam avgöra om originalmasken var fel.
- Källfilens NoData visar giltig datatäckning men avslöjar **inte vilken historisk modellmask** (skog, mark, vatten) som användes.
- Källarkivet innehåller kommunala klipp. Källklippets egna NoData- och yttergränser kan skilja sig från det nationella produktionsrastret. Utanför källfilens utbredning räknas inga 2010-celler i denna analys.
- NMD:s vattenfraktion utgår från klassade 10m-rutor och areaomräkning, **inte verifierad strandpolygon** med exakt geografisk gräns.
- 100 %-bandet inkluderar numerisk tolerans på 0,1 procentenhet; nollbandet har 0,001 procentenhet. Detta är medvetet asymmetriskt eftersom rasteroperationen kan ge avrundningsfel.
- Giltig rastercell 2010 är **inte** liktydig med uppmätt skog och råbiomassan har ännu inte verifierad gemensam fysisk enhet.

## Reproducerbarhet
`scripts/audit_native_2010_water_fraction_mask.py` och workflow `.github/workflows/audit-native-2010-water-fraction.yml` hämtar de arkiverade ursprungsfilerna och Naturvårdsverkets NMD2018 10m basraster från Norrbotten. Resultaten sparas i `metadata/native_2010_water_fraction_mask.json`, med en SHA-256 för NMD-källarkivet. Workflow verifierar att sex vattenband partitionerar hela eligible NMD-populationen och att de tre 4/8-granngrupperna partitionerar 100 %-bandet.

**Ingen ursprungsfil ändras och inga modellerade värden korrigeras.**
