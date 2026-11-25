## Uppdatering 2026-11-25: direkt källbekräftelse från SLU

**Viktig metoduppdatering:** tidigare i dokumentet redovisade statusen om obekräftad enhet är numera **historisk och ersatt** av följande direktbekräftelse från SLU, återgiven av projektets användare i korrespondens den 25 november 2026.

SLU:s Mats svarade om **exakt** `BIOMASS_XX_P_10.tif`:

> Kartskiktet med biomassa (på `BIOMASS_XX_P_10.tif`) är i tonTS/ha (TS = torrsubstans) och representerar hela träden ovan stubbskär inklusive grenar. För barrträd ingår även barren men det gör inte löven på lövträd.

Metodreferens som uppgavs av SLU: Marklund, L.G. (1988). *Biomassafunktioner för tall, gran och björk i Sverige*. Sveriges lantbruksuniversitet, Institutionen för skogstaxering, Rapport 45, 73 s.

**Fakta för just detta raster:** enhet **ton torrsubstans/ha**, ovan stubbskär, inklusive grenarna och barr hos barrträd, exklusive löv på lövträd, stubbar och rötter. Detta gäller exakt 2010-lagret, inte automatiskt andra år eller lager. XML-sidecars saknade uttrycklig enhet, men är inte längre avgörande eftersom dataleverantören nu specifikt har bekräftat den.

**Omräkning på projektets fullt omprojicerade 25m-grid EPSG:3006:** varje fullt giltig rastercell har planarea **0,0625 ha**, och bidraget i ton TS blir `värde_i_tTS_per_ha * 0.0625`. Summan av de *gemensamt giltiga, uttryckligt definierade* cellerna blir därmed fysisk modellskattad torrmassa. Den är **inte hela Luleås skogsförråd**; arbetsgräns, vattenklass, gemensam datatäckning och skogsdefinition måste stå i tabellrubrik. Rasterreprojicering har gjorts på hela griddet med `average`, inte bara genom att flytta rasterhörn.

**Jämförbarhet:** 2015 och 2018 har sedan tidigare dokumenterade ton TS/ha och biomassa ovan mark, utan stubbar/rötter. Dock är det inte källbekräftat att deras exakta barr-/lövinklusion, modellkalibrering och nollregler är samma som 2010. Vi får **räkna separata ton TS-värden** men **inte hävda en verifierad relativ fysisk biomassaförändring** mellan åren eller automatiskt korrigera 2010-modellen utifrån differensen.

**Spårbarhet:** `scripts/audit_biomass_units_and_mass_gate.py` har uppdaterats från NULL till faktisk ton TS-omräkning för 2010 under status `PHYSICAL_MASS_2010_CONVERSION_SOURCE_CONFIRMED_TEMPORAL_COMPARABILITY_NOT_VERIFIED`. Vattenfel från äldre QA-körningar korrigeras inte automatiskt; historisk vattentäckning och registrerade avverkningar kräver egna masker och kvalitetskontroller. Detta är en *bekräftelse från källans expert per e-post*, inte en öppet publicerad produktmetadatafil.

---

# Spårning av exakt biomassakälla för SLU Skogskarta 2010

## Bekräftat från projektets filer (2026-11-25)

**Exakt original:** [BIOMASS_XX_P_10.tif](https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/BIOMASS_XX_P_10.tif)

**Källdefinition:** SLU Skogskarta 2010, 25 m, RT90 2,5 gon V (**EPSG:3021**). Denna referens är fastslagen genom `docs/data/preview/preview_layers.json`, `scripts/cache_biomass_release.py`, `scripts/fetch_and_compare_biomass_native.py`, och filens arkiverade `lulea_biomass_2010_provenance.json`.

**Arkiveringskedjan:** ursprungliga cellvärden läses från nationalrastret i käll-CRS till `float32`, inom kommunens arbetsgräns. Utanför urvalet används NoData −9999. Arkivskriptet tillåter inte annan band-skalning än **1** eller offset än **0**. Det finns **ingen uttrycklig kg→ton-faktor** i klippningskedjan. Detta innebär *inte* att enheten därmed är fastställd: den kan redan definieras av originalrasterproduktens värden.

**Viktigt tillägg:** 2015 års aktiva projektlager är `Biomass_leaf.tif`, som projektet tidigare verifierat kan avse *totalt ovanjordiskt biomassaskikt* trots namnet. 2018 är `SGD2_BIO.tif`. Enhetsjämförelser måste avse exakt dessa filer – inte en tänkt namngiven normalprodukt.

## Officiella källor och återstående motsägelse

