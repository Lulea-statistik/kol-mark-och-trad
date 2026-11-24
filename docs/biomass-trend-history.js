'use strict';
(async()=>{
 const status=document.getElementById('historicBiomassStatus');
 const area=document.getElementById('historicBiomassArea');
 const table=document.getElementById('historicBiomassTable');
 const ageInfo=document.getElementById('historicAgeNote');
 const fmt=(v,d=2)=>Number(v).toLocaleString('sv-SE',{maximumFractionDigits:d});
 try{
  const [mainResponse,ageResponse]=await Promise.all([
   fetch('data/modelled_biomass_series_2000_2018.json',{cache:'no-store'}),
   fetch('data/age_adjusted_biomass_2000_2005.json',{cache:'no-store'})
  ]);
  if(!mainResponse.ok||!ageResponse.ok)throw Error('Datatabellen gick inte att hämta (HTTP '+mainResponse.status+'/'+ageResponse.status+')');
  const primary=await mainResponse.json(),alternative=await ageResponse.json();
  if(primary.status!=='EXPLORATORY_MODEL_NOT_A_VALIDATED_BIOMASS_TIMESERIES'||
     primary.comparison_crs!=='EPSG:3006'||primary.target_cell_m!==25 ||
     primary.years?.length!==5 || primary.years.map(v=>v.year).join(',')!=='2000,2005,2010,2015,2018')
    throw Error('Fel på den granskade femåriga biomassaserien');
  if(alternative.status!=='PROVISIONAL_AGE_DEPENDENT_RAW_BIOMASS_MODEL'||
     alternative.grid_crs!=='EPSG:3006' || alternative.historical_results?.length!==3)
    throw Error('Fel på den åldersbaserade jämförelsemodellen');
  const rows=primary.years;
  const years=rows.map(r=>String(r.year));
  const estimates=rows.map(r=>r.year<=2010?r.raw_mean_on_common_support:null);
  const observed=rows.map(r=>r.year>=2010?r.raw_mean_on_common_support:null);
  if(!window.Chart)throw Error('Chart.js kunde inte laddas');
  new Chart(document.getElementById('historicBiomassChart'),{
    type:'line',
    data:{labels:years,datasets:[
      {label:'Skattad biomassa från virkesvolym (2000, 2005)',data:estimates,
       borderColor:'#b77a30',backgroundColor:'#b77a30',borderWidth:3,
       borderDash:[7,5],pointRadius:6,pointHoverRadius:8,tension:0},
      {label:'Arkiverade biomassaraster (2010, 2015, 2018)',data:observed,
       borderColor:'#17667d',backgroundColor:'#17667d',borderWidth:3,
       pointRadius:6,pointHoverRadius:8,tension:0}
    ]},
    options:{responsive:true,maintainAspectRatio:false,interaction:{intersect:false,mode:'nearest'},
      plugins:{tooltip:{callbacks:{
       title:items=>items[0].label+(Number(items[0].label)<2010?' – skattat':' – rasterprodukt'),
       label:item=>item.dataset.label+': '+fmt(item.parsed.y)+' medelråvärde (ej ton)'
      }}},
      scales:{y:{beginAtZero:true,title:{display:true,text:'Medelråvärde, inte ton torr biomassa'}},
       x:{title:{display:true,text:'Kartår / omdrev'}}}}
  });
  for(const r of rows){
   const tr=document.createElement('tr');
   const type=r.year<2010?'Skattat från SLU:s virkesvolym (2010-kalibrerat)':r.year===2010?'SLU biomassaraster':'Biomassaraster från annan produktgeneration';
   const range=r.scenario_low_minus_20pct==null?'–':fmt(r.scenario_low_minus_20pct)+'–'+fmt(r.scenario_high_plus_20pct)+'*';
   for(const txt of [String(r.year),fmt(r.raw_mean_on_common_support),type,range]){
    const td=document.createElement('td');td.textContent=txt;tr.appendChild(td);
   }
   table.appendChild(tr);
  }
  area.textContent='Samma geografiska beräkningsyta för alla fem datapunkter: '+fmt(primary.common_valid_area_ha,2)+
   ' hektar ('+fmt(primary.common_valid_cells,0)+' gemensamt giltiga 25-metersceller) efter fullständig rasterreprojicering till EPSG:3006.';
  const a=alternative.historical_results;
  const get=y=>a.find(r=>r.year===y);
  ageInfo.textContent='Alternativ åldersbaserad volymomräkning ger för 2000 '+
    fmt(get(2000).age_based_raw_mean)+' och 2005 '+fmt(get(2005).age_based_raw_mean)+
    ' medelråvärde, mot '+fmt(get(2000).global_factor_raw_mean)+' respektive '+
    fmt(get(2005).global_factor_raw_mean)+' med en global faktor på samma åldersmodells-yta. '+
    'Åldersmodellen gäller '+fmt(alternative.common_valid_area_ha,2)+' hektar och kan INTE ritas in i huvudkurvan, som gäller en annan gemensam yta.';
  status.textContent='Beräkningen är verifierad från arkiverade källraster. Åren 2000 och 2005 är skattningar från virkesvolym, övriga år är råvärden ur biomassaprodukter. Produkterna är ännu inte metodharmoniserade.';
 }catch(error){
   status.textContent='Det gick inte att visa tidsserien: '+error.message;
   status.classList.add('warning');
 }
})();