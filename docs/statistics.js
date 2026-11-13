'use strict';
const definitions=[
  {key:'biomass',label:'Trädbiomassa ovan mark (kol)'},
  {key:'soil',label:'Kolförråd – markkol (Stock_SOC)'},
  {key:'soil_all',label:'Kolförråd (totalt, inkl. dött material) – Stock_All'},
  {key:'volume',label:'Volymbaserad skattning (reserv)'}
];
const fmt=(n,d=0)=>Number(n).toLocaleString('sv-SE',{maximumFractionDigits:d});
function setCell(row,value){const cell=document.createElement('td');cell.textContent=value;row.appendChild(cell);}
let currentData={layers:{}},carbonChartInstance=null,densityChartInstance=null;
const unitSelect=document.getElementById('carbonUnit');
unitSelect.addEventListener('change',()=>render(currentData));
function render(d){
 currentData=d;
 if(carbonChartInstance){carbonChartInstance.destroy();carbonChartInstance=null;}
 if(densityChartInstance){densityChartInstance.destroy();densityChartInstance=null;}
 const factor=unitSelect.value==='CO2'?44/12:1;
 const unitLabel=unitSelect.value==='CO2'?'ton CO₂':'ton C';
 document.getElementById('carbonMassHeading').textContent='Kolförråd, '+unitLabel;
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
  setCell(row,valid?(partial?'Täckt yta: ':'')+fmt(stored*factor):'Data saknas');
  setCell(row,covered!==null?fmt(covered,1):'—');
  setCell(row,valid&&Number.isFinite(Number(data.coverage_pct_of_municipality))
    ?fmt(data.coverage_pct_of_municipality,1)+' %'+(partial?' (ofullständig)':''):'—');
  setCell(row,valid?[data.source,data.source_year].filter(Boolean).join(' · '):'Ej importerad');
  tbody.appendChild(row);
  if(valid&&item.key!=='volume')verified.push({key:item.key,label:item.label,value:stored,density:covered>0?stored/covered:null,partial});
 }
 // Only sum non-overlapping stock pools; Stock_All already includes Stock_SOC.
 // Do not turn missing data or mismatched source extents into a municipal total.
 const sumRow=document.createElement('tr');
 const combinedKeys=['biomass','soil_all'];
 const components=combinedKeys.map(key=>verified.find(x=>x.key===key));
 const sameExtent=components.every(Boolean)&&components.every(x=>!x.partial);
 const totalValid=sameExtent&&components.every(x=>Number.isFinite(x.value));
 setCell(sumRow,'Summa kolförråd (trädbiomassa + totalt markförråd; preliminärt urval)');
 setCell(sumRow,totalValid?fmt(components.reduce((acc,x)=>acc+x.value,0)*factor):'Data saknas – fullständig och jämförbar täckning krävs');
 setCell(sumRow,'—');setCell(sumRow,'—');
 setCell(sumRow,totalValid?'Modellberäknad sammanställning; granskas före användning':'Ej beräknad');
 tbody.appendChild(sumRow);
 const comparable=verified.filter(x=>x.key!=='soil_all');
 const available=comparable.filter(x=>!x.partial&&x.value>=0);
 const status=document.getElementById('statsStatus');
 status.textContent=verified.length
   ?verified.length+' källager med beräknade värden inom Luleås kommungräns. Sammanställningen anger täckt yta och extrapolerar inte till ytor utan data.'
   :'Inga verifierade kolförrådsraster finns ännu i projektet. Tabellerna visar dataluckor utan påhittade värden.';
 const note=document.getElementById('chartNote');
 if(available.length&&window.Chart){
  note.textContent='Varje stapel avser endast observerade eller modellerade rasterceller inom Luleå kommun. Skogsmark kan täcka en mindre del av kommunytan utan att resultatet är felaktigt. Staplar för skilda kolpooler får inte automatiskt summeras.';
  carbonChartInstance=new Chart(document.getElementById('carbonChart'),{
    type:'bar',data:{labels:available.map(x=>x.label),datasets:[{label:unitLabel+' inom kommunen',data:available.map(x=>x.value*factor),backgroundColor:['#2f7858','#947046']}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,title:{display:true,text:unitLabel}}}}
  });
 }else{
  note.textContent='Diagrammet visas när en kontrollerad kolförrådsserie har importerats.';
  document.getElementById('carbonChart').hidden=true;
 }
 const density=comparable.filter(x=>x.density!==null);
 if(density.length&&window.Chart){
  densityChartInstance=new Chart(document.getElementById('densityChart'),{
   type:'bar',data:{labels:density.map(x=>x.label),datasets:[{label:unitLabel+' per täckt ha',data:density.map(x=>x.density*factor),backgroundColor:['#3c8065','#ad8558']}]},
   options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,title:{display:true,text:unitLabel+'/ha täckt yta'}}}}
  });
 }else document.getElementById('densityChart').hidden=true;
}
fetch('data/layers.json',{cache:'no-store'})
 .then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json();})
 .then(render).catch(e=>{document.getElementById('statsStatus').textContent='Kunde inte läsa lagermetadata: '+e.message;render({layers:{}});});