SLU:s [produktöversikt](https://www.slu.se/miljoanalys/statistik-och-miljodata/miljodatakatalogen/slu-skogskarta/) bekräftar biomassavariabler, årgångar och 25m-upplösning fram till 2010, men inte uttryckligen enheten eller träddelsomfattningen för **exakta** `BIOMASS_XX_P_10.tif`.

En [vetenskaplig källa (HESS, supplement 2025)](https://hess.copernicus.org/articles/29/5493/2025/hess-29-5493-2025-supplement.pdf) anger 2010 som ovanjordisk biomassa, ton/ha, medan beskrivningar av tidigare kNN-raster använder kg/ha och även underjordiska fraktioner. Dessa är olika uppgifter och får inte automatiskt appliceras på vår källfil.

SLU:s originalserver har två *filunika metadata*: [BIOMASS_XX_P_10.tif.aux.xml](https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/BIOMASS_XX_P_10.tif.aux.xml) och [BIOMASS_XX_P_10.tif.xml](https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/BIOMASS_XX_P_10.tif.xml).

## Ny verifieringskedja

`scripts/audit_2010_source_unit_metadata.py`:
1. Kräver en arkiverad 2010-proveniens som med SHA256 kan verifieras mot `lulea_biomass_2010_SHA256SUMS.txt`.
2. Kontrollerar att manifestets och proveniensens original-URL är samma exakta SLU-raster.
3. Kräver originalskala **1**, offset **0**, 25m och dokumenterat ursprung EPSG:3021.
4. Hämtar och arkiverar de **två exakta XML-sidecar-filerna**, registrerar hash och extraherar eventuella explicita textställen om kg/ha, ton/ha, rötter och ovanjordisk biomassa.
5. Skriver **granskningsbar evidens** till `metadata/biomass2010_source_unit_metadata_audit.json`.
6. Håller kvar resultatet `2010_tonnes_verified=false` och `2010_biomass_components_verified=false` tills eventuella metadata och extern produktdokumentation har granskats och entydigt matchats mot källraster.

### Fortsatt granskningsregel

Om XML-filerna innehåller tydlig enhet och biomassakomponent för **samma rasterband**, dokumentera och verifiera med SLU:s produktdokumentation och publicera en egen källhänvisning. Om de saknar detta eller ger tvetydiga uppgifter, efterfråga skriftlig bekräftelse från SLU:s datakontakt om **exakt `BIOMASS_XX_P_10.tif`**, inklusive ev. rotbiomassa. Ingen automatisk skalning från kg till ton eller rotjustering får göras på de nu publicerade råvärdena.

## Omräkning, om senare verifierad

Om originalcellen uttrycker **ton torrsubstans/ha av samma träddelar** som 2015 och 2018, och arkivet verkligen bevarat värdena, kan vi tillämpa **0,0625 ha per 25m-pixel** i vårt gemensamma EPSG:3006-grid och redovisa 2010 i ton TS. Om `kg/ha` gäller måste vi även använda **1/1000**, och om underjordiska delar ingår krävs en **källförankrad** biologisk komponentharmonisering. Om jämförelsebara träddelar inte kan identifieras är det sakligt riktigare att publicera två olika serier än att konstruera en falskt jämförbar trend.

## Faktiskt resultat av metadataaudit (GitHub Actions 45625700650)

**Godkänd källkontroll:** [workflowkörning](https://github.com/Lulea-statistik/kol-mark-och-trad/actions/runs/45625700650).

De båda filer som hämtades från den **exakta** 2010-rasterkatalogen:
- `BIOMASS_XX_P_10.tif.aux.xml`, 3 966 byte, SHA256 `b0b4abca3078d73b01b034475742a7b48d74df2baf62430e0ff40b6af99b8ccc`.
- `BIOMASS_XX_P_10.tif.xml`, 555 byte, SHA256 `a1123078cc061b0c2b4801b63af2c123feacd5fc5c3560d57aca619cb9790647`.

**Resultat:** Ingendera innehåller en explicit textangivelse om **kg/ha, ton/ha, rötter eller ovanjordisk biomassa**. Den första innehåller histogram och statistiska metadata, bland annat originalrastrets uppgivna maxvärde **623** och medel **81,203858...**. Den andra innehåller i huvudsak metadata om när statistiken beräknades **2014-08-08** och inte produktens fysikaliska definition. Dessa siffror kan inte användas för att sluta sig till enhet.

**Teknisk proveniens:** den hashverifierade kommunala arkivproveniensen för 2010 matchar den faktiska SLU-rasteradressen, EPSG:3021 och 25m, och arkiveringen använder skalfaktor 1 och offset 0. Ingen explicit kg→ton-operation sker i klippningen.

**Slutsats:** enheten och komponenterna kan fortfarande **inte anses verifierade** utifrån denna metadataaudit. Spärren från PR #100 är därför fortsatt korrekt.

### Förslag till källspecifik fråga till SLU

**Ämne: Produktdefinition för SLU Skogskarta 2010 – BIOMASS_XX_P_10.tif**

Hej,

Vi arbetar med jämförelser av biomassa i Luleå kommun mellan SLU Skogskarta 2010, SLU Skogskarta 2015 och Skogliga grunddata omdrev 2 (lokalt skannat 2018).

För 2010 används exakt följande rasterfil:
`https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/BIOMASS_XX_P_10.tif`

Vi har granskat rasterfilens `.tif.aux.xml` och `.tif.xml`, men de anger inte fysikalisk enhet eller vilka biomassa­komponenter som ingår. Filen är 25m, i RT90 2,5 gon V (EPSG:3021). Vårt lokala utsnitt har bevarat råvärdena utan omräkningsfaktor.

Kan ni bekräfta:
1. Vilken fysikalisk enhet som gäller **för själva rastervärdena i den exakta 2010-filen** (ton torrsubstans/ha, kg/ha eller annat)?
2. Om rastervärdet avser **endast ovanjordisk trädbiomassa** (stam, grenar, toppar, barr/löv) eller **även stubbar och rötter**, inklusive eventuella undantag?
3. Om biomassadefinitionen och modellernas nollregler är jämförbara med **2015 års `Biomass_leaf.tif`** och **2018 års `SGD2_BIO.tif`**?
4. Om det finns en originalproduktbeskrivning eller metodrapport för just 2010-lagret som kan citeras i en offentlig kommunal sammanställning?

Vi vill undvika att tolka faktiska skogsförändringar som modellfel och vill redovisa källornas olika biomassadefinitioner korrekt.

Tack på förhand!
