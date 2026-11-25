# NMD2018 temporärt ej skog: volym, nollvärden och dekomponering

## Varför denna analys?

PR #99 fastställde att NMD2018:s klassgrupp **Temporärt ej skog** (koder **118** utanför våtmark och **128** på våtmark) omfattar **469 240 gemensamt giltiga celler** (29 327,5 ha, EPSG:3006 25m) och står för **10 430 210 av totalt 18 566 343 råvärdesenheter** i överskottet 2010–2018: cirka **56,2 %**. Detta är den största **bokföringsmässiga** delposten, inte bevisad avverkningsorsak.

Mål: särskilja möjlig historiskt virkesrik skog från trädfattigare områden med hjälp av **2010 års modellerade virkesvolym**, och kvantifiera var **2015 och 2018 års biomassaraster har faktiska nollvärden**, till skillnad från NoData.

## Ny analys i `scripts/compare_nmd2018_landcover_biomass_volume.py`

Det tidigare verifierade fullständiga rasteromprojektionsflödet för 2010/15/18 och NMD2018 återanvänds **utan ändring av källrastren**:

- 2010 biomassa och volym är original **EPSG:3021, 25 m**.
- 2015 biomassa är original **EPSG:3006, 12,5 m**.
- 2018 biomassa och NMD2018 är original **EPSG:3006, 10 m**.
- Alla raster analyseras på **samma fullt omprojicerade EPSG:3006 25m-grid** med gemensamt giltiga biomassaceller.
- NMD är **kategorisk** (nearest). Årsbiomassa och virkesvolym **ytmedelvärdesomsamplas**. Enhets- och träddelsfrågan kvarstår för 2010.

Gruppering av **endast NMD118/128** efter 2010-volymens råvärde:
- 0
- över 0 men under 50
- 50 till under 100
- 100 till under 200
- minst 200
- 2010-volym saknas

För varje klass beräknas cellantal, summa och medelråvärden biomassa 2010/2015/2018, noll 2015, noll 2018, noll båda åren och andelen av råskillnaden där 2018 års biomassa är noll. Särredovisning per NMD118 och NMD128 ingår. Kontrollvillkor verifierar att klassernas summa och volymklasserna avstämmer exakt mot den redan publicerade gruppsumman.

## Tolkning och begränsningar

**Ett positivt 2010-volymvärde är ett modellerat värde**, inte dokumentation av en faktisk avverkning eller bevis att marken var produktiv skog 2010. Att 2018 års biomassa blir noll kan bero på modellens tre-metersregel, men nollvärde **är inte i sig verifierat orsakad av tre-metersregeln**.

Äldre avverkningsanalys i `scripts/diagnose_nmd_nonforest_harvest.py` gäller **produktivitetsklass 0** – en annan NMD-klassning – och får inte användas som om den omfattade NMD-baskoder 118 och 128. För faktisk avverkningsattribution krävs ett **nytt** geografiskt korsningstest av daterade avverkningspolygoner 2011–2018 mot **samma** 118/128-celler och exakt samma datumdefinition. Befintligt skikt från Skogsstyrelsen är inte ett heltäckande avverkningsregister; frånvaro av träff är inte bevis för utebliven avverkning.

SMD2000 kan ge ytterligare historisk klassning, men de lokala SMD-vektorleveranserna är generaliserade, har licensvillkor och ska inte laddas upp till offentligt GitHub.

## Förhållande till framtida harmoniserad summa 2010

- Den officiella ursprungliga 2010-summan ska inte modifieras.
- PR #99:s gemensamma skogssumma på **1 705 502 celler** är en **arealharmoniserad råvärdesreferens**.
- Denna analys skapar inte automatiskt en korrigerad 2010-summa: den ger data för att välja **spårbara scenarioschabloner** per avverknings-/modellklass, med separat känslighetsintervall.
- En **fysisk** kommunal 2010-summa i ton TS kräver fortsatt källspecifik verifiering av 2010-rastrets enheter/komponenter och jämförbar markyta; den kontroll som tillkom i PR #100 ska inte kringgås.
