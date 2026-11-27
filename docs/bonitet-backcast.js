/* Bonitet backward scenario: never labels hypothetical values as observations. */
(function(){
'use strict';
const status=document.getElementById('bonitetBackcastStatus');
const table=document.getElementById('bonitetBackcastTable');
const canvas=document.getElementById('bonitetBackcastChart');
if(!status||!table||!canvas)return;
const sv=(n,p=2)=>Number(n).toLocaleString('sv-SE',{minimumFractionDigits:p,maximumFractionDigits:p});
fetch('data/bonitet_bakatrakning_scenarier.json',{cache:'no-store'})
.then(r=>{if(!r.ok)throw Error('scenariofilen är inte publicerad');return r.json()})
.then(d=>{
  if(d.status!=='ILLUSTRATIVE_NOT_FIELD_CALIBRATED'||d.crs!=='EPSG:3006')
    throw Error('resultat saknar obligatorisk scenariomärkning');
  const c=d.cohorts.age_ge20;
  const scenarios=[['low','Låg tillväxt'],['central','Basscenario'],['high','Hög tillväxt']];
  const original=c.modeled_mass_tTS;
  const toM=n=>n/1e6;
  const perYear=(original['2018']-original['2015'])/3/c.area_ha;
  status.textContent='Urval: '+sv(c.area_ha,0)+' ha på samma celler. Modellerad 2015–2018-förändring: '+sv(perYear)+' ton TS/ha och år. Scenario för tillväxt baseras på antagen bonitet och omräkningsfaktor, inte uppmätt tillväxt eller kalibrerad beståndsmodell.';
  const rows=scenarios.map(([key,label])=>{
    const v=c.scenario_backcast[key];
    return '<tr><th scope="row">'+label+'</th><td>'+sv(v.assumed_annual_net_gain_tTS/c.area_ha)+'</td><td>'+
      sv(toM(v['2010_backcast_from_2015_tTS']))+'</td><td>'+
      sv(toM(v['2010_backcast_from_2018_tTS']))+'</td></tr>';
  });
  table.innerHTML='<table><caption>Illustrativ bakåträkning till 2010 (miljoner ton TS, gemensam area)</caption>'+
    '<thead><tr><th>Beräkning</th><th>Antagen nettotillväxt (ton TS/ha/år)</th><th>Från 2015</th><th>Från 2018</th></tr></thead><tbody>'+rows.join('')+
    '<tr><th>2010 års ursprungliga modell</th><td>–</td><td colspan="2">'+sv(toM(original['2010']))+'</td></tr></tbody></table>';
  if(typeof Chart==='undefined')return;
  const labels=['Låg','Bas','Hög'];
  const lowToHigh=scenarios.map(([k])=>c.scenario_backcast[k]);
  new Chart(canvas,{type:'bar',data:{labels,datasets:[
    {label:'Bakåt från 2015',data:lowToHigh.map(x=>toM(x['2010_backcast_from_2015_tTS'])),backgroundColor:'#6a90ad'},
    {label:'Bakåt från 2018',data:lowToHigh.map(x=>toM(x['2010_backcast_from_2018_tTS'])),backgroundColor:'#b87851'},
    {label:'Modellerad biomassa 2010',type:'line',data:lowToHigh.map(()=>toM(original['2010'])),borderColor:'#364d46',backgroundColor:'#364d46',pointRadius:4,borderWidth:2}
  ]},options:{responsive:true,maintainAspectRatio:false,
    plugins:{tooltip:{callbacks:{label:c=>c.dataset.label+': '+sv(c.parsed.y)+' miljoner ton TS'}}},
    scales:{y:{title:{display:true,text:'Miljoner ton modellerad/illustrativ TS'}}}}});
}).catch(e=>status.textContent='Bakåträkningen kan inte laddas: '+e.message);
})();
