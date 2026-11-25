# SMD2000: historisk källkontroll av 579 avvikande 2010-celler

## Resultat som faktiskt är beräknade på lokalt SMD-underlag (2026-11-25)

Den lokalt tillgängliga, **privata** CSV-filen `smd2000_2010_579_native_pixels_local.csv` omfattar 579 **unika** 2010-källrasterceller × tre varianter av historisk SMD2000-leverans (1 737 rader). Cellerna valdes ut i en tidigare kontroll för att både 2010-biomassa och volym har giltiga råvärden samtidigt som ursprungligt NMD2018-data anger **minst 99,9 % vatten**. Dessa 579 celler är alltså **inte ett statistiskt representativt urval av all skog i kommunen**.

| Historisk SMD2000-klass vid cellmitt | Januari 2012, verifierat EPSG:3006 | April 2012 | Alternativ lulea.zip |
|---|---:|---:|---:|
| Vatten | **460** (79,4 %) | 460 | 439 |
| Skog | 64 | 64 | 82 |
| Övrig mark | 55 | 55 | 58 |
| Summa | **579** | 579 | 579 |

**Högre evidenskrav – samstämmighet mellan samtliga tre leveranser:**
- **425 av 579** (73,4 %) är *vatten i samtliga tre*.
- 55 celler är skog i samtliga tre.
- 51 celler är övrig mark i samtliga tre.
- 48 celler (8,3 %) har olika klassning mellan minst två leveranser.
- Januari och april skiljer sig i endast **två** celler; januari och alternativleveransen skiljer sig i **47** celler.
- För januariarkivet är **324 av 579** celler minst **95 % SMD-vatten till arealen** i cellpolygonen, inte bara i mitten.
- Av de **22 celler** som saknar NMD2018-land inom alla åtta grannceller är **19** klassade som vatten i *samtliga tre* SMD-leveranser. De återstående tre är grus-/sandtag enligt den tidigare cellrapporten.

### Vetenskaplig slutsats

**2010 års modellerade biomassa/volym förekommer på ett antal områden som i historisk SMD2000 bedöms som vatten och även är vatten 2018.** Det finns därför empiriskt stöd för ett modell-/markmaskproblem i vissa 2010-celler. I synnerhet är en *förändrad strandlinje 2010–2018 som enda generell förklaring* svår att försvara för de 19 isolerade vattenområdena.

**Detta bevisar inte** att 2010-modellen överskattar biomassan i hela kommunen med 73 % eller 79 %, eller att trendresultaten från PR #105 är korrigerade. Materialet är selekterat på NMD2018-vatten och klassningen från SMD gäller cirka **år 2000**. De tre SMD-leveranserna är inte tre oberoende inventeringar; skillnader mellan dem kan bero på generalisering och geometrisk bearbetning.

## Reproducerbar privat sammanfattning

Nytt `scripts/summarize_smd2000_water_anomaly_consensus_private.py` läser de redan existerande **privata** cellvisa jämförelserna och kontrollerar exakt en rad per kombination av 2010-pixel och SMD-leverans. Verktyget räknar antal, parvisa avvikelser, vattenandel per cell och de 22 isolerade. Det **exporterar aldrig koordinater, geometrier eller cellvisa klassningar**; om JSON sparas måste den skrivas utanför det publika Git-repositoriet. Verktygets GitHub Actions använder bara **syntetiskt framställda testceller**, aldrig de riktiga SMD-filerna.

```bash
python scripts/summarize_smd2000_water_anomaly_consensus_private.py \
  --input "/privat/smd2000_2010_579_native_pixels_local.csv" \
  --output "/privat/resultat/smd2000_water_anomaly_aggregate.json"
```

### Fortsatt prioritering

När originalklippen från GitHub Releases är nedladdade till den privata lokala miljön bör vi genomföra den **fullständiga** överläggningen för 2010-proxyn med SMD2000-skog, skog+ungskog och vattenmask (PR #106–107). Först **då** får vi en arealrepresentation och omräknad **råvärdessummeutveckling 2010–2018** för hela det gemensamma giltiga jämförelseområdet.

Inga licensierade SMD2000-shapefiler, cellkoordinater eller kartlager ska publiceras. Aggregerade resultat behöver också licensgranskas före extern användning. 2010 års fysikaliska biomassaenheter och träddelsdefinition kvarstår som öppet metodhinder (PR #104).
