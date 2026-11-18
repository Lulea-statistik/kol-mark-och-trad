# Granskningsprotokoll för SGD2 × NMD2018

Efter Actions-körningen finns `biomass_independent_review_register.csv` i samma ZIP som övriga kvalitetsrapporter.

## Register och bedömningsbeslut

Varje unik cell representeras av `cell_id` beräknat från centrumkoordinater i **EPSG:3006**. En cell kan omfattas av flera flaggor; dessa lagras i `flag_rules` och ska **inte** räknas flera gånger. Granskningsurvalet bygger på prioriterade höga värden per klass: `risk_ranked_not_random`. Urvalet är inte representativt för alla biomassaceller.

Först är varje cell `not_reviewed` och `proposed_action=no_change`. Den som bedömer en cell ska dokumentera:
- Oberoende källa, datum för källmaterialet, källans verifierade EPSG-kod och bedömd lägesosäkerhet.
- Observerat marktäcke, biologisk rimlighet, bedömare, datum och motivering.
- Bedömning `confirmed_error`, `plausible_biomass` eller `uncertain`.

Sätt endast `proposed_action` till `zero_in_derived_product` eller `nodata_in_derived_product` för en dokumenterat `confirmed_error`. Välj **0** bara om cellen verkligen saknar biomassa; använd **NoData** om värdet är okänt/ej tillämpligt. Skriptet kontrollerar att bekräftade fel har källbelägg och att ofullständiga/oskäliga korrigeringsförslag stoppas.

Lokalt efter manuell granskning:

```bash
python scripts/create_biomass_review_register.py --validate /sokvag/till/ifyllt_register.csv
```

Ingen maskningsfil, ändring av raster eller uppdatering av den publika webbplatsen sker. Utfallet är **manuell valideringsstatus**, inte en automatisk rättning.

## Kvalitetspåstående

Minskad totalbiomassa eller färre flaggade celler räcker inte för att visa förbättring. Ett kvalitetsmått kräver jämförelse med **oberoende sanningsunderlag**. Eftersom nuvarande register består av riskprioriterade höga värden får andelen bekräftade fel i registret **inte** generaliseras till alla kommunens celler. För generaliserbara mått behövs ett separat, stratifierat slumpmässigt urval och osäkerhetsintervall.


## Representativt kontrollurval – ny komplettering

Utöver de 135 tidigare **riskprioriterade**, ej representativa granskningscellerna skapas ett nytt sannolikhetsurval i artefakten `biomass_stratified_validation_sample_epsg3006.csv` tillsammans med urvalsprotokollet `biomass_stratified_sample_design.md`.

Urvalet görs genom k-minsta oberoende slumpnycklar från alla gemensamt giltiga originalceller, med fixerad seed, och **utan återläggning** inom var och en av åtta **ömsesidigt uteslutande** klasser: positiv biomassa i sammanhängande NMD-vatten, i vattenkant, i byggnad, på väg, på annan exploaterad mark, höga råvärden i övriga klasser (>500), ordinär positiv biomassa (oflaggad kontroll) och nollvärden (negativ kontroll). Klassningen använder denna uttryckliga prioritetsordning; cellen tillhör den första matchande klassen. Målet är 30 slumpade celler per klass (eller alla om klassen innehåller färre).

För varje klass sparas den exakta populationen, stickprovsstorleken och inklusionssannolikheten. Detta tillåter senare viktning efter oberoende manuell bedömning. **Inga manuella kontrollresultat finns vid genereringen**. Ett stratifierat urval förbättrar urvalsdesignen men gör inte NMD2018 till en oberoende sanningskälla.

Källa: raster-SGD2 och NMD2018 10 m i faktiskt verifierad EPSG:3006; de analyseras i originalgrid innan eventuell kartreprojicering. Granskaren måste verifiera CRS för ortofoto/vektorkälla, fotograferingsår och lägesnoggrannhet samt tolka vegetation i blandpixlar. Inte heller detta urval innebär att någon maskning eller ändring av biomassaraster görs.


## Granskningskarta och isbrytarhypotes (hamn)

Efter en ny fullständig audit körs `scripts/publish_biomass_review_map.py` och exporterar `docs/data/biomass_review_snapshot.geojson`. GitHub Actions publicerar endast denna genererade fil till `main` (kräver rättigheten `contents: write`), vilket gör den tillgänglig för [granskningskartan](../biomass-review.html) i GitHub Pages. Resultatfilen bifogas också som Actions-artefakt. Om publiceringen misslyckas ska redan granskade kvalitetsvärden inte påverkas; kontrollera jobbets publiceringssteg.

**Koordinatsystem:** Käll-SGD2 och NMD2018 verifieras i programmet vara EPSG:3006. Programmets metadata innehåller nu SGD2:s faktiska sexdelade affina transform. De 10 × 10 m rastercellernas fyra hörn hämtas från **originalgridet** och transformeras med pyproj till EPSG:4326 för GeoJSON/Leaflet. Detta är inte en bbox-transformation eller rasteromprojektion; GeoJSON innehåller **vektoriserade cellkonturer**, inte ett återprojicerat raster. Ingen originalrastercell ändras. Ingen geopandas används.

Användaren har pekat ut två punkter med möjliga isbrytare eller andra höga fartyg i hamn: **22,171025° Ö / 65,571144° N** och **22,170352° Ö / 65,572057° N**. Punktenas talformat är geografiska grader. Vid kartvisningen har dessa uttryckligen **tolkats** som longitud/latitud EPSG:4326, men datum och exakt CRS från koordinatverktyget är inte oberoende verifierade. Punkterna är **granskningshypoteser, inte konstaterade fel**, och symbolerna är punkter – inte uppskattade fartygs- eller cellavtryck.

### Granskningsfråga

Fartyg som ligger vid kaj vid laserskanning eller annat höjdbaserat insamlingstillfälle kan vara en tänkbar förklaring till avvikande höga värden på vatten. För att särskilja detta från faktisk vegetation och modellbrus måste minst tre saker verifieras:

1. Biomassacellens **faktiska läge**, storlek, värde och samtidiga NMD-klass.
2. **Laserskanningens/flygdatainsamlingens datum**, samt om fartyg faktiskt låg vid kaj vid just den tidpunkten.
3. **Oberoende** geografiskt bevis, t.ex. tidsbestämt ortofoto, fartygspositioner med tillräcklig läges-/tidsnoggrannhet och vatten-/kajgeometri. En aktuell satellitbild räcker inte som historiskt bevis.

Om en cell blir verifierad som felaktig kan beslut dokumenteras i separat granskningsregister. Det är **inte** lämpligt att nollställa alla celler kring hamnpunkterna; kajer och närliggande vegetation kan innehålla verklig biomassa.
