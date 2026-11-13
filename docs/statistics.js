'use strict';
const definitions=[
  {key:'biomass',label:'Trädbiomassa ovan mark (kol)'},
  {key:'soil',label:'Markkol (Stock_SOC)'},
  {key:'soil_all',label:'Mark totalt (Stock_All)'},
  {key:'volume',label:'Volymbaserad skattning (reserv)'}
];
const fmt=(n,d=0)=>Number(n).toLocaleString('sv-SE',{maximumFractionDigits:d});
function setCell(row,value){const cell=document.createElement('td');cell.textContent=value;row.appendChild(cell);}
function render(d){
 const tbody=document.querySelector('#carbonTable tbody');
 tbody.replaceChildren();
 const verified=[];
 for(const item of definitions){
  const data=d.layers?.[item.key],row=document.createElement('tr');
  const valid=!!data&&Number.isFinite(Number(data.total_tonnes_C))&&data.total_tonnes_C!==null;
  const partial=valid&&data.total_scope!=='municipality';
  const stored=valid?Number(data.total_tonnes_C):null;
  const covered=valid&&Number.isFinite(Number(data.covered_hectares))?Number(data.covered_hectares):null;
  setCell(row,item.label);
  setCell(row,valid?(partial?'Täckt yta: ':'')+fmt(stored):'Data saknas');
  setCell(row,valid?fmt(stored*44/12):'—');
  setCell(row,covered!==null?fmt(covered,1):'—');
  setCell(row,valid&&Number.isFinite(Number(data.coverage_pct_of_municipality))
    ?fmt(data.coverage_pct_of_municipality,1)+' %'+(partial?' (ofullständig)':''):'—');
  setCell(row,valid?[data.source,data.source_year].filter(Boolean).join(' · '):'Ej importerad');
  tbody.appendChild(row);
  if(valid&&item.key!=='volume')verified.push({key:item.key,label:item.label,value:stored,density:covered>0?stored/covered:null,partial});
 }
 const comparable=verified.filter(x=>x.key!=='soil_all');
 const available=comparable.filter(x=>!x.partial&&x.value>=0);
 const status=document.getElementById('statsStatus');
 status.textContent=verified.length
   ?verified.length+' källager med beräknade värden inom Luleås kommungräns. Sammanställningen anger täckt yta och extrapolerar inte till ytor utan data.'
   :'Inga verifierade kolförrådsraster finns ännu i projektet. Tabellerna visar dataluckor utan påhittade värden.';
 const note=document.getElementById('chartNote');
 if(available.length&&window.Chart){
  note.textContent='Varje stapel avser endast observerade eller modellerade rasterceller inom Luleå kommun. Skogsmark kan täcka en mindre del av kommunytan utan att resultatet är felaktigt. Staplar för skilda kolpooler får inte automatiskt summeras.';
  new Chart(document.getElementById('carbonChart'),{
    type:'bar',data:{labels:available.map(x=>x.label),datasets:[{label:'Ton C inom kommunen',data:available.map(x=>x.value),backgroundColor:['#2f7858','#947046']}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,title:{display:true,text:'Ton C'}}}}
  });
 }else{
  note.textContent='Diagrammet visas när en kontrollerad kolförrådsserie har importerats.';
  document.getElementById('carbonChart').hidden=true;
 }
 const density=comparable.filter(x=>x.density!==null);
 if(density.length&&window.Chart){
  new Chart(document.getElementById('densityChart'),{
   type:'bar',data:{labels:density.map(x=>x.label),datasets:[{label:'Ton C per täckt ha',data:density.map(x=>x.density),backgroundColor:['#3c8065','#ad8558']}]},
   options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,title:{display:true,text:'Ton C/ha täckt yta'}}}}
  });
 }else document.getElementById('densityChart').hidden=true;
}
fetch('data/layers.json',{cache:'no-store'})
 .then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json();})
 .then(render).catch(e=>{document.getElementById('statsStatus').textContent='Kunde inte läsa lagermetadata: '+e.message;render({layers:{}});});
