# Registrerad avverkning 2011–2018 på NMD2018 temporärt ej skog (118 och 128)

Syftet är att testa PR #101:s dominerande råvärdesavvikelse på **exakt samma 469 240 rasterceller** (29 327,5 ha) för vilka biomassan 2010, 2015 och 2018 är gemensamt giltig. Av dessa har **119 269 celler** modellerad virkesvolym 2010 >=100. De står tillsammans för cirka 11,98 miljoner råvärdesenheters skillnad mellan 2010 och 2018, jämfört med nettoöverskottet **10,43 miljoner** inom NMD118/128.

## Metod

- Biomassta från tre originalraster, 2010 ursprung EPSG:3021 25m, 2015 EPSG:3006 12,5m och 2018 EPSG:3006 10m.
- Ursprunglig NMD2018 **basprodukt** EPSG:3006 10m används med kategorier **118 och 128** (inte produktivitetsklass 0).
- Samtliga biomassaraster och 2010 års volym omprojiceras i sin helhet till projektets identiska 25m EPSG:3006-grid före överläggningen. NMD2018 bas raster resamplas kategoriskt (nearest).
- Skogsstyrelsens daterade avverkningspolygoner hämtas via spatial fråga för Luleå; datumfältet **Avvdatum** används, inte anmälningsdatum/ärendeår, och geometrin begärs ut i EPSG:4326 och transformeras till EPSG:3006 för rasterisering.
- Avverkningsperioder: **2011–2015**, **2016–2018**, **båda perioder**, samt **ingen registrerad avverkning**. Överlappande perioder särredovisas utan dubbelräkning.
- För varje avverkningsklass redovisas cellantal och biomassaråsumma 2010/2015/2018, samt nettoförändringen. Två volymskikt redovisas: **2010-volym minst 100** och **2010-volym under 100**. Saknad volym redovisas separat.
- Kontrollvillkor kräver samma 469 240 och 119 269 celler som PR #101 och samma rånettoskillnad (cirka 10 430 210). Om underlag eller programförändringar bryter avstämningen avbryts publiceringen.

## Vad resultatet kan respektive inte kan visa

Registrerad avverkning 2011–2018 som överlappar celler med stor 2010–2018-biomassaskillnad **stödjer förenlighet med en verklig skogsförändring**. Överlapp bevisar varken att 2010-rastret var korrekt eller att all observerad biomassaförlust orsakades av avverkningen. Avverkningsregistret är **inte fullständigt**; frånvaro av avverkningspolygon är inte säker ingen avverkning. År 2018 kan skanningsdatum och avverkningsdatum korsa varandra, varför vissa avverkningar registrerade 2018 kan ha inträffat efter laserskanningen. Underlagets tidsstämpel och innehåll måste därför beaktas i tolkningen.

Denna analys ger *deskriptiva bidragsandelar*, inte en säker kausal procentfördelning. Den ändrar **inte** 2010 års originalbiomassa eller producerar ton torrsubstans: PR #100:s källspecifika spärr gäller fortfarande.

Kod: `scripts/diagnose_nmd118_128_dated_harvest.py`. Arbetsflöde: `.github/workflows/diagnose-nmd118-128-harvest.yml`. Resultatfil: `metadata/nmd2018_temporary_not_forest_harvest_2011_2018.json` som 90-dagars GitHub Actions-artefakt.
