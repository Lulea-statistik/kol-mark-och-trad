# Varför så hög biomassa 2010 inom NMD2018 "ej skogsmark"?

## Befintliga resultat från PR #79 (verifierad GitHub Actions-körning)

På samma 2 456 410 analysceller (153 525,625 ha) i EPSG:3006 ger NMD-klass 0 **17 604,25 ha** och biomassamedelråvärden 2010 **55,63**, 2015 **27,87**, 2018 **28,28**. Detta är **26,18 % av nettoskillnaden 2010–2015** och **41,48 % av nettoskillnaden 2010–2018**, trots att klassen upptar bara 11,47 % av jämförelseytan.

Klass 1, produktiv skogsmark, visar emellertid också större biomassamedelvärde 2010 (**80,90**) jämfört med 2015 (**70,78**) och 2018 (**76,04**). Därför kan klass 0 inte ensam stå för hela skillnaden. Nettobidragen är en bokföringsuppdelning av råvärden, inte bevis på orsak.

**Viktigt:** NMD2018 klass 0 betyder "ej skogsmark enligt NMD2018". Det är inte en historisk kontroll av om området var skogsmark 2010. Områden kan vara trädbärande men inte uppfylla produktions-/skogskriteriet, och felklassning i rastergränser eller olika avgränsningar kan förekomma. Även 2010 års modell inkluderar underjordiska biomassakomponenter medan andra produkter skiljer sig. Modellerna är inte komponentharmoniserade.

## Nytt kontrolltest

`scripts/diagnose_nmd2018_nonforest_volume.py` korsar den **fasta** NMD2018-klassningen med 2010 års verifierade virkesvolym på exakt samma celler i **EPSG:3006 / 25 m**, utan EPSG:3857-förhandsbilder. 2010 års volymklasser är 0, (0,50), [50,100), [100,200), och 200+.

Resultattabellen ska visa för varje kombination:
- antal gemensamt giltiga celler och hectares,
- biomassa 2010/2015/2018 medelråvärden,
- kombinationens andel av 2010–2018 års summerade råvärdesskillnad,
- saknade volymvärden per NMD-klass som separat kontroll.

Den konkreta **hypotesprövningen** är om den stora nivådifferensen i NMD klass 0 koncentreras till celler med hög virkesvolym 2010. Ett sådant resultat indikerar att klass 0 inte motsvarar "trädlös mark år 2010". Det fastställer dock inte att NMD2018 var fel eller att skog avverkats; ett avverknings-/markanvändningstest skulle kräva korsning med daterade avverkningspolygoner och historisk klassning.

**Status:** ny faktisk rasterkörning ingår i PR och måste bli grön innan nya siffror får användas. Befintlig webb- och biomassaserie ändras inte i denna PR.
