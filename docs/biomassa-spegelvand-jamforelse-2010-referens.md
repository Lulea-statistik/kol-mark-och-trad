# Spegelvänd biomassajämförelse: referens 2010, följ samma celler till 2018

## Frågeställning

Tidigare PR #99 analyserade **samma pixelpopulation** 2010/2015/2018 på en fast **2018 års NMD-skogsmask**: 1 705 502 celler (106 594 ha), råsummor 150,82 miljoner 2010 och 150,39 miljoner 2018 (−0,29 %). Den jämförelsen kan dölja avverkad skog eftersom områden som 2018 klassas som temporärt ej skog utesluts.

Vi vänder på urvalet: **definiera en historisk 2010-proxy utifrån 2010 års modellerade virkesvolym** och följ biomassan på samma celler 2010 → 2015 → 2018 utan att exkludera celler som 2018 upphör att vara skog. Jämför sedan med originalreferensen.

## Kritiskt metodval

Projektet har **inte ett komplett verifierat NMD2010-landtäckesraster**. SLU Skogskarta 2010:s virkesvolym är ett **modellresultat**, inte en oberoende observerad skogsmask från 2010. Vi får därför inte presentera det som ”skogsområden enligt NMD2010”.

För transparent känslighet används fyra fasta **2010-volymurval**: >0, ≥10, ≥50 och ≥100 i volymrastrets eget råvärde. Detta definierar inte en officiell skogsmarksgräns. Höga gränser missar ungskog och lågproduktiv skog medan låga gränser riskerar inkludera modellerad virkesvolym i vatten och hårdgjord mark. Gränsvärdet 50 används som primär visningsproxy, och 10/100 visar urvalseffekten.

## Reproducerbar metod

- 2010 biomassa och virkesvolym: ursprungs-CRS **EPSG:3021**, 25m.
- 2015 biomassa: **EPSG:3006**, 12,5m.
- 2018 biomassa och NMD2018: **EPSG:3006**, 10m.
- Samtliga rastergrid omprojiceras fullt med `WarpedVRT` till **EPSG:3006 25m** innan analys. Värderaster omsamplas med `average`, NMD2018-kategorier med `nearest`.
- Samma **2 456 410** biomassaceller gemensamt giltiga 2010, 2015 och 2018 i Luleå arbetsområde som PR #99. NoData hålls separat från noll. Där 2010-volym är NoData exkluderas cellen endast från volymmasken och registreras särskilt.
- Summerar biomassans **råvärden** i fasta volymurval definierade av **2010**. Därefter korsas varje 2010-urval med **2018 NMD-skog**, **inte skog**, **temporärt ej skog**, och **vatten**. En övergång till temporärt ej skog kan vara förenlig med dokumenterad avverkning 2011–2018 men klassningen är inte en kausal observation.
- Originalets **2018-skogsreferens** finns med som kontroll, och summerade 2010-maskar ska exakt dela sig i 2018-skog + 2018-ej-skog på samma celler.

## Vad resultatet får visa

Rapportera **råvärdessumma 2010/2015/2018, procentuell förändring inom samma cellpopulation, areal och 2018 års markklassning**. Detta svarar på hur uppmätt/modellerad biomassa ändras inom ett urval som definierades 2010 och där avverkade områden inte automatiskt rensas bort.

Det svarar **inte** på exakt hur mycket 2010 års verkliga skog har minskat: 2010-proxyn har modellfel, unga bestånd kan saknas och den gemensamt giltiga masken utesluter annan 2010-mark. 2010 års enhet och träddelsdefinition är fortsatt blockerad av PR #104; resultaten är **inte ton torrsubstans** och inte vetenskapligt enhets- och komponentharmoniserade.

## Kod och kontroll

`scripts/compare_2010_volume_proxy_reverse_biomass.py` och `.github/workflows/reverse-2010-volume-mask-biomass.yml` skapar `metadata/biomass_2010_reference_reverse_2018.json` som Actions-artefakt. Inga originalraster eller publicerade beräkningar modifieras.

### Möjligt nästa steg

För en genuin observerad 2010-landtäckesmask krävs lämplig historisk klassning nära 2010, gärna förenad med historiska ortofoton/avverkningsgeometrier. Det tidigare lokalt licensierade SMD2000-lagret är inte samma sak som 2010 och bör hanteras privat med geografiska och tidsmässiga osäkerheter.
