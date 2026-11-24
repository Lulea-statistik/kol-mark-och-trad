# SLU Riksskogstaxeringen som oberoende länsreferens

Status: **metod- och källregister, ännu ingen numerisk kalibrering**. Syfte är att pröva rimligheten i biomassan och volymtrenden för Luleås gemensamma rasterceller, inte att ersätta rasterdata med länsmedelvärden.

## Verifierade tabellgrupper (kontrollerade 2026-11-24)

Källa: https://skogsstatistik.slu.se/pxweb/sv/OffStat/

| Mått | SLU:s tabell | Omfattning | Avgränsning och kontroll |
| --- | --- | --- | --- |
| Biomassa, torrvikt | 2.13b | Skogsmark, län från 2016 | Kontrollera trädfraktion och skyddad/ej skyddad areal; absolut total är inte ton/ha |
| Biomassa, torrvikt | 3.29b | Produktiv skogsmark, län från 2016 | Föredras när vår analys uttryckligen maskas till produktiv skogsmark; skilj från tabell 2.13b |
| Virkesförråd | 3.21 | m³sk/ha efter beståndsålder | Jämför åldersklasser först efter harmonisering av åldersgränser och arealdefinition |
| Virkesförråd | 3.18a/3.18b | Produktiv skogsmark, trädslag/diameter | 3.18b exkluderar formellt skyddade områden; blanda inte med 3.18a |
| Bonitet | 3.11a/3.11b | Produktiv skogsmark | Bonitet är långsiktig produktionsförmåga, inte uppmätt årsökning av volym |
| Årlig avsatt tillväxt | 3.31a | Produktiv skogsmark, län; 10 000 m³sk eller m³sk/ha | Inklusive tillväxt för avverkade träd; år är ett medelår för ingående tillväxtår, inte ett enskilt års observation |

Källingångar:
- https://skogsstatistik.slu.se/pxweb/sv/OffStat/OffStat__Skogsmark__Virkesforrad/
- https://skogsstatistik.slu.se/pxweb/sv/OffStat/OffStat__ProduktivSkogsmark__Virkesforrad/
- https://skogsstatistik.slu.se/pxweb/sv/OffStat/OffStat__ProduktivSkogsmark__StandortVegetation/
- https://skogsstatistik.slu.se/pxweb/sv/OffStat/OffStat__ProduktivSkogsmark__Tillvaxt/

## Geografisk referens

1. **Norrbottens län** är primär regional kontroll eftersom Luleå ligger där.
2. **Västerbottens län** är jämförelselän; skillnaden visar känslighet men är inte ett automatiskt interpolationssteg.
3. **Västernorrlands och Jämtlands län** är känslighetsreferenser, inte län att väga in utan lokalt belägg.
4. En vägd referens får beräknas först när lokala arealandelar för samma skogsmarksdefinition, trädslag, beståndsålder och bonitetsklass finns verifierade. Vikter ska summera till 1 och dokumenteras. **Ingen gissad länsvikt används.**

## Strikt jämförelse med Luleås rasterserie

- Huvudkurvans **2 316 804 celler × 625 m² = 144 800,25 ha** avser en gemensam *modell- och rastertäckning*, inte verifierad produktiv skogsmark. Detta är inte en lämplig automatisk nämnare för länstabellernas `m³sk/ha` eller `ton torrvikt/ha`.
- För länsjämförelse krävs en verifierad mask för **motsvarande ägoslag**, ålderspopulation och skyddsstatus. Föredra arealviktad intensitet (summa volym/korrekt areal) på den populationen; redovisa täckningsgrad och osäkerhet.
- SLU:s femårsmedelvärden redovisas med **mittenår**, exempelvis 2021–2025 = 2023. Tillväxttabell 3.31a har dessutom en annan referensperiod för ingående tillväxtår; kontrollera fotnoten vid varje uttag.
- Biomassa (ton torrvikt), virkesförråd (m³sk) och bonitet (m³sk/ha/år som produktionskapacitet) är olika variabler. Konvertera inte med okänd generell faktor. Jämför aldrig biomassaråvärden utan verifierad enhet direkt med ton torrvikt/ha.
- PR #70 visar att volymråmedlet på samma celler steg **87,376 → 108,260 (+23,90 %) 2005–2010**. 2005-biomassan är i huvudserien beräknad som 2005-volym × en 2010-kalibrerad faktor. Ökningen är därmed **inte ett oberoende mått på tillväxt**.
- SLU:s länsvisa biomassaserier börjar 2016. De validerar möjliga senare nivåer men kan **inte användas som observerat facit för 2005 eller 2010**.

## Nästa maskinläsbara steg (inte genomfört)

1. Hämta PxWeb CSV/JSON för fyra län, vald tabell, **år, mått, enhet, ägoslag, trädfraktion, skyddsstatus och eventuellt medelfel**. Logga ursprunglig URL, extraktionstid och frågeparametrar.
2. Bygg en lokal verifierad skogsmarksmask och beräkna värden per hektar på identisk population. Kontrollera källraster-CRS och NoData före maskning; rasterreprojektion sker för hela pixelgridet till EPSG:3006 vid analys, och EPSG:3857 vid kartvisning.
3. Redovisa per variabel: Luleå-raster, Norrbotten, Västerbotten samt Jämtland/Västernorrland som känslighet; procentavvikelse och osäkerhet först efter enhetskontroll. Undvik länsviktad kommunskattning utan empirisk motivering.
4. Låt befintlig publicerad rasterkurva vara orörd. Visa först en granskningsrapport och publicera ett utfall när samtliga kontroller passerat.

**Publiceringsspärr:** Inga numeriska länsvärden eller påståenden om kalibrerad Luleå-biomassa får visas förrän uttag och geografiska nämnare har verifierats.
