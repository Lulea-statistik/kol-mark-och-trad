# Oberoende validering av biomassa 2010–2018 mot Riksskogstaxeringen

**Status 27 november 2026:** källinventering och metodgranskning; **ingen oberoende korrigeringsfaktor verifierad**. Den tidigare jämförelsen av biomassaraster är en modell-till-modell-analys, inte en jämförelse med fältmätningar.

## 1. Kontroll av källor och tillgänglighet

| Källa | Vad den faktiskt innehåller | Årtäckning / geografi | Lämplig användning | Begränsning |
|---|---|---|---|---|
| SLU PxWeb, produktiv skogsmark, tabell 3.29b (trädbiomassans torrvikt, fraktioner) | Miljoner ton torrvikt: stam+bark, grenar+barr, ovan stubbskäret, stubbar+rötter, total; skyddade områden skiljs åt | Länsvis, från 2016; femårsmedelvärden | Kontroll av länsnivå och komponentdefinition runt 2018 | **Ingen direkt kommunskattning** för Luleå och inte historisk länstabell för 2010 enligt nuvarande PxWeb-tabell |
| SLU PxWeb, virkesförråd och produktiv skogsmarksareal | Volym samt areal efter län, ålder och trädslag | Långa historiska länstidsserier inklusive 2010 | Oberoende rimlighetskontroll av skattad volym och beståndsstruktur | Virkesförråd m³sk är **inte biomassa ton TS** |
| SLU Taxwebb (Excel-nedladdning) | Uppgifter om levande träd, volym och biomassa; kan visa relativt medelfel och konfidensintervall | All produktiv skogsmark från 2005, andra urval längre bakåt | Kandidat för historiska länsvisa skattningar kring **2010** och **2018**, med osäkerhet | Kräver verifierad urvalskonfiguration, viktning och eventuell jämförbarhet mellan metoder; stor Windows/PowerPivot-fil |
| SLU Riksskogstaxeringens ytdata | Tillfälliga provytors fältdata avsedda som fjärranalysvalideringsdata | Från 2007, uppdaterade data till 2025 enligt SLU:s nedladdningssida | Eventuell extern validering av modellvärden vid provytor, efter kontroll av åtkomliga geolägen och mättidpunkt | **SLU avråder uttryckligen från att använda detta urval för totalskattningar eller medelvärden för ett område**; provytor på bestånds-/ägoslagsgränser är uteslutna |
| SLU:s officiella statistik/Skogsdata | Landsomfattande historiska biomassatrender och vissa geografiska tabeller | Historiska femårsperioder | Kontext och komponentdefinition | Rikssiffror får inte användas som direkt kommunal validering |

### Verifierbara källor

1. SLU, officiell statistik om skog: https://www.slu.se/miljoanalys/statistik-och-miljodata/statistik/
2. SLU, produktiv skogsmark, färdiga PX-tabeller: https://www.slu.se/om-slu/organisation/institutioner/skoglig-resurshushallning/miljoanalys/riksskogstaxeringen/vara-data/senaste-statistiken/produktiv-skogsmark/
3. SLU, PxWeb tabell 3.29b, länsvis trädbiomassa: https://skogsstatistik.slu.se/pxweb/sv/OffStat/OffStat__ProduktivSkogsmark__Virkesforrad/PS_Virkesf_tradbiom_b_tab.px
4. SLU, Taxwebb och nedladdningsbara analysfiler: https://www.slu.se/om-slu/organisation/institutioner/skoglig-resurshushallning/miljoanalys/riksskogstaxeringen/vara-data/taxwebb/
5. SLU, metadata för ytdata och urvalsbegränsningar: https://www.slu.se/miljoanalys/statistik-och-miljodata/miljodatakatalogen/riksskogstaxeringens-ytdata/
6. SLU, tillgängliga dataset/skräd­darsydda mikrodatautplock: https://www.slu.se/om-slu/organisation/institutioner/skoglig-resurshushallning/miljoanalys/riksskogstaxeringen/vara-data/
7. SLU, metadata för statistiken: https://www.slu.se/miljoanalys/statistik-och-miljodata/miljodatakatalogen/riksskogstaxeringens-statistik/

## 2. Först krävs en jämförbar mätstorhet

För **varje rasterår** (2000, 2005, 2010, 2015, 2018) ska följande dokumenteras innan jämförelse:

