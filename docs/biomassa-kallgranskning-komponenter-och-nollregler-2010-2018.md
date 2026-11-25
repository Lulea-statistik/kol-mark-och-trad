# Biomassakomponenter och modellers nollregler: jämförelse 2010–2015–2018

## Resultat från originaldokumentation, 25 november 2026

Nu är **ton torrsubstans per hektar** bekräftat för de tre ingående produkterna och 2010-lagret har dessutom ett **direkt expertutlåtande från SLU för exakt rasterfil** `BIOMASS_XX_P_10.tif`. Rasterdata är fortfarande *modellskattningar* och får inte ses som fältobservationer av årlig skogstillväxt.

| Egenskap | 2010 Skogskarta | 2015 Skogskarta `Biomass_leaf.tif` | 2018 SGD2 `SGD2_BIO.tif` |
|---|---|---|---|
| Enhet | ton TS/ha | ton TS/ha | ton TS/ha |
| Stamved, grenar, toppar | Ingår (ovanför stubbskär) | Ingår | Ingår |
| Stubbar och rötter | Ingår inte | Ingår inte | Ingår inte |
| Barr på barrträd | **Ingår, uttryckligen bekräftat av SLU** | Ej specificerat i aktuell produktbeskrivning | Ej specificerat i aktuell produktbeskrivning |
| Löv på lövträd | **Ingår inte, uttryckligen bekräftat av SLU** | Ej specificerat i aktuell produktbeskrivning | Ej specificerat i aktuell produktbeskrivning |
| Modellnoll vid höjd <3 m | Ej verifierat likvärdig regel | **Ja**, värden nollställs | **Ja**, produktbeskrivningen anger nollställning |
| Grundläggande data | SLU äldre skogskarta | Riksskogstaxeringen + flygbildsytmodeller + Sentinel-2 | Riksskogstaxeringen + nationella laserskanningen |

### Exakt dokumentation

1. **2010:** SLU:s Mats bekräftade i e-post som användaren återgav 2026-11-25: exakt `BIOMASS_XX_P_10.tif` mäter ton TS/ha, hela trädets massa ovan stubbskär inklusive grenar, barr ingår för barrträd, medan löv på lövträd inte ingår. Marklund, L.G. (1988), *Biomassafunktioner för tall, gran och björk i Sverige*, SLU Rapport 45. Källspecifik e-post, inte allmänt publicerad produktbeskrivning.
2. **2015:** [SLU Skogskarta 2015 produktbeskrivning, s. 3](https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/raster-slu-skogskarta---produktbeskrivning.pdf) beskriver biomassa som stamved, grenar och toppar i ton TS/ha, exklusive stubbar och rötter; nollställning när grundytevägd medelhöjd understiger 3m. **Ingen uttrycklig regel om barr och löv** anges.
3. **2015, exakt fil:** [Wallerman och Nilsson (2019), utvärdering `EvaluateSLUSkogskarta.pdf`](https://gis.slu.se/data/slu_forest_map/2015/docs/EvaluateSLUSkogskarta.pdf), sektion *Total biomassa (ovan jord)* kopplar `Biomass_leaf` till variabeln `BiomassAbo`. Filnamnets 'leaf' innebär inte att endast lövbiomassa mäts.
4. **2018, omdrev 2:** [Skogliga grunddata produktbeskrivning, 2022-07-01, s. 3](https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/skogliga-grunddata/skogliga-grunddata-220701---produktbeskrivning.pdf) anger stamved, grenar och toppar i ton TS/ha, exklusive stubbar och rötter. Beskriver också nollvärden vid höjd under 3 m samt att laserdatum varierar geografiskt. **Ingen uttrycklig regel om barr och löv** anges. Produktens dokumenterade upplösning i denna äldre generella beskrivning är 12,5 m, medan det faktiska arkiverade `SGD2_BIO.tif` är **10 m**, verifierat av projektets rasterproveniens. Det är därför extra viktigt att få den **exakta SGD2-varianten** bekräftad, inte extrapolera från en annan produktgeneration.

## Skillnader som sannolikt har betydelse för trendtolkningen

- **Fysikaliska delkomponenter:** Stammassa plus grenar och toppar och exkludering av rötter/stubbar är gemensamt dokumenterat. Men vi kan **inte** anta att 2015 och 2018 behandlar barr och löv exakt som SLU 2010. Inga procentuella justeringsfaktorer kan källförankras ännu.
- **Skogshöjd och nollvärden:** En 3m-tröskel i 2015 och SGD skapar verkliga *modellnollor* i ung skog, även där biomassa faktiskt finns. Om 2010 års raster använder andra höjd- eller maskregler kan hela områden visas med högre 2010-biomassa utan att träden faktiskt avverkats.
- **Sensorer:** SLU 2015 använder bildmatchning/Sentinel-2; SGD 2018 laserskanning. En skillnad som återfinns även i icke avverkad skog kan bero på modellmetod, fenologi och tidsläge.
- **Årtal:** 2015-bilderna kan representera olika fotograferingstillfällen (produktbeskrivningen anger 2014–2016); SGD omdrev-2 är daterat 2018 i Luleå enligt projektets separata skanningskontroll. Exakt biologisk tillväxt per kalenderår får inte utläsas direkt.

## Praktisk konsekvens för projektets siffror

De verifierade referenssummorna från PR #109 i **ton TS** på gemensamt giltiga 25m-celler i **EPSG:3006** kan fortsatt redovisas separat per år och markmask. Skillnaderna (till exempel −0,29 % för NMD2018-skog och −14,98 % för 2010 volym≥50) är fortfarande **kvoter mellan olika modeller** för samma rasterceller, inte en metodharmoniserad förändring av fältobserverad biomassa.

### Nästa avgörande uppgifter

Begär gärna en **kompletterande bekräftelse av SLU** för exakt `Biomass_leaf.tif` 2015 och `SGD2_BIO.tif` 2018:
- Ingår **barr för barrträd**, och exkluderas **löv för lövträd**, i båda produkternas biomassa?
- Vilka biomassa­funktioner eller variabeldefinitioner gäller respektive fil, och bygger båda på **Marklund 1988** eller andra funktioner?
- Vilken höjd- och maskregel gäller i 2010 års exakt `BIOMASS_XX_P_10.tif` jämfört med 2015/SGD2:s gräns 3 m?
- Finns någon viktig produktgenerationsskillnad (SGD2 exakt 10m kontra 2022 års generella dokumentation) som påverkar biomassadefinitionen?

Mask för historisk skog och klassning av registrerade avverkningar behöver fortsatt kontrolleras separat. Ingen automatisk "modellkorrigering" får maskera verklig avverkning.

## Reproducerbar evidens

`scripts/audit_biomass_component_comparability.py` och `.github/workflows/audit-biomass-component-comparability.yml` skriver en kompakt maskinläsbar källmatris med explicit *okänd* barr-/lövstatus 2015 och 2018, kända nollregler och enhet samt en spärr mot påståenden om verifierad fysisk ändringsprocent. Inga källraster ändras.
