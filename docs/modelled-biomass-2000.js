'use strict';
(async()=>{
 const status=document.getElementById('modelStatus');
 const fmt=(v,d=2)=>Number(v).toLocaleString('sv-SE',{maximumFractionDigits:d});
 try{
  const response=await fetch('data/modelled_biomass_series_2000_2018.json',{cache:'no-store'});
  if(!response.ok)throw Error('Modellfil saknas, HTTP '+response.status);
  const data=await response.json();
  if(data.status!=='EXPLORATORY_MODEL_NOT_A_VALIDATED_BIOMASS_TIMESERIES'
   || data.comparison_crs!=='EPSG:3006'||data.years?.length!==5)throw Error('Oväntat modellformat');
  const rows=data.years;
  document.getElementById('support').textContent='Gemensam giltig yta: '+fmt(data.common_valid_area_ha,1)+' hektar ('+fmt(data.common_valid_cells,0)+' rasterceller). 2010 års råkonverteringsfaktor: '+fmt(data.calibration_factor_raw_biomass_per_raw_volume,4)+'.';
  for(const row of rows){
    const tr=document.createElement('tr');
    for(const val of [String(row.year),fmt(row.raw_mean_on_common_support),
      row.status.startsWith('MODELLED')?'Skattat från virkesvolym (2010-kalibrerat)':'Ursprungligt biomassaraster (olika produktgenerationer)',
      row.scenario_low_minus_20pct==null?'–':fmt(row.scenario_low_minus_20pct)+'–'+fmt(row.scenario_high_plus_20pct)]){
      const cell=document.createElement('td');cell.textContent=val;tr.appendChild(cell);
    }
    document.getElementById('modelRows').appendChild(tr);
  }
  if(!window.Chart)throw Error('Diagramkomponenten kunde inte laddas');
  const obs=rows.map(r=>r.year>=2010?r.raw_mean_on_common_support:null);
  const inferred=rows.map(r=>r.year<=2010?r.raw_mean_on_common_support:null);
  new Chart(document.getElementById('modelChart'),{
   type:'line',data:{labels:rows.map(r=>String(r.year)),datasets:[
    {label:'Beräknat från volym (2000–2005)',data:inferred,borderColor:'#b36d27',backgroundColor:'#b36d27',borderDash:[7,4],borderWidth:3,pointRadius:5,spanGaps:false},
    {label:'Biomassaraster 2010–2018 (ej metodharmoniserade)',data:obs,borderColor:'#18647a',backgroundColor:'#18647a',borderWidth:3,pointRadius:5,spanGaps:false},
    {label:'Känslighet −20 % (endast modellår)',data:rows.map(r=>r.scenario_low_minus_20pct),borderColor:'#b36d27',borderDash:[2,5],pointRadius:0,borderWidth:1,spanGaps:false},
    {label:'Känslighet +20 % (endast modellår)',data:rows.map(r=>r.scenario_high_plus_20pct),borderColor:'#b36d27',borderDash:[2,5],pointRadius:0,borderWidth:1,spanGaps:false}
   ]},options:{responsive:true,maintainAspectRatio:false,plugins:{tooltip:{callbacks:{label:i=>i.dataset.label+': '+fmt(i.parsed.y)} }},
   scales:{y:{title:{display:true,text:'Medelråvärde (inte verifierade ton)'},beginAtZero:true},x:{title:{display:true,text:'Referensår (ej exakta observationsdatum)'}}}}
  });
  status.textContent='Data hämtad från kontrollerad GitHub Actions-körning. Modellen är preliminär och ska inte redovisas som faktisk biomassaförändring.';
 }catch(err){status.textContent='Kunde inte visa modellserien: '+err.message;}
})();