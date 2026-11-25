# Ton torrsubstans per gemensamt rasterurval 2010, 2015 och 2018

## Källbekräftelse och status

SLU har den **25 november 2026** skriftligen bekräftat för **exakt raster `BIOMASS_XX_P_10.tif`** att enheten är **ton torrsubstans per hektar (ton TS/ha)**. Trädet mäts ovan stubbskär inklusive grenar. För barrträd ingår barren men löv på lövträd ingår inte. Stubbar och rötter ingår inte. Källa: direkt e-postsvar från SLU:s Mats, tillhandahållet av projektägaren; metodhänvisning Marklund, L.G. (1988), SLU Rapport 45.

2015 års `Biomass_leaf.tif` och 2018 års `SGD2_BIO.tif` har i projektet sedan tidigare stöd för **ton TS/ha** och ovanjordisk biomassa. Deras exakta blad-/barrkomponenter, modellmetoder och nollregler är däremot **inte bekräftat identiska** med 2010. Treårsändring får därför inte kallas metodharmoniserad eller fältobserverad.

## Arealsummerade modellskattningar

Tidigare giltighetskontroller i PR #99 och #105 har verifierat samma treårspopulation efter **fullständig rasterreprojicering** till **EPSG:3006, 25m**. Original-CRS 2010 = EPSG:3021 och 2015/2018 = EPSG:3006. För varje giltig jämförelsecell multipliceras det källstödda rastervärdet i **ton TS/ha med 0,0625 hektar**. Dessa tal är åren var för sig modellskattade *ton torrmassa inom just den valda masken*.

| Samma geografiska mask (referens) | Celler | ha | 2010 miljoner ton TS | 2015 miljoner ton TS | 2018 miljoner ton TS |
|---|---:|---:|---:|---:|---:|
| Alla tre åren giltiga (NMD2018-märkt) | 2 456 410 | 153 525,625 | 11,8042 | 9,9381 | 10,6438 |
| Endast NMD2018-skog, ej temporärt avverkat | 1 705 502 | 106 593,875 | 9,4264 | 8,6920 | 9,3993 |
| 2010 års volym≥50, behåll även 2018-ej-skog | 1 897 060 | 118 566,25 | 11,1718 | 9,0103 | 9,4978 |

Rastret är **inte en inventerad total för Luleå kommun**: urvalen kräver att alla tre biomassalager är giltiga och representerar projektets arbetsgräns; historisk skogsklassning är inte verifierad. Det är ingen skattning av kol eller CO2. 2010 års 25m-grid och jämförelsegridden hanteras med CRS- och NoData-kontroller, och ingen avverkad 2010-skog justeras bort automatiskt.

## Vad maskvalet betyder

NMD2018-skog ger cirka **−0,29 %** i förhållandet mellan 2018 och 2010 års modellerade biomassa inom samma 2018-skogsmark. Om vi i stället behåller 2010 års modellerat virkesrika celler (volym≥50), även där 2018 års markklass inte är skog, blir förhållandet cirka **−14,98 %**. Detta är en skillnad i *maskdefinierat modellförhållande*, inte två oberoende skattningar av samma verkliga skogsförändring. Den historiska 2010-masken kan innehålla falskt skogsklassat vatten och felaktiga modellvärden.

## Nästa kontroller

1. Verifiera explicit blad-, barr-, modell- och höjdtröskeldefinition för 2015 och 2018 mot SLU/Skogsstyrelsen, inklusive eventuell användning av samma Marklund-funktioner.
2. Utför den redan förberedda privata **SMD2000-överläggningen** (PR #106–107) mot den fullständiga 2010-masken, utan att publicera licensierad geometri.
3. Redovisa vatten och registrerade avverkningar separat; ersätt aldrig registrerad avverkning med godtycklig nedjustering av 2010-värden.
4. Gör därefter en genomlyst bestånds- och modelljämförelse på gemensamma markceller. Observera att SMD2000 är generaliserad kartläggning av ca år 2000, inte observerad skog 2010.

*De tabellerade talens cellantal och råsummor avser verifierade tidigare rasterkörningar. PR #109 ändrar beräkningarnas enhetsmärkning och kontrollkedja, inte originalraster eller den tidigare populationen.*
