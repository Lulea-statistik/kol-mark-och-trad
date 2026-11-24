'use strict';
(async()=>{
 const status=document.getElementById('speciesStabilityStatus');
 const main=document.getElementById('speciesStabilityTable');
 const matrix=document.getElementById('speciesTransitionTable');
 const fmt=(n,d=1)=>Number(n).toLocaleString('sv-SE',{maximumFractionDigits:d});
 const pct=(n)=>n==null?'–':fmt(100*n)+' %';
 const add=(el,values)=>{
  const tr=document.createElement('tr');
  for(const value of values){const td=document.createElement('td');td.textContent=value;tr.appendChild(td)}
  el.appendChild(tr);
 };
 try{
  const r=await fetch('data/species_stability_2005_2010.json',{cache:'no-store'});
  if(!r.ok)throw Error('HTTP '+r.status);
  const d=await r.json();
  if(d.status!=='VERIFIED_SOURCE_PAIRED_SPECIES_VOLUMES_NOT_A_BIOMASS_CHANGE'||
     d.raster_crs!=='EPSG:3006'||d.cell_size_m!==25||
     d.baseline_area_ha!==144800.25||!d.dominance_stability)
   throw Error('Fel raster, referensyta eller format i trädslagsmodellen');
  const s=d.dominance_stability;
  for(const [key,label] of [
   ['age_2005_0_20','0–20 år'],
   ['age_2005_20_40','20–40 år'],
   ['age_2005_40_60','40–60 år'],
   ['age_2005_60_plus','60 år eller äldre'],
   ['age_2005_20_plus','Alla minst 20 år'],
   ['age_2005_20_plus_no_large_age_reset','Minst 20 år, ingen stor åldersminskning'],
   ['age_2005_20_plus_age_consistent','Minst 20 år, ålderskonsistent']
  ]){
   const x=s[key];
   if(!x)throw Error('Åldersgrupp saknas: '+key);
   add(main,[label,fmt(x.area_ha,0),pct(x.eligible_share),
     pct(x.same_dominant_class_fraction),
     pct(x.dominant_pine_stays_pine_fraction),
     pct(x.dominant_spruce_stays_spruce_fraction),
     pct(x.mean_conifer_volume_share_2005),
     pct(x.mean_conifer_volume_share_2010)]);
  }
  const older=s.age_2005_20_plus;
  const names=['Tall','Gran','Björk','Övrigt löv','Blandad','Oklassificerad'];
  const counts=older.transition_counts;
  if(counts.length!==6||counts.some(row=>row.length!==6))throw Error('Övergångsmatris 6×6 saknas');
  for(let i=0;i<6;i++){
   const row=counts[i];
   const n=row.reduce((a,b)=>a+b,0);
   add(matrix,[names[i],...row.map(v=>n>0?pct(v/n):'–')]);
  }
  status.textContent='Källa: åtta trädslagsvolymraster från SLU 2005/2010. '+fmt(d.baseline_area_ha,2)+
   ' ha gemensam 25 m-analysyta i EPSG:3006. Dominansgräns 60 % av de fyra redovisade delvolymerna; '+
   'celler med låg volym eller bristande delvolymsavstämning redovisas separat som oklassificerade. '+
   'Klassbyte är inte automatiskt verkligt trädslagsbyte.';
 }catch(e){status.textContent='Trädslagsstabiliteten kunde inte visas: '+e.message;status.classList.add('warning')}
})();