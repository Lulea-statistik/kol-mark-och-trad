'use strict';
(async()=>{
 const status=document.getElementById('volume2005ChangeStatus');
 const tbody=document.getElementById('volume2005AgeTable');
 const fmt=(v,d=2)=>Number(v).toLocaleString('sv-SE',{maximumFractionDigits:d});
 try{
  const response=await fetch('data/volume_2005_2010_diagnostics.json',{cache:'no-store'});
  if(!response.ok)throw Error('HTTP '+response.status);
  const d=await response.json();
  if(d.status!=='HISTORICAL_VOLUME_CHANGE_DESCRIPTIVE_NOT_GROWTH'||
     d.analysis_crs!=='EPSG:3006'||d.pixel_size_m!==25||
     d.common_valid_area_ha!==144800.25)
    throw Error('Oförenlig diagnos för volym / EPSG / yta');
  const rows=d.baseline_age_2005_strata.filter(x=>x.n>=100);
  const makeRow=values=>{
   const tr=document.createElement('tr');
   for(const value of values){const cell=document.createElement('td');cell.textContent=value;tr.appendChild(cell)}
   tbody.appendChild(tr);
  };
  for(const row of rows){
   makeRow([
    row.age_2005_upper===null?row.age_2005_lower+'+':row.age_2005_lower+'–'+row.age_2005_upper,
    fmt(row.area_ha,0),fmt(row.mean_volume_2005),fmt(row.mean_volume_2010),
    fmt(row.mean_change_2005_2010)
   ]);
  }
  if(!window.Chart)throw Error('Chart.js saknas');
  new Chart(document.getElementById('volume2005AgeChart'),{
   type:'bar',
   data:{labels:rows.map(x=>x.age_2005_upper===null?x.age_2005_lower+'+':x.age_2005_lower+'–'+x.age_2005_upper),
    datasets:[
     {label:'Virkesvolym 2005',data:rows.map(x=>x.mean_volume_2005),backgroundColor:'#367eaa'},
     {label:'Virkesvolym 2010',data:rows.map(x=>x.mean_volume_2010),backgroundColor:'#c07b39'}
    ]},options:{responsive:true,maintainAspectRatio:false,
    interaction:{mode:'index',intersect:false},
    scales:{x:{title:{display:true,text:'Åldersklass från 2005 års åldersraster'}},
     y:{beginAtZero:true,title:{display:true,text:'Medelråvärde från virkesvolymsraster (ej verifierad fysisk förändring)'}}},
    plugins:{tooltip:{callbacks:{label:item=>item.dataset.label+': '+fmt(item.parsed.y)}}}}
  });
  const q=d.age_difference_classes;
  const ageReset=100*q.age_2010_at_least_10_less_than_2005.n/d.common_valid_cells;
  const stable=100*q.age_2010_roughly_age_2005_plus_five.n/d.common_valid_cells;
  status.textContent='På '+fmt(d.common_valid_area_ha,2)+' ha stiger virkesvolymens medelråvärde från '+
    fmt(d.volume_raw_means['2005'])+' (2005) till '+fmt(d.volume_raw_means['2010'])+
    ' (2010): +'+fmt(d.volume_raw_change_percent_2005_2010)+' %. '+
    fmt(100*d.volume_cells_increase_fraction_2005_2010,1)+' % av cellerna har högre virkesvolymsvärde 2010. '+
    'Åldersskattningen 2010 är minst 10 år lägre än 2005 i '+fmt(ageReset,1)+
    ' % av cellerna; i '+fmt(stable,1)+
    ' % är åldersskillnaden inom intervallet −2 till +12 år. '+
    'Dessa toleranser är explorativa och anger inte säker avverkning, tillväxt eller modellfel.';
 }catch(e){status.textContent='Virkesvolymdiagnostiken kunde inte visas: '+e.message;status.classList.add('warning')}
})();