# Datakällor och importordning för Luleås kolkarta

Inventering 2026-11-13. Detta dokument är ett granskningsunderlag, **inte en bekräftelse att rasterfiler finns i repot**.

| Prioritet | Källa | Lager | Upplösning/tid | Åtkomst | Status |
|---|---|---|---|---|---|
| 1 | Skogsstyrelsen / SLU Skogliga grunddata | Biomassa, omdrev 3 (2025–) | 12,5 m produktfamilj, faktisk täckning varierar | Skogsstyrelsen raster: konto/åtkomst kan krävas | Finns i katalog; inget verifierat Luleå-raster importerat |
| 2 | Skogsstyrelsen / SLU Skogliga grunddata | Biomassa, omdrev 2 (2018–2025) | 12,5 m produktfamilj | Som ovan | Reserv där omdrev 3 saknar täckning, måste jämföras |
| 3 | Skogsstyrelsen / SLU Skogliga grunddata | Biomassa, omdrev 1 (2008–2016) | 12,5 m produktfamilj | Som ovan | Äldre reserv med egen observationsperiod |
| 4 | SLU Kolkartor | Stock_SOC (markkol) | 10 × 10 m, kartläggning kopplad till 2000–2020 | https://gis.slu.se/data/carbon/ | Källraster ännu ej hämtat eller enheter kontrollerade |
| 5 | SLU Kolkartor | Stock_All (totalt markförråd, inkl. SOC och DOM) | 10 × 10 m, kartläggning kopplad till 2000–2020 | Samma | Alternativt markmått, **lägg aldrig ihop med Stock_SOC** |
| 6 | SLU Skogskarta | Biomassa | 2015: 12,5 m; äldre: 25 m | https://gis.slu.se/data/slu_forest_map/ | Historiskt kompletterande underlag, inte nutidsvärde |
| 7 | Skogsstyrelsen / SLU Skogliga grunddata | Volym, omdrev 3/2/1 | Samma grunddataproduktfamilj | Skogsstyrelsen | **Endast** reserv där biomassaprodukter inte är användbara, och bara med dokumenterad biomassafunktion |

Källor:
- https://www.skogsstyrelsen.se/laddanergeodata
- https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/geodatatjanster/
- https://www.slu.se/miljoanalys/statistik-och-miljodata/miljodatakatalogen/skogliga-grunddata/
- https://www.slu.se/miljoanalys/statistik-och-miljodata/miljodatakatalogen/slu-skogskarta/
- https://www.slu.se/miljoanalys/statistik-och-miljodata/miljodatakatalogen/slu-kolkartor/

## Väsentliga verifieringar före import

1. **Originalraster:** filens dokumenterade koordinatsystem (EPSG eller WKT), rastertransform, NODATA, band, pixelstorlek, nodata-/vatten-/skogsmask och absolut mätvärdesskala (eventuell scale/offset).
2. **Fysisk enhet:** ton C/ha, ton torr biomassa/ha, kg torr biomassa/ha eller annan enhet. **Använd inte värden som ton/ha bara för att siffrorna ser rimliga ut.** Produkter kan ha andra definitioner, exempelvis totalbiomassa inklusive rötter.
3. **Vilken biomassa?** Bestäm om den innehåller endast ovanjordiska delar, grenar, stam, barr, stubbe, rötter eller annan kombination. Kartan kan inte märkas \"ovan mark\" förrän detta är verifierat.
4. **År och omdrev:** registrera produktionsår, laserflygning, inventeringsperiod eller motsvarande. Slå inte samman omdrev som om de hade samma observationsdatum.
5. **Geografisk avgränsning:** återanvänt kommunlager finns i `docs/data/lulea_boundary.geojson` (lon/lat, EPSG:4326) och kommer från kommunens tidigare väderprojekt. Verifiera mot aktuell officiell Luleå kommungeometri innan officiell statistik publiceras.
6. **Rasterbearbetning:** klipp i **källrastrets CRS**. Maskera kommunytan i **EPSG:3006** för arealintegrering och reprojicera hela bildgridet till **EPSG:3857** innan webbvisning.
7. **Täckning:** Skogsbiomassa finns i regel enbart för skogliga celler. Beräkna kolsumma på giltiga skogsceller inom kommunen och rapportera täckt areal, utan att extrapolera till all kommunmark. För markkol är även marktyp och klassade markytor avgörande.
8. **Säkerhet och rättigheter:** Kontrollera nedladdningsvillkor för respektive källa och lägg inga lösenord i GitHub.

## Viktig åtskillnad

En nationell kolförrådskarta med 10 m pixelstorlek innebär inte samma lokala noggrannhet som 10 m markprover. SLU påpekar uttryckligen att markkolskartan till stor del bygger på **regionala medelvärden**, ofta länsnivå. Kommunresultat ska därför beskrivas som *modellskattning*, inte mätning.

**Nästa tekniska steg:** få tag på faktiska GeoTIFF-filer eller läsbehörighet till aktuella nedladdningstjänster, verifiera metadata och därefter köra `scripts/process_carbon_raster.py` för varje lämpligt källager. Karta och statistiksida förblir utan värden tills den granskningen är gjord.
