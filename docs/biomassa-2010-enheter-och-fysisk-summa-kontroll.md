# Kontroll av fysiska biomassavärden efter PR #99

## Källgranskning: vad kan uttryckas i ton torrsubstans?
Produktdokumenten är källor för **produktdefinitionen**, inte verifierade enhetsmetadata inbäddade i våra tre arkiverade rasterfiler.

| Referenslager | Enhet | Träddelar | Dokumentationsstatus |
|---|---|---|---|
| SLU Skogskarta 2010 | **Ej dokumenterat säkert för det exakta källrastret** | Ej slutligt verifierat | **Ingen fysisk 2010-tonsumma publiceras** |
| SLU Skogskarta 2015 | ton TS/ha | Stamved, grenar, toppar; ej stubbar eller rötter | Produktbeskrivning Skogsstyrelsen/SLU 2021-01-12, sidan 3 |
| Skogliga grunddata omdrev 2, Luleå skannat 2018 | ton TS/ha | Stamved, grenar, toppar; ej stubbar eller rötter | Produktbeskrivning Skogsstyrelsen/SLU 2022-07-01, sidan 3 |

Verifierbara källor:
- 2015: https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/raster-slu-skogskarta---produktbeskrivning.pdf
- 2018: https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/skogliga-grunddata/skogliga-grunddata-220701---produktbeskrivning.pdf
- Översikt 2010: https://www.slu.se/miljoanalys/statistik-och-miljodata/miljodatakatalogen/slu-skogskarta/

Dessa dokument förklarar också varför jämförelsen inte får göras mekaniskt: 2010 års SLU Skogskarta baserades på Landsat/SPOT och 25m-celler. 2015 års Skogskarta kombinerade Sentinel-2 med flygbildsbaserade ytmodeller (12,5m) och satte **höjd under 3 meter till noll**. Skogliga grunddata omdrev 2 baseras på laserskanning 2018–2025 (lokal Luleå-årgång tidigare verifierad till 2018), med en liknande 3m-höjdgräns och 10m-celler. Skillnader i metoder och modellmasker kan bli särskilt viktiga på nyavverkad mark/ungskog.

## Arealharmoniserad skogsreferens och dess fysisk-enhetsspärr

Gemensam mask i EPSG:3006 med 25m analysraster, **1 705 502 celler × 0,0625 ha = 106 593,875 ha**. Alla tre års värden summeras på samma platser där alla raster har giltiga data; fasta skogsklasser enligt **NMD2018**, inte bevisad skog år 2010.

| År | Pixelråsumma | Villkorlig tTS-summa (råsumma × 0,0625 ha) | Status |
|---|---:|---:|---|
| 2010 | 150 823 037 | **9 426 440 om antagen tTS/ha** | **Ej verifierbar som fysisk massa för 2010** |
| 2015 | 139 072 470 | **8 692 029** | Villkorlig fysisk ton TS, dokumenterad produktdefinition men arkivproveniens behöver slutverifieras |
| 2018 | 150 389 133 | **9 399 321** | Villkorlig fysisk ton TS, dokumenterad produktdefinition men arkivproveniens behöver slutverifieras |

**Viktig distinktion:** Raden 2010:s 9,43 miljoner ton TS är **endast en räkneövning med en antagen enhet**, inte ett verifierat värde att publicera som tTS. Den är inte en kalibrering och inte ett mått för hela Luleå. Inget av dessa alternativ är kolförråd eller CO2e utan ytterligare separat konvertering med verifierad kolandel och träddelsomfattning.

Källdokumentation stöder dessutom att rasterprodukterna är **modellskattningar**, inte oberoende uppmätt biomassaförråd per cell. Nollreglerna för kort skog kan skapa metodberoende bias mot 2010.

## Reproducerbar kod och kontroller

`scripts/audit_biomass_units_and_mass_gate.py` läser den godkända PR #99-serien från `metadata/biomass2010_harmonized_comparison.json`, beräknar kandidatmassor med dokumenterade enheter för 2015 och 2018, och sätter den faktiska 2010-massan till `null` med status `BLOCKED_2010_SOURCE_SPECIFIC_UNIT_OR_COMPARTMENT_UNCONFIRMED`. Ett hypotetiskt räkneexempel exponeras bara under ett särskilt icke-publicerbart fält. GitHub Actions validerar uttryckligen att detta villkor inte kan gå förlorat.

För att låsa upp 2010 fysiskt krävs:
1. Hitta **metadata eller metodbeskrivning för det exakt använda SLU Skogskarta 2010 Biomassa-rastret**: värdeenhet, skalning och träddelar.
2. Kontroller mot `lulea_biomass_2010_provenance.json` och motsvarande för 2015/2018: verklig filidentitet, nedladdningskälla, rasterbandets eventuella skalning/offset.
3. Utvärdera 2010-skog i historiskt stabila bestånd (SMD2000-skogsmark + NMD2018-skogsmark) och den dominerande NMD2018-kategorin **temporärt ej skog** mot dokumenterade avverkningar. Redovisa andel av nettoskillnad separat från orsak.
4. Skilj ut **strikt gemensamt skogsurval**, **hela kommunens täckning**, samt scenariostyrd korrigering. Den första är inte samma sak som den sista.

## Försiktighetsprincip
Ingen ursprunglig pixel korrigeras, inga licensierade SMD2000-geometrier eller derivat publiceras och inga modelljusteringar görs för att pressa 2010 till samma värde som 2018.
