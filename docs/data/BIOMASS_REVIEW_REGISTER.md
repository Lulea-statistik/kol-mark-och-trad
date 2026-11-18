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


## Användarobservationer och större granskningsmarkörer (2026-11-18)

Den nya granskningskartan visar **36 px stora cirkelmarkörer** för vanligt slump-/riskurval och **44 px** för de nio användarrapporterade platserna, ovanpå oförändrade polygonkonturer för faktiska källrasterceller om 10 x 10 m. Detta är en skärm-/zoomhjälp och utgör **inte större geografiska rasterceller eller maskområden**.

Manuellt rapporterade koordinater lagras i `docs/data/biomass_user_observations_epsg3006.csv` med miljö, kluster-ID, rapporterad bedömning och motivering. Kända grupper: byggnad i centrum (1), vatten/hamn (1), tre exempelkluster i stålindustriområde (3), sjukhusområde (1), väg (1) samt två ännu ej klassade exploaterade miljöer (2). Alla nio är rapporterade av användaren efter visuell kartgranskning, **inte oberoende verifierade fel**. Automatisk utbredning till närliggande celler skulle sakna tillräckligt belägg och görs därför inte. Orsaken isbrytare/fartyg är endast hypotes.

Kartfilens export `scripts/publish_biomass_review_map.py` läser observations-CSV i dess uttryckliga EPSG:3006, transformerar varje faktisk centrumkoordinat till EPSG:4326 och kopplar observationen till motsvarande originalcell när den redan ingår i urvalet. Annars visas en separat symbol på den angivna platsen. Exportens test `scripts/test_review_map_export.py` kräver att varje rapporterad plats finns **exakt en gång** och att alla förblir oberäftade. Ingen ytterligare klassning eller rasterändring görs.

Utökade markörer är cirklar i **skärmpixlar**; geografiskt korrekta ytor visas separat med befintliga cellpolygoner från verifierad rastertransform.

## Kompletterande manuella observationer 2026-11-18

Ytterligare **17 koordinater i EPSG:3006** från användarens kartgranskning har lagts in i `biomass_user_observations_epsg3006.csv`. Det ger sammanlagt **26 manuella observationer**. De nya punkterna omfattar hårdgjord yta (1), vägar (3), byggnader (6), uppställda tåg (2) och vatten (5). **Uppställda tåg** är en ny hypotes om temporära höga objekt vid laserskanning, motsvarande hamnens möjliga fartygspåverkan, men ingen faktisk närvaro vid flygningstidpunkten har verifierats. Vattenpunkter kräver historisk vattenlinje och ortofoto, och byggnader/vägar kräver geometri med känt datum och CRS.

Alla 26 kartobservationer exporteras till samma Leaflet-GeoJSON i EPSG:4326 efter transformering från verifierat käll-CRS EPSG:3006. Befintliga slumpmässiga kontrollurval och deras inklusionssannolikheter **ändras inte**. Observationerna är manuellt rapporterade, inte oberoende facit; hela kluster eller intilliggande rasterceller markeras inte automatiskt som fel.

## Nya observationer: jordbruksmark, vatten och strandkant (2026-11-18)

Ytterligare **nio nya unika EPSG:3006-positioner** har lagts till i `docs/data/biomass_user_observations_epsg3006.csv`: jordbruksmark (1), öppet vatten (7) och obevuxen strandkant (1). En åttonde angiven vattenpunkt, `848545, 7317675`, förekom redan sedan tidigare och har **inte** dubbelregistrerats. Totalt finns **35 unika manuella observationer**. Dessa är rapporterade granskningsindikationer och aldrig automatiskt verifierade fel. Jordbruksmark kan innehålla träd eller buskar, och strandkant kan ha glest växttäcke; historiska, oberoende bild- och marktäckesunderlag krävs före maskbeslut.

## Tillfällig källaotillgänglighet

GitHub Actions #11 stoppades av att `gis.slu.se` inte kunde nås på HTTPS 443, trots godkända enhetstester; #10 kördes med framgång. Analysen provar nu att öppna original-SGD2 upp till tre gånger vid **RasterioIOError** med paus mellan försöken. Om källan fortfarande inte går att öppna avbryts granskningen; data ersätts aldrig av preliminära eller äldre raster och inga nya kvalitetspåståenden görs.

## Individuell visuell granskning – grön karta (2026-11-18)

De **35 platser som användaren själv pekat ut och bedömt** får nu `observation_status=user_individually_reviewed` i `docs/data/biomass_user_observations_epsg3006.csv`. Exporten anger `individually_reviewed=true` på respektive observation och, för observationer som sammanfaller med slump-/riskurvalet, inom `user_observation` för samma cellpolygon. Enhetstestet kräver 35 individuellt granskade positioner och `independently_confirmed=false` för samtliga.

**Kartans symboler:** grönt `#16a34a` = individuellt granskad av användaren; rött = utpekad men inte individuellt granskad; lila = hamnhypotes; orange/blått = risk-/slumpurval. Statusfiltret delar upp granskade och övriga objekt. Grön betyder uttryckligen **inte** bekräftad felaktig biomassacell och innebär ingen korrigering eller statistik över verifierade fel. Varje observation behåller sin ursprungliga marktyp och motivering. Historiskt daterat oberoende kontrollunderlag behövs fortsatt inför maskningsbeslut.

De fasta cirkelsymbolerna är 36–44 **skärmpixlar**, inte större geografiska maskytor. Källraster och ursprungliga SGD2-pixelkonturer i EPSG:3006 förblir oförändrade.

## Oberoende uppdatering av gröna granskningsmarkörer (2026-11-18)

Om SGD2:s rasterserver `gis.slu.se` tillfälligt är otillgänglig kan man nu starta GitHub Actions-flödet **Refresh biomass review map annotations** i stället för den fullständiga rasteranalysen. Skriptet `scripts/refresh_biomass_review_annotations.py` läser den redan publicerade GeoJSON-kartan med **tidigare originalgeometriska SGD2-celler** och det aktuella registret med manuella observationer i EPSG:3006. Befintliga manuella attribut uppdateras utan dubbletter; nya punkter får EPSG:4326 efter en uttrycklig pyproj-transformering från EPSG:3006. Det ursprungliga stickprovets alla geometrier, råvärden och tidsstämpel lämnas orörda.

Arbetsflödet kör sedan samma `scripts/test_review_map_export.py` som den fullständiga auditen och publicerar enbart `docs/data/biomass_review_snapshot.geojson`. Metadata flaggar att manuella observationer har uppdaterats **utan rasterhämtning**. Detta är uttryckligen **inte** en ny SGD2/NMD-analys. Ny fullständig analys kräver att källservern åter är tillgänglig. Denna process ändrar inga raster eller bekräftar några biomassafel.

## Manuell bedömning av rimlig biomassa kontra misstänkta fel (2026-11-18)

Användaren har kompletterat de tidigare 35 individuellt granskade punkterna med **29 nya unika 10-meterscellcentrum i EPSG:3006**: **12 skogsceller med rimlig förekomst av biomassa**, **2 jordbruksmark utan skog**, **7 byggnader**, **8 vatten**. Det finns nu **64 individuellt granskade punkter**. Tidigare uppgivna punkter har kontrollerats för dubletter.

Ny kolumn `manual_plausibility_assessment` skiljer strikt mellan `plausible_biomass` (12 skogsceller) och `suspected_false_positive` (52 övriga observationer, inklusive tidigare 35). Det senare betyder misstänkt orimligt biomassavärde baserat på användarens visuella kontroll, **inte** vetenskapligt bekräftad felcell; även byggnader, vatten och jordbruksmark kräver historiskt daterad källverifiering före åtgärd. Skog innebär bara att **förekomst** av biomassa är rimlig, inte att den rapporterade biomassamängden är korrekt.

Grön färg fortsätter att betyda **individuellt granskad**. För att inte blanda ihop granskad med felaktig visas en tydligare fylld grön cirkel för `plausible_biomass` och mer genomskinlig grön cirkel för `suspected_false_positive`. Kartans filter **Bedömd biomassarimlighet** kan skilja dessa åt. Separat `independently_confirmed=false` bevaras för alla punkter och ingen råbiomassa eller statistiskt slumpurval förändras. Anteckningar exporteras både vid fullständig rasteraudit och med det fristående annoteringsflödet som fungerar även om SLU-servern är nere.

## Nytt manuellt urval – 25 celler (2026-11-18)

Användaren har klassificerat **25 nya unika centrumkoordinater**, alla angivna i EPSG:3006: **13 vatten, 1 hårdgjord yta, 5 skog (rimlig förekomst av biomassa), 1 byggnad och 5 väg**. Dessa läggs till utan dubbletter i det tidigare registret med 64 poster. Ny totalsiffra: **89 individuellt granskade**, varav **17 rimliga skogsceller** (`plausible_biomass`) och **72 misstänkta falskt positiva** (`suspected_false_positive`). Färgkodningen och de två bedömningsfiltren är oförändrade.

Marktäckebedömningar är användarens visuella observationer, inte oberoende daterat facit. Även i skog gäller rimlig *förekomst* av biomassa, inte verifierad fysisk mängd. Original-SGD2, NMD-raster, källgrid och sannolikhetsurval påverkas inte. Kör den fristående `refresh-biomass-review-map.yml` för att föra över ändringarna till den offentliga GeoJSON-filen utan att vara beroende av SLU:s server.

## Ny manuellt granskad omgång – 64 unika lägen (2026-11-18)

