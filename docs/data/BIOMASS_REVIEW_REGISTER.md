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
