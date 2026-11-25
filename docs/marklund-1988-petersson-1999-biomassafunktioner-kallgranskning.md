# Marklund 1988 och Petersson 1999: tolkningsstöd för biomassamodellerna

## Källstatus den 25 november 2026

Projektägaren har tillfört SLU-rapporten:

**Petersson, Hans (1999). *Biomassafunktioner för trädfaktorer av tall, gran och björk i Sverige*.** Institutionen för skoglig resurshushållning, Sveriges lantbruksuniversitet. Arbetsrapport, 31 s.

- [SLU:s permanenta publikationspost](https://research.slu.se/sv/publications/biomassafunktioner-f%C3%B6r-tr%C3%A4dfaktorer-av-tall-gran-och-bj%C3%B6rk-i-sver/)
- [PDF som projektägaren hänvisat till](https://research.slu.se/ws/portalfiles/portal/19293962/fulltext.pdf)
- [Alternativ fil-URL från SLU:s publikationspost](https://research.slu.se/files/19293962/fulltext.pdf)

**Verifieringsnivå:** Publikationens titel, år, författare, omfattning och SLU:s publicerade **sammanfattning** har lästs och verifierats på den officiella publikationsposten. **PDF-fulltexten gick inte att hämta i den aktuella analysmiljön; ingen genomgång av formler, tabeller eller exakta sidhänvisningar görs anspråk på.** Undvik att tillskriva fulltexten ytterligare uppgifter utan verifiering.

## Vad den verifierade sammanfattningen faktiskt säger

- Rapporten utarbetades för **SKA 99** och beskriver **biomassafunktioner** för trädens torrvikt, bland annat för trädfraktioner och biomassan ovan stubbhöjd.
- Utgångsdata är **samma trädmaterial som Marklund (1988)** använde; det innebär **inte** att de nya funktionerna är matematiskt identiska med Marklunds.
- Syftet var att tillgodose framskrivning av biomassa med avseende på både trädens **volym** (diameter, höjd, form) och **densitet** (tillväxthistorik, konkurrens, ålder). Jämfört med Marklund gavs större vikt åt variabler relaterade till densitetskomponenten.
- Rapporten framställde **22 biomassafunktioner** för fraktioner såsom stam inklusive bark, bark, barr, levande och döda grenar, biomassa ovan stubbhöjd samt rot- och stubbfraktioner i vissa arter. **Funktionernas existens innebär inte att dessa fraktioner alla ingår i ett visst GIS-raster**.
- Störst redovisad variation fanns i **döda grenar** (spridning minst **77 %** kring de aktuella funktionerna); för **levande grenar hos björk** nämns cirka **45 %**. Dessa siffror är kopplade till de specifika fraktionsfunktionernas rapporterade residualspridning, **inte** ett osäkerhetsintervall för vår 2010-, 2015- eller 2018-raster.
- Det ursprungliga trädmaterialet **saknade små träd, träd yngre än fem år mätt i brösthöjd, höglägesskog och kustnära skog**. Det begränsar representativiteten i vissa tillämpningar och är principiellt relevant för Luleås geografiska skogsmiljö.
- Peterssons rapport uppger att funktionerna gav liknande torrvikter som Marklunds i simuleringsmodellens utgångsläge, medan skillnaderna mellan funktionerna kunde växa med längre simuleringshorisont. **Detta är inte en direkt jämförelse mellan SLU:s geografiska rasterprodukter 2010 och 2015 eller SGD2 2018.**

## Koppling till tidigare verifierad produktinformation

- **2010**, exakt raster `BIOMASS_XX_P_10.tif`: SLU:s Mats bekräftade via e-post 2026-11-25 enhet **ton TS/ha**, ovan stubbskär inklusive grenar; barr på barrträd ingår, **löv på lövträd ingår inte**, inga stubbar/rötter. Marklund (1988) angavs som funktionsreferens.
- **2015**, exakt `Biomass_leaf.tif`: dokumenterat som **total biomassa ovan jord**, inte endast löv. **Det är inte bekräftat** att den beräknas med samma funktionsuppsättning eller definition av barr/löv som 2010.
- **2018 SGD2**, exakt `SGD2_BIO.tif`: dokumenterad biomassa ovan jord, ton TS/ha; laserskanning i Luleå 2018. Alla 540 verifierade SGD2-indexrutor har `Lov_Avlov=1` (med löv), men detta beskriver mätförhållanden, **inte torrviktsdefinitionen**. **Det är inte bekräftat** vilken individuell biomassafunktion och fraktionssummering som användes i detta raster.

**Källkritisk slutsats:** Rapporten är ett stöd för hur olika biomassafunktioner kan bete sig och varför olika trädslag/åldrar bör särredovisas. Den utgör **inte källbelägg för att SLU Skogskarta 2015 eller SGD2 använder Peterssons 1999-funktioner eller Marklunds 1988-funktioner**. Ingen korrigeringsfaktor får beräknas genom att anta detta.

## Föreslagna nästa verifieringar

1. Be SLU bekräfta **exakt** vilka biomassafunktioner och vilka fraktioner som summeras i `Biomass_leaf.tif` (2015), särskilt barr och löv, och om Marklund/Petersson används direkt eller som kalibreringsunderlag.
2. Be Skogsstyrelsen/SLU bekräfta motsvarande för `SGD2_BIO.tif` (omdrev 2, 2018 i Luleå).
3. När funktionerna är källverifierade: jämför funktionernas förväntade torrvikt för **samma trädstorlek, trädslag och ålder** som ett rent metodtest. Det är **inte** automatiskt en cellkorrigering av GIS-skikten.
4. Använd genomförd PR #112 som deskriptivt rastertest på oavverkad respektive registrerat avverkad skog. Strata baseras på **modellerad** 2010-ålder och modellerad volymdominans, inte oberoende trädobservationer. Det är därför inte möjligt att från dessa strata ensamma identifiera en biomassafunktions systematiska fel.

Originaldata, kolförråd, faktisk avverkning och offentlig kartpublicering ändras **inte** i denna källanteckning.