Användaren anger **65 centrumkoordinater i EPSG:3006**, varav en hårdgjord yta `829955,7291915` förekommer två gånger. Efter dubblettkontroll mot både hela listan och befintliga CSV-registret registreras **64 nya unika** centrumlägen: **21 vatten**, **2 strandkant**, **2 väg**, **13 hårdgjord yta** och **26 byggnad**. Inga av de 64 fanns redan i registret.

Totalt **153 individuellt granskade** punkter, uppdelade i **17 skogspunkter med bedömt rimlig förekomst av biomassa** och **136 misstänkta felvärden**. Alla 64 nya poster tilldelas `user_individually_reviewed` och `suspected_false_positive` för användarens visuella marktäckesbedömning, inte `independently_confirmed`. Användarens bedömningar kräver fortfarande separat verifiering mot historiskt daterat underlag, särskilt vid strandlinjer, vägrenar och byggnader. Inga angränsande pixlar maskas automatiskt.

Publicera utan hämtning av SGD2 genom att köra flödet **Refresh biomass review map annotations** efter sammanslagning av ändringen. Originalraster och tidigare representativa slumpurval förändras inte.

## Femte manuella omgången – vatten, byggnad, väg och skog (2026-11-18)

Användaren har angivit 28 vattenpositioner varav 22 unika i meddelandet, 6 byggnadspositioner, 1 skog och 4 väg (EPSG:3006). **9 av de unika vattenpositionerna fanns redan i registret** och **4 koordinater återkommer både under vatten och byggnad**. Efter avstämning finns därför **20 nya unika platser**: **9 vatten**, **4 vatten/byggnad med motsägande användaruppgifter**, **2 byggnader**, **1 skog**, **4 vägar**. De fyra konflikterna är `826645,7290315`, `826645,7290305`, `826635,7290295`, `826635,7290285`. Dessa anges uttryckligen som `reported_context=vatten/byggnad` utan att en av marktyperna godtyckligt ges företräde. De behöver manuellt avgöras mot historiskt daterat källmaterial.

Ny totalsiffra: **173 individuellt granskade unika centrumpositioner**, varav **18 skog där biomassaförekomst bedöms rimlig** och **155 potentiellt orimliga biomassavärden**, inklusive de fyra marktypskonflikterna. Samtliga saknar oberoende verifiering; detta är användarbedömningar. Det fristående GitHub Actions-flödet `Refresh biomass review map annotations` uppdaterar GeoJSON utan rasterhämtning. Originalrastrens geometri och råvärden ändras inte.

## Sjätte omgången – 30 nya granskningspunkter (2026-11-18)

Användaren rapporterade ytterligare **30 nya unika cellcentrum i EPSG:3006**: **9 väg**, **4 vatten**, **16 byggnad** och **1 hårdgjord yta**. Dessa avstämdes mot samtliga 173 tidigare registrerade positioner och inga koordinatdubletter hittades. Totalt **203 individuellt granskade** positioner, varav **18 manuellt bedömda som skog där biomassa kan vara rimlig** och **185 manuellt misstänkta felaktiga biomassavärden**. Samtliga nya poster markeras som individuellt granskade men inte oberoende verifierade fel; deras manuella marktypsbedömningar motiverar inget automatiskt maskbeslut för närliggande celler.

Kör `Refresh biomass review map annotations` för att publicera den nya manuella kartinformationen utan rasterhämtning från SLU. Den tidigare geografiskt verifierade originalgridens geometri och rasterprovvärden lämnas oförändrade.

## Sista riktade granskningsomgången – 20 celler (2026-11-18)

Ytterligare **20 nya unika cellcentrum i EPSG:3006** har registrerats utan dubletter mot de tidigare 203: **2 vatten**, **5 väg**, **8 byggnad**, **4 skog där biomassaförekomst bedömts rimlig**, och **1 jordbruksmark**. Totalt finns **223 manuellt granskade unika lägen**, varav **22 skogskontroller med rimlig förekomst av biomassa** och **201 misstänkta avvikelser** (inklusive fyra olösta vatten/byggnad-konflikter). Samtliga är användarbedömningar utan oberoende historisk verifiering.

### Övergång från riktad granskning till metodutvärdering

Användaren bedömer att de mest prioriterade/riskabla cellerna och celler med höga värden i stort sett har granskats. Därför behöver **inte fler riktade manuella exempel samlas in som standard**. Nästa steg är att analysera vilka regler som återskapar observationerna korrekt och kontrollera eventuella falska positiva mot de 22 rimliga skogskontrollerna. De 223 lägena är ett **selektivt och icke-representativt tränings-/kontrollunderlag**, inte ett giltigt underlag för en generell felandel i SGD2. Eventuella slutsatser om total felandel fordrar ett separat sannolikhetsurval och verifierad referensklassning. Separera fortsatt slumpurval och riskurval. Fyra motstridiga klassningar måste utredas eller exkluderas vid utvärdering av marktyp. Inga rastervärden eller andra celler ska automatiskt maskas utifrån detta material.
