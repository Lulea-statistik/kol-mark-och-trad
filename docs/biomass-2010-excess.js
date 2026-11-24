'use strict';
(async()=>{
 const status=document.getElementById('biomass2010ExcessStatus');
 const ageBody=document.getElementById('biomass2010AgeTable');
 const coverageBody=document.getElementById('biomass2010CoverageTable');
 const volumeBody=document.getElementById('biomass2010VolumeTable');
 const fmt=(n,d=2)=>Number(n).toLocaleString('sv-SE',{maximumFractionDigits:d});
 const put=(body,values)=>{
  const tr=document.createElement('tr');
  for(const value of values){const td=document.createElement('td');td.textContent=value;tr.appendChild(td)}
  body.appendChild(tr);
 };
 try{
  const resp=await fetch('data/biomass_2010_excess_diagnostics.json',{cache:'no-store'});
  if(!resp.ok)throw Error('HTTP '+resp.status);
  const d=await resp.json();
  if(d.status!=='DESCRIPTIVE_2010_EXCESS_DIAGNOSTICS_NOT_HARMONIZED'||d.analysis_crs!=='EPSG:3006'||
     d.cell_size_m!==25||d.joint_valid_with_2010_age_volume.cells<=0)
     throw Error('Diagnostisk data har fel format, CRS eller rasterstorlek');
  const years=['2010','2015','2018'];
  const age=d.strata_age_as_of_2010.filter(x=>x.n>0);
  const bands=d.strata_volume_as_of_2010.filter(x=>x.n>0);
  for(const y of years){
    const b=d.paired_biomass_only[y];
    put(coverageBody,[y,fmt(b.own_area_ha,0),fmt(b.own_mean),fmt(b.paired_area_ha,0),fmt(b.paired_mean)]);
  }
  for(const x of age){
   const label=x.age_to===null?x.age_from+'+':x.age_from+'–'+x.age_to;
   put(ageBody,[label,fmt(x.area_ha,0),...years.map(y=>fmt(x.raw_means[y])),
     fmt(x.mean_2010_minus_2015)]);
  }
  for(const x of bands){
   put(volumeBody,[x.label,fmt(x.area_ha,0),...years.map(y=>fmt(x.raw_means[y]))]);
  }
  if(!window.Chart)throw Error('Chart.js kunde inte laddas');
  new Chart(document.getElementById('biomass2010AgeChart'),{
   type:'line',data:{labels:age.map(x=>x.age_to===null?x.age_from+'+':x.age_from+'–'+x.age_to),
     datasets:years.map((y,i)=>({
       label:y+' års biomassaraster',
       data:age.map(x=>x.n<50?null:x.raw_means[y]),
       borderColor:['#b85f28','#2b729e','#26764c'][i],
       backgroundColor:['#b85f28','#2b729e','#26764c'][i],
       pointRadius:4,borderWidth:2,spanGaps:false,tension:0
     }))},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
       scales:{x:{title:{display:true,text:'Beståndsålder enligt 2010 års raster (år)'}},
               y:{title:{display:true,text:'Medelråvärde (ej verifierad ton torrsubstans)'}}},
       plugins:{tooltip:{callbacks:{label:item=>item.dataset.label+': '+fmt(item.parsed.y)}}}}
  });
  status.textContent='Verifierad rasterdiagnostik: '+fmt(d.joint_valid_with_2010_age_volume.area_ha,2)+
   ' hektar med gemensamt giltiga biomassavärden, 2010 års beståndsålder och 2010 års virkesvolym. '+
   'Alla års värden i ålders- och volymtabellerna avser samma celler.';
 }catch(e){status.textContent='Diagnostiken kunde inte visas: '+e.message;status.classList.add('warning')}
})();