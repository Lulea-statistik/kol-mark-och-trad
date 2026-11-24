# Fördjupad diagnostik av NMD2018-klasser och biomassaskillnaden 2010–2018

## Verifierade resultat från föregående körning

[GitHub Actions #45400889281](https://github.com/Lulea-statistik/kol-mark-och-trad/actions/runs/45400889281) passerade alla kontroller för **2 456 410 gemensamt giltiga 25-metersceller = 153 525,625 ha** i EPSG:3006.

| Klass enligt NMD2018 (fast referens) | Yta (ha) | Medelråvärde 2010 | Medelråvärde 2018 | Andel av nettodifferensen 2010–2018 |
| --- | ---: | ---: | ---: | ---: |
| 118 Temporärt ej skog utanför våtmark | 29 077,8125 | 47,45 | 25,46 | 55,11 % |
| 128 Temporärt ej skog på våtmark | 249,6875 | 74,71 | 25,12 | 1,07 % |
| 61 Sjö/vattendrag | 717,5 | 123,52 | 25,17 | 6,08 % |
| 62 Hav | 896,3125 | 120,06 | 5,40 | 8,86 % |

På 2010 års virkesvolym >=100 m³sk/ha återfinns **7 340,31 ha av klass 118**. Medelråvärdet för biomassa på dessa celler är 120,91 år 2010 och 20,48 år 2018. Detta är en viktig geografisk koncentration, men inget bevis på avverkning.

## Ny kontroll: skogsspecifik referens och vattenavstånd

Den uppdaterade analysen tar även fram:

1. Viktad medelnivå för **endast skogsklasser 111–117 och 121–127** (exklusive temporärt ej skog 118/128). Serien räknas på samma klassade och gemensamt giltiga celler alla tre år och ska inte utges för att vara hela kommunens skogsmark 2010.
2. Vattenceller i NMD2018 (61 och 62) uppdelade efter avstånd från cellcentrum till **närmsta NMD2018-icke-vattencell** på gemensamt 25 m rastergrid: 0–50, 50–100, 100–250 och minst 250 meter. För varje avståndsklass anges areal, medelråvärde 2010/2015/2018 och andel med hög virkesvolym 2010.

Beräkningen görs med full rasterreprojicering, aldrig enbart transformerad bounding-box. Avstånd är från *NMD-klassat vatten till NMD-klassad icke-vattenyta*, **inte** ett oberoende kustlinjemått. Den geografiska studien avser den begränsade gemensamma biomassatäckningen, inte alla vattenytor i Luleå kommun. NMD2018 kan inte styrka enskilda cellers historiska markklass 2010.

## Beslutsregel

Om höga vattenråvärden koncentreras till avståndsbandet 0–50 m är en strandlinje-/resamplingshypotes förenlig med resultatet. Om de även återfinns långt från icke-vatten indikerar det en bredare mask-/modellfråga. Ingen av dessa observationer bevisar rasterfel eller vilken ursprungskälla som är orsak; 2010 års virkesvolym och biomassa kan dela modellunderlag.

**Ingen automatisk justering av 2010, 2015 eller 2018 års ursprungliga data görs.** Dessa är diagnoser av råvärden innan säkerställd harmonisering.
