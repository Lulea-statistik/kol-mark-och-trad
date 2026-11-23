# Prövning av avverkning som förklaring till högre råbiomassa år 2010

**Hypotes:** Om den högre uppskattningen av biomassa 2010 delvis är verklig bör celler inom faktiskt avverkade områden 2011–2015 uppvisa större minskning 2010–2015 än jämförbara celler utanför dessa områden.

## Verifierade källfakta

- Skogsstyrelsens [produktbeskrivning för utförda avverkningar, 2026-01-13](https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/utforda-avverkningar---produktbeskrivning.pdf) beskriver polygoner identifierade genom skillnadsanalys i satellitbilder, med fältet **Avvdatum** för datum för avverkning, **Arendear** för registreringsår, **Arealha** för kartytans areal och **Kalladatum** för datumkälla. Dessa får inte sammanblandas.
- Lagrets publicerade **EPSG:3006** är bekräftat. REST-queryn begär **EPSG:4326** för GeoJSON och varje geometri transformeras därefter faktiskt till EPSG:3006 innan maskning på rastergridet.
- Skogsstyrelsen säger uttryckligen att detekterade avverkningar är ett **vägledande underlag**, inte lämpligt som direkt statistikprodukt. Oanmälda avverkningar och avverkningar under 0,5 ha saknas. Metoden ändrades 2022, efter de undersökta perioderna.
- De arkiverade biomassaklippen 2010/2015/2018 och deras SHA-256 kontrolleras före analys. Ingen omräkning av källraster eller tidigare diagram görs.

## Genomförd implementation

`.github/workflows/biomass-harvest-overlay.yml` kan köras manuellt och vid denna PR. Programmet:

1. Frågar Skogsstyrelsens publika ArcGIS REST-lager om objekt-ID för kommun **2580** och hämtar polygoner i kontrollerade omgångar.
2. Klassificerar på faktiskt angivet avverkningsdatum **2011–2015** och **2016–2018**. Saknat avverkningsdatum blir **okänt**, inte noll avverkning.
3. Skär varje polygon mot projektets arbetsgeometri (inte verifierad officiell kommungräns).
4. Reprojicerar hela biomassarastergridet till EPSG:3006 med **25 m**, **Resampling.average**, och bevarar NoData.
5. Jämför råvärden i gemensamma giltiga celler inom fyra grupper: *ingen registrerad avverkning*, *avverkad 2011–2015*, *avverkad 2016–2018*, *avverkad i båda perioderna*.
6. Redovisar råmedel 2010, 2015, 2018, medelskillnader, andel celler med 2010 över 2015/2018 samt avverkade ytor och källposternas antal.

Inga publika totalsiffror uppdateras innan den empiriska analysen blivit kontrollerad.

## Tolkning

- Avverkning 2011–2015 kan vara en bidragande förklaring om större råvärdesminskning uppträder inom dessa ytor än inom ytor utan registrerad avverkning.
- Detta bevisar **inte** kausalitet. Det senare materialet kan beskriva andra observationsår, produkter och metoder; det kan finnas förväxlingsfaktorer (beståndsålder, skogstyp, bildkvalitet).
- Om även ej registrerat avverkade celler uppvisar betydligt lägre råvärden 2015 tyder det på att avverkning ensam inte förklarar nivåskillnaden. Avsaknad av registrerad avverkning bevisar däremot inte att ingen avverkning skett.
- Extremvärden 2015 (råmaximum **16 007**) kan bidra till medelvärdet, men måste kontrolleras separat. Källornas definitioner/skalning och officiell landmask saknar fortfarande slutlig verifiering.

## Äldre källor 2000 och 2005

SLU:s egna kataloger listar följande **virkesvolym**, inte dokumenterad biomassaraster för respektive år:
- [TOTALVOL_XX_P_00.tif](https://gis.slu.se/data/slu_forest_map/2000/Data/Raster/Rt90/TOTALVOL_XX_P_00.tif)
- [TOTALVOL_XX_P_05.tif](https://gis.slu.se/data/slu_forest_map/2005/Data/Raster/Rt90/TOTALVOL_XX_P_05.tif)

Det finns också trädslagsvis volym och beståndsålder. Dessa kan hjälpa oss testa 2010 års nivå med **2000/2005 som tidsmässiga kontrollpunkter**. Men volym i m³sk/ha får inte betraktas som samma variabel som biomassa i ton TS/ha utan en verifierad, helst trädslagsspecifik kalibrering. Volymlagren arkiveras och kalibreras lämpligen i ett separat efterföljande arbetssteg; inga syntetiska historiska biomassatal har införts här.
