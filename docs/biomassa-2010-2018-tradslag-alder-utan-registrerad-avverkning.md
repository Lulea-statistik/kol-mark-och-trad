# Biomassajämförelse på samma celler: trädslag, beståndsålder och registrerad avverkning

## Fråga

Håller den högre modellerade biomassan 2010 jämfört med 2015/2018 i Luleå även inom **skogsmark utan registrerad avverkning**? Finns olika mönster i tall-, gran- respektive lövdominerade 2010-bestånd och olika åldrar?

Den tidigare 2010-volymmasken gav cirka **−15 %** mellan 2010 och 2018 när exakt samma 25m-celler följs. Detta är en kvot av **olika modellprodukter** och beror starkt på maskval. En mask med skog enligt NMD2018 ger i stället cirka **−0,29 %**. Skillnaden är inte i sig evidens för faktisk tillväxt/förlust.

## Ny rasterbaserad jämförelse

`scripts/compare_biomass_species_age_harvest_2010_2018.py` hämtar verifierad 2010-volym, biomassa 2010/2015/2018 och modellerad **beståndsålder 2010** från tidigare arkiverade GitHub Releases samt original-2010 trädslagsvolymer `PINEVOL_XX_P_10.tif`, `SPRUCEVOL_XX_P_10.tif` och `DECIDUOUSVOL_XX_P_10.tif` från SLU. Skogsstyrelsens **daterade avverkningspolygoner 2011–2018** hämtas från samma REST-tjänst som i projektets tidigare avverkningsanalyser. Original-NMD2018 kommer från Naturvårdsverket.

Källdata kontrolleras för:
- Original-CRS **EPSG:3021, 25m** för 2010 biomassa, ålder, volym och trädslagsvolym.
- Original-CRS **EPSG:3006, 12,5m** för 2015 biomassa.
- Original-CRS **EPSG:3006, 10m** för 2018 SGD2-biomassa och NMD2018.
- Avverkningspolygoner levereras via REST med efterfrågad EPSG:4326 och transformeras till verifierat arbetsgrid **EPSG:3006**.
- Fullständig omprojicering av rastergridden till **EPSG:3006, 25m**; aldrig enbart transformerade rasterhörn. **NoData exkluderas**, inte ersätts med noll.

Ingen GeoPandas används.

### Urval och jämförelsegrupper

Två parallella geografiska masker, alltid identiska celler mellan 2010 och 2018:

1. **Skog enligt NMD2018**. Uppvisar överlevande skog 2018 men kan introducera efterhandsurval som exkluderar avverkad 2010-skog.
2. **2010-modellerad volym ≥50**. Inkluderar även senare avverkad skog men kan felklassificera vatten och annan mark.

Inom varje mask redovisas:
- **Inga avverkningar registrerade 2011–2018** (inte samma sak som bevisat oavverkad).
- **Överlapp med registrerad avverkning 2011–2018** (förklarande strata, inga värden justeras).
- 2010-dominerande **tall**, **gran**, **löv**, **blandskog** och **oklassad**.
- Beståndsålder enligt 2010-modellen: **0–19**, **20–39**, **40–59**, **60–79**, **80–99**, **100–139**, **140–499 år**; eventuella värden ≥500 redovisas enbart i totalgruppen och flaggas i valideringen.

Dominans definieras som minst **60 %** av modellerad trädslagsvolym för tall, gran respektive `DECIDUOUSVOL`. Volymsumman måste ligga inom **20 %** av total 2010-modellvolym och volym ≥20. I stället för att lägga ihop björk och löv, vilket kan innebära dubbelräkning, används här bara `DECIDUOUSVOL`; dess exakta relation till `BIRCHVOL` kräver fortfarande källgranskning. Om komponenterna inte avstämmer klassas cellen **oklassad**, inte som löv- eller barrskog.

### Mått

- Antal jämförbara celler och hektar per grupp.
- Modellerad ton torrsubstans för 2010, 2015 och 2018, med SLU:s bekräftade 2010-enhet och cellarean **0,0625 ha**.
- Medelvärde ton TS/ha, modellkvoter 2015/2010 och 2018/2010 och andel celler med lägre 2015-värde än 2010.
- Medelvolym och medelålder enligt respektive **2010-modellskikt**.

Alla summor av kontrollerade trädslagsgrupper ska avstämmas exakt mot överordnad mask, utan dubbelräkning. Skattad **verklig biomassaförändring** är uttryckligen `null`, inte likställd med modellkvoten.

## Hur resultaten ska tolkas

Korsningen är värdefull för att se om 2010:s höga nivåer är ett **generellt mönster bland äldre barrdominerad skog utan registrerad avverkning** eller främst knutna till modellerad 2010-skog som inte är skog enligt NMD2018. Den **kan inte** isolera SLU:s 2010-modellbias eller ett specifikt fel från SGD2:s lövade laserskanning. Projektets tidigare analys visar att **alla 540 dokumenterade SGD2-indexrutor i Luleå 2018 är märkta `Lov_Avlov = 1`**, så någon lokal avlövad kontrollgrupp saknas.

De historiska ålders- och trädslagslagren är också SLU-modeller och inte oberoende fältkontroller. Små och/eller oregistrerade avverkningar kan förekomma, och NMD2018-maskens användning kan selektera bort faktisk förlust mellan 2010 och 2018.

**Status:** PR innehåller reproducerbar rasterkod och GitHub Actions-arbetsflöde. Siffror i ton TS per trädslags- och åldersgrupp ska inte skrivas in här förrän den verkliga rasterkörningen är godkänd och rapportfilen granskas. Inga ursprungliga biomassaraster har ändrats.