1. Biomassakomponent: ovanjordisk levande biomassa? stam+bark? grenar+barr? totalt inklusive stubbar/rötter? Stående död ved? Värdet 'biomassa' räcker inte som definition.
2. Fysisk enhet och konvertering: kg/ha, ton TS/ha, kg/cell etc.; verifiera mot rastermetadata och originaldokumentation, inte bara filnamn.
3. Referensår och tidsfönster: ett fjärranalysraster med nominellt årtal får inte okritiskt likställas med ett femårsmedelvärde från fältinventering.
4. Markdefinition: NMD2018 skog och *produktiv skogsmark* enligt Riksskogstaxeringen är **inte identiska**; dokumentera skillnaderna och välj antingen strikt jämförbar delpopulation eller ny lämplig geodatamask.
5. Geografisk nivå: Luleå kommuns 25-metersraster ska inte direkt divideras med Norrbottens länsvärde. För validering på länsnivå krävs en **separat länsvis rasteranalys med samma definitioner**, raster-CRS och markmask, eller en giltig och dokumenterad urvalskorrigering.

## 3. Första möjliga faktiska referenskontroller

**A. Länstrend:** Hämta länsvis femårsmedel för biomassans torrvikt runt 2018 från PxWeb tabell 3.29b (2016 och senare) och 2010-kandidater från Taxwebb. Redovisa det centrala mätåret, tidsfönstret, biomassafraktion och medelfel. Kontrollera särskilt om 2010–2018 länstrenden rimligen kan förklara stor kommunal modellnedgång. Denna jämförelse är *indirekt*.

**B. Virkesförråd:** Kontrollera om 2010 års modellerade TOTALVOL (på harmoniserad mask) avviker i riktning/storlek från SLU:s uppmätta länstrend för samma period. Kräver enheter och arealkriterier. Att 2010 har högt virkesförråd kan inte ensamt validera biomassaskattningen.

**C. Provyta/modell:** Utred om offentlig tillfällig provytedata kan kopplas till rasterceller med tillräckligt precis och tillståndsenlig geolokalisering. Respektera SLU:s varning för användning som områdestotal. Testa prediktionsfel och årsmismatch på *oberoende ytor*; undvik samma provytor som användes när någon av modellerna byggdes.

**D. Behöver länstrend omräknas till Luleå?** Endast efter explicit modell för stratifiering och med osäkerhet. Kommunandel av länet är inte fast över tid; extrapolera inte länstrend som korrektionsfaktor utan ytterligare belägg.

## 4. Beslutskriterier innan ett ändrat kolförråd publiceras

- **Ingen korrigering:** Om komponenter, geografi eller referensdata inte matchar. Behåll originalserien och den redan publicerade jämförbara gemensamma-mask-serien.
- **Diagnostisk modellharmonisering (tillåten nu):** Korrigera endast kända *tekniska* jämförbarhetsproblem (NoData, gemensam mask, CRS, felaktiga summor eller komponentdefinitioner som kan transformeras exakt). Märk separat och förvara original och revisionsspår.
- **Scenariokurva (möjlig efter explicit antagande):** Publicera hypotetisk 2010-justering med synliga antaganden och utan att kalla den observerat eller sanningskalibrerat kolförråd. Om inga rimliga bounds finns: publicera inte ett skenprecist procentvärde.
- **Fältkalibrerad 2010-korrigering (ej verifierad):** Kräver tillräckligt oberoende fältdata, tids- och arealkonsistens, test av systematiskt fel, oberoende utvärdering, metod för verklig tillväxt/avgång och osäkerhetsintervall.
- **Fältkalibrering av samtliga år:** Kräver separat validering av varje modellgeneration eller en ommodellering med gemensam definition och referens. En justeringsfaktor för 2010 får inte automatiskt kopieras till 2000/2005/2015/2018.

## 5. Vad inventeringen INTE verifierat

- Ingen numerisk länsvis biomassaserie för 2010–2018 har ännu hämtats, justerats till samma biomassafraktion och kontrollerats mot Luleås raster.
- Ingen fältbaserad korrigeringskoefficient eller osäkerhetsintervall har skattats.
- Det finns ingen bevisad faktisk biomassaminskning på gemensamma celler enbart för att modell 2018 ger lägre ton TS än modell 2010.

**Slutsats:** Det finns etablerade, auktoritativa externa referenskällor för fortsättningen. Däremot kan vi ännu inte besvara exakt hur stor del av 2010 års överskott som är modellfel och därför **inte** publicera 'korrigerad biomassa 2010' som verifierad sanning.
