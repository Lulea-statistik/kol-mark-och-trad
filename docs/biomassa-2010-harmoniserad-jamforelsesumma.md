# 2010 års biomassa: dekomponering och harmoniserbar jämförelsesumma

## Resultat på gemensam rasterpopulation
Underlaget är den befintliga verifierade analysen `metadata/nmd2018_landcover_biomass_volume.json`: samma **2 456 410** giltiga celler för 2010, 2015 och 2018 i ett **fullständigt omprojicerat EPSG:3006, 25m-grid**. 2010 års källraster har verifierat EPSG:3021 25m, 2015 EPSG:3006 12,5m och 2018 EPSG:3006 10m. NMD2018 original 10m, EPSG:3006.

Alla summor nedan är **råvärdessummor över pixlar**, inte ton biomassa, ton kol, ton CO2, total kommunbiomassa eller jämförbara fysikaliska lager. Värdena är inte ännu vetenskapligt harmoniserade mellan biomassamodellernas komponenter och enheter. Man får **inte** multiplicera med 0,0625 hektar och presentera ton utan dokumentation att respektive raster uttrycks i exempelvis ton/ha för jämförbara träddelar.

### Tre nivåer av jämförbarhet (råvärdessummor, ej fysiska totalsummor)

| Nivå | Definition | Celler | Areal, ha | Råsumma 2010 | Råsumma 2015 | Råsumma 2018 |
|---|---|---:|---:|---:|---:|---:|
| A: alla gemensamt giltiga | Samma analysceller med data alla tre år | 2 456 410 | 153 525,625 | ca 188 867 036 | ca 159 009 658 | ca 170 300 694 |
| B: utan NMD2018-vatten | Som A men ta bort klass 61,62 | 2 430 589 | 151 911,813 | Beräknas exakt av workflow | Beräknas exakt | Beräknas exakt |
| **C: endast NMD2018-skog** | Samma skogsmask, NMD 111–117 och 121–127, temporärt ej skog exkluderas | **1 705 502** | **106 593,875** | **ca 150 823 037** | **ca 139 072 470** | **ca 150 389 133** |

**C är rekommenderat första harmoniserade jämförelsevärde för 2010** och ska visas tillsammans med exakt motsvarande 2015 och 2018, med obligatorisk etikett `Jämförbar skogsmark enligt NMD2018 – råvärdessumma, gemensamt giltiga celler`. Det är **inte** ett korrigerat kommunövergripande kolförråd eller en omräkning av 2010 års originalbiomassa. Att begränsa ytan kan reducera en del av selektionsproblemet, men också dölja förändringar genom avverkning och återväxt.

### Bidrag till nettoskillnaden 2010–2018 (deskriptivt, ej orsaksandelar)

Analysen summerar *fasta NMD2018-markklasser* på identiska celler. Om den totala råvärdesskillnaden är cirka **18 566 343**, blir fördelningen:
- Temporärt ej skog: **+10 430 210** råvärdesenheter, ca 56,2 % av nettoöverskottet.
- Vatten: **+2 773 444**, ca 14,9 %.
- Öppen våtmark: **+2 202 926**, ca 11,9 %.
- Övrig öppen mark: **+1 980 960**, ca 10,7 %.
- Skog utanför våtmark: **+1 529 875**, ca 8,2 %.
- Exploaterad mark: **+463 406**, ca 2,5 %.
- Åkermark: **+281 492**, ca 1,5 %.
- Skog på våtmark: **−1 095 971**, ca −5,9 %.

Klasserna summerar till nettoskillnaden, även när en delkomponent är negativ. Dessa procentsatser **är inte andelar av kausala orsaker**. Den största posten `Temporärt ej skog` är NMD:s klassificering **år 2018** och kan representera nylig avverkning, föryngring, olika biomassakomponenter eller modellfel. Det bevisar inte att 56 % av överskottet 2010 orsakades av avverkningar.

### Nästa steg före en fysisk korrigerad totalsumma 2010
1. **Enhet och biomassadefinition** måste kontrolleras i originalmetadata för samtliga årsmodeller: enheter, ovanjordisk/träd- eller bladkomponent, torrvikt eller kol, hektarbas, 2010 års volymkartering och använda skogsdefinitioner. Källornas årtal får inte misstas för ett gemensamt inventeringsår.
2. Använd lokalt licensierad **SMD2000-geometri** för att särskilja skog i både SMD2000 och NMD2018, möjlig förändring och markslag som redan var vatten 2000. SMD2000 är generaliserat och har felklassning; minst två tidslager kan inte säkert avgöra verklig mark 2010.
3. Kvalitetskontrollera `Temporärt ej skog`, som står för största bidraget, med historiska avverkningar, ålder och trädslag – **utan att anta att biomassan 2010 automatiskt ska korrigeras nedåt**.
4. Rapportera 2010 som **originalsumma, arealharmoniserad skogsreferens och en explicit scenariojusterad summa** endast efter kontroller av metod och fysisk enhet; dessutom ett intervall och hur mycket varje justeringsregel bidrar. Interpolera inte NoData med noll.
5. Följ separat både den gemensamma geografiska ytan och hela kommunens täckning. En forest-only-referens är inte likvärdig med `biomassa i Luleå kommun`.

## Reproducerbar metod
`scripts/decompose_harmonize_biomass2010.py` läser **befintligt** JSON-underlag från NMD/biomassaflödet, grupperar NMD-klasserna i fyra disjunkta kategorier, multiplicerar gruppmedelvärde med antalet faktiska giltiga celler, och kontrollerar att summor och cellantal avstäms mot originalanalysen och `forest_only_NMD2018_reference`. JSON sparas i `metadata/biomass2010_harmonized_comparison.json` som en GitHub Actions-artifakt.

Ingen källrasterfil ändras. Inget licensierat SMD2000-underlag publiceras i denna PR. Skriptet använder inte någon volym→biomassaomvandling och tar inte fram en påstått verifierad totalsumma i ton kol.
