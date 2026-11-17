# Biomassans rimlighet och oberoende validering

## Syftet

En förbättring ska motsvara att **felaktiga biomassavärden kan identifieras och korrigeras med högre säkerhet**, inte att totalsumman blir större eller mindre. Från och med denna utveckling redovisas separata riskflaggor, men **inget automatiskt fastställt fel**.

## Regler som faktiskt körs på samma SGD2 10m-grid i EPSG:3006

- Positiv biomassa på **sammanhängande inlandsvatten eller hav** med enighet i 3×3 NMD2018-celler: hög granskningsprioritet. Vatten vid klassgräns redovisas separat.
- Positiv biomassa inne i sammanhängande NMD2018-klasser **byggnad (51)** respektive **väg (53)**: granskningsprioritet; observera att NMD är rasterklass och inte verifierad byggnadsyta/asfaltgeometri.
- Övrig exploaterad mark (52): granskningssignal, **inte raderingsgrund**.
- Råvärden >500 och >1000: **endast urval för extremvärdesgranskning**. Kombinationsflagga för extremvärde på vatten/byggnad/väg.
- Alla flaggor redovisas som antal celler, nominell cellarea och summa råvärden. Grupper kan överlappa och får **inte summeras till ett unikt antal**.

Efter GitHub Actions-körning finns artefakterna:
- `biomass_plausibility_review.md`: klasser, flaggor och beslutskriterier.
- `biomass_review_candidates_epsg3006.csv`: prioriterat granskningsurval med koordinater i EPSG:3006, klass, råvärde och flagga. Urvalet är **avsiktligt inriktat mot höga värden**, inte representativt stickprov.
- Tidigare analysresultat och sex stegvisa känslighetsscenarier finns kvar oförändrade.

## För att kalla en cell felaktig

Kontrollera cellens läge mot oberoende ortofoto, polygoner för öppet vatten eller byggnadsavtryck, eventuell historisk karta och laserdata/trädhöjd. Ange underlagets datum, CRS, metod och eventuella lägesfel. För hög biomassa krävs dessutom verifierad GeoTIFF-enhet/skalning och lämplig referens för biologiskt plausibla värden på motsvarande skogstyp; en global gräns är inte tillräcklig.

Ett framtida **oberoende, stratifierat slumpmässigt stickprov** bör ge en osäkerhetsuppskattning för (1) hur stor andel föreslagna borttagningar som faktiskt är fel (precision), och (2) hur stor andel plausibla biomassaceller som riskerar att tas bort. Redovisa vattenceller, byggnader, vägar och extremvärden separat och jämför varje iteration mot denna kontroll.

## Maskningsbeslut

Ingen ny maskning förrän oberoende källvalidering har dokumenterats. Redovisa därefter original, godkända exkluderingsregler och förändrade riskmått **för samma giltiga cellpopulation**. Håll ursprunglig produkt oförändrad och publicera validerad variant separat. Skilj på `0` (verifierat ingen biomassa) och `NoData` (okänt eller ej tillämpligt), och visa hur valet påverkar medelvärden och arealer.
