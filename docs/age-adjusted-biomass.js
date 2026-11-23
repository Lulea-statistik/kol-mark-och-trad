'use strict';
(async()=>{
 const node=document.getElementById('ageModelStatus');
 const fmt=(x,d=2)=>Number(x).toLocaleString('sv-SE',{maximumFractionDigits:d});
 try{
  const resp=await fetch('data/age_adjusted_biomass_2000_2005.json',{cache:'no-store'});
  if(!resp.ok)throw new Error('HTTP '+resp.status);
  const d=await resp.json();
  if(d.status!=='PROVISIONAL_AGE_DEPENDENT_RAW_BIOMASS_MODEL'||d.grid_crs!=='EPSG:3006'
    ||d.historical_results?.length!==3)throw new Error('Okänt/ogranskat resultatformat');
  const years=d.historical_results;
  for(const r of years){
   const tr=document.createElement('tr');
   for(const val of [String(r.year),fmt(r.age_based_raw_mean),fmt(r.global_factor_raw_mean),
        fmt(r.relative_difference_percent,2)+' %']){
     const td=document.createElement('td');td.textContent=val;tr.appendChild(td);
   }
   document.getElementById('ageModelRows').appendChild(tr);
  }
  document.getElementById('ageModelSupport').textContent=
   'Gemensam giltig yta i åldersanalysen: '+fmt(d.common_valid_area_ha,2)+' ha ('+
   fmt(d.common_valid_cells,0)+' celler). Råvärden är inte bekräftade ton torrsubstans. '+
   'Samma celler används inom denna jämförelse. Beräknat från arkiverade GeoTIFF i EPSG:3006, 25 m.';
  if(!window.Chart)throw new Error('Chart.js saknas');
  new Chart(document.getElementById('ageModelChart'),{
    type:'bar',data:{labels:years.map(r=>String(r.year)),datasets:[
      {label:'Åldersanpassad omräkning',data:years.map(r=>r.age_based_raw_mean),backgroundColor:'#17657e'},
      {label:'En enda faktor, samma yta',data:years.map(r=>r.global_factor_raw_mean),backgroundColor:'#bd7c38'}
    ]},options:{responsive:true,maintainAspectRatio:false,scales:{
       y:{beginAtZero:true,title:{display:true,text:'Medelråvärde, inte ton'}}},
       plugins:{tooltip:{callbacks:{label:i=>i.dataset.label+': '+fmt(i.parsed.y)}}}}
  });
  node.textContent='Åldersbaserad modell och global referens beräknade på samma yta. Modellvärdena är preliminära.';
 }catch(e){node.textContent='Åldersmodellen kan inte läsas: '+e.message;}
})();