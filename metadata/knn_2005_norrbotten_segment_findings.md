# Inventering av SLU kNN 2005 segmenterade Norrbotten.zip

Granskad fil: https://gis.slu.se/data/slu_forest_map/2005/Data/SegmentShape/Norrbotten.zip

Metod: läs ZIP-centralkatalog och båda DBF-scheman med verifierade HTTP 206 byte-range. Ingen full nedladdning. Analyskörning [#45197630788](https://github.com/Lulea-statistik/kol-mark-och-trad/actions/runs/45197630788) godkänd.

## Verifierat resultat

- Norrbotten_O.dbf, **302 922** poster.
- Norrbotten_V.dbf, **345 133** poster.
- Fält i **båda**: `ID`, `Voltot_mea`, `Voltot_med`, `Voltot_std`, `Sprce_mean`, `Sprce_med`, `Sprce_std`, `Pine_mean`, `Pine_med`, `Pine_std`, `Cntrt_mean`, `Cntrt_med`, `Cntrt_std`, `Birch_mean`, `Birch_med`, `Birch_std`, `Decid_mean`, `Decid_med`, `Decid_std`, `Oak_mean`, `Oak_med`, `Oak_std`, `Beech_mean`, `Beech_med`, `Beech_std`, `Age_mean`, `Age_median`, `Age_std`, `Hght_mean`, `Hght_med`, `Hght_std`, `Shape_Leng`, `Shape_Area`.
- **Ingen** DBF-kolumn namngiven biomassa, bio, BM eller motsvarande fanns i de båda tabellerna. Det är därför fel att använda zip som **observerad 2005 års biomassa**.
- Båda PRJ-strängarna beskriver Bessel 1841 / RT90-liknande Transverse Mercator med falsk östlig koordinat 1 500 000 m och centralmeridian 15,8082778°, men **PRJ innehåller inte någon explicit EPSG-auktoritet**. Ingen CRS likställs automatiskt utan granskad transformation, exempelvis till EPSG:3021 innan överlagring med raster.
- SLU:s [produktinformation](https://gis.slu.se/data/slu_forest_map/2005/Data/SegmentShape/kNN-2005-2010-info.pdf) förklarar att segment är beståndsliknande områden med statistik från ingående 25 m rasterceller. Datasetet är **inte fristående skoglig inventering** och **inte en oberoende validering** av SLU:s samtidiga volymskikt.

## Konsekvens för biomassamodellen

Åldersbaserad modell 2000/2005 består som preliminär: den påverkas inte av att ZIP-filen saknar biomassavärden. Segmentdata kan däremot ge en alternativ rumslig aggregering för volym, trädslagskomposition och ålder. En framtida trädslagsspecifik kvotmodell måste kalibreras separat och kontrolleras för faktorernas beroende av ålder, trädslag och skogsmark.

**Kvarstående datafråga:** SLU:s allmänna Skogskarta-beskrivning uppger biomassa för 2005, men den prövade `BIOMASS_XX_P_05.tif` gav HTTP 404. Vi har ännu inte ett verifierat originalskikt 2005 för att validera resultatet. Saknade lager ska inte ersättas med antagna observationer.
