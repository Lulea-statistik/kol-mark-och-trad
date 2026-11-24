'use strict';
(async()=>{
 const area=document.getElementById('componentScenario');
 if(!area)return;
 const slider=document.getElementById('rootShootRatio'),value=document.getElementById('rootShootRatioValue');
 const tbody=document.getElementById('componentScenarioRows');
 const table2=document.getElementById('componentClassRows');
 const status=document.getElementById('componentScenarioStatus');
 const n=(v,d=2)=>Number(v).toLocaleString('sv-SE',{minimumFractionDigits:d,maximumFractionDigits:d});
 const ref={
  all:{2010:76.88742364943045,2015:64.73253959370062,2018:69.3290996204125},
  productive:{2010:80.89917208595149,2015:70.78269969146817,2018:76.04325888776853},
  nonforest:{2010:55.62615695821283,2015:27.873794384480757,2018:28.281096393171826},
  unproductive:{2010:60.955598206326265,2015:50.54966455749692,2018:53.88543074414971}
 };
 const addRow=(body,arr)=>{
  const tr=document.createElement('tr');
  for(const v of arr){const td=document.createElement('td');td.textContent=v;tr.appendChild(td)}
  body.appendChild(tr);
 };
 const update=()=>{
  const r=Number(slider.value)/100;
  value.textContent=n(r,2);
  tbody.replaceChildren();
  // Assumed: 2010 observed above+below, 2015 and 2018 above only.
  // No unit conversion or model-bias correction is applied.
  for(const y of [2010,2015,2018]){
   const raw=ref.all[y],above=y===2010?raw/(1+r):raw;
   const total=y===2010?raw:raw*(1+r);
   addRow(tbody,[String(y),n(raw),n(above),n(total)]);
  }
  table2.replaceChildren();
  for(const [key,label] of [['productive','Produktiv skogsmark'],['nonforest','Ej skogsmark'],['unproductive','Improduktiv skogsmark']]){
   const d=ref[key];
   addRow(table2,[label,n(d[2010]/(1+r)),n(d[2015]),n(d[2018]),n(d[2010]/(1+r)-d[2018])]);
  }
 };
 try{
  const resp=await fetch('data/biomass_2010_excess_diagnostics.json',{cache:'no-store'});
  if(!resp.ok)throw Error('diagnostic JSON HTTP '+resp.status);
  const d=await resp.json();
  if(d.analysis_crs!=='EPSG:3006'||d.cell_size_m!==25||d.paired_biomass_only['2010'].paired_n!==2456410){
   throw Error('Analysens referenspopulation stämmer inte');
  }
  for(const y of [2010,2015,2018]){
   if(Math.abs(ref.all[y]-d.paired_biomass_only[String(y)].paired_mean)>1e-6)
    throw Error('Referensmedel för '+y+' skiljer sig från publicerad rasterdiagnostik');
  }
  slider.addEventListener('input',update);
  update();
  status.textContent='Scenarierna använder verifierade medelråvärden på samma 153 525,625 ha, men rot/stubbandelen är ett antagande.';
 }catch(error){
  status.textContent='Scenariot kan inte kontrolleras mot publicerade data: '+error.message;
  slider.disabled=true;
  tbody.replaceChildren();
  table2.replaceChildren();
 }
})();
