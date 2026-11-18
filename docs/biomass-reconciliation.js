'use strict';
(async()=>{
 const status=document.getElementById('audit-status');
 const fmt=(n,d=0)=>Number(n).toLocaleString('sv-SE',{maximumFractionDigits:d});
 const $=id=>document.getElementById(id);
 let records=[];
 const isValid=v=>typeof v==='number'&&Number.isFinite(v);
 function group(assessment){
  const a=records.filter(r=>r.assessment===assessment);
  return {count:a.length,positive:a.filter(r=>r.known&&r.raw>0).length,zero:a.filter(r=>r.known&&r.raw===0).length,
    unknown:a.filter(r=>!r.known).length,sum:a.reduce((s,r)=>s+(r.known&&r.raw>0?r.raw:0),0)};
 }
 function exportCsv(){
  const fraction=Number($('reduction').value)/100;
  const header=['east_epsg3006','north_epsg3006','reported_context','manual_plausibility_assessment','original_raw_biomass','scenario_raw_biomass','scenario_delta_raw','scenario_assumption','independently_confirmed'];
  const rows=records.map(r=>{
   const reduced=r.assessment==='suspected_false_positive'&&r.known&&r.raw>0;
   const next=r.known?(reduced?r.raw*(1-fraction):r.raw):null;
   return [r.x,r.y,r.context,r.assessment,r.known?r.raw:'',next===null?'':next,r.known?next-r.raw:'',
     reduced?'hypothetical_reduction_not_a_correction':'unchanged_or_unknown',false];
  });
  const csv=[header,...rows].map(row=>row.map(v=>'"'+String(v).replaceAll('"','""')+'"').join(',')).join('\r\n')+'\r\n';
  const url=URL.createObjectURL(new Blob(['\ufeff',csv],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download='biomassa_granskning_fore_efter_scenario_epsg3006.csv';a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 function render(){
  const suspected=group('suspected_false_positive'),plausible=group('plausible_biomass');
  $('n-reviewed').textContent=fmt(records.length);$('n-suspect').textContent=fmt(suspected.count);
  $('n-plausible').textContent=fmt(plausible.count);$('n-positive').textContent=fmt(suspected.positive);
  const table=$('assessment-rows');table.replaceChildren();
  for(const [label,a]of [['Misstänkt orimlig biomassa',suspected],['Rimlig förekomst av skogsbiomassa',plausible]]){
   const tr=document.createElement('tr');for(const v of [label,fmt(a.count),fmt(a.positive),fmt(a.zero),fmt(a.unknown),fmt(a.sum)]){
    const td=document.createElement('td');td.textContent=v;tr.appendChild(td);
   }table.appendChild(tr);
  }
  const fraction=Number($('reduction').value)/100;
  $('reduction-label').textContent=fmt(fraction*100)+' %';
  $('scenario-delta').textContent='−'+fmt(suspected.sum*fraction,2)+' råvärdesenheter';
  $('scenario-remainder').textContent=fmt(suspected.sum*(1-fraction),2)+' råvärdesenheter';
 }
 try{
  const response=await fetch('data/biomass_review_snapshot.geojson',{cache:'no-store'});
  if(!response.ok)throw Error('HTTP '+response.status);
  const d=await response.json();
  if(d.metadata?.input_source_crs!=='EPSG:3006')throw Error('Förväntat käll-CRS EPSG:3006 saknas');
  const visited=new Set();
  records=d.features.filter(f=>f.properties?.origins?.includes('user_observation')).map(f=>{
   const p=f.properties,o=p.user_observation||p,k=p.east_epsg3006+','+p.north_epsg3006;
   if(visited.has(k))throw Error('Dubblerad ursprungscell: '+k);
   visited.add(k);
   return {x:p.east_epsg3006,y:p.north_epsg3006,context:o.reported_context,
    assessment:o.manual_plausibility_assessment,known:isValid(p.raw_biomass),raw:p.raw_biomass};
  });
  if(records.length!==d.metadata.manual_observations_count)throw Error('Antalet granskningsposter motsvarar inte kartmetadata');
  if(records.some(r=>!['suspected_false_positive','plausible_biomass'].includes(r.assessment)))throw Error('Okänd manuell bedömning');
  status.textContent='Läste '+fmt(records.length)+' unika individuellt granskade koordinater. Rastergranskning senast '+d.metadata.audit_timestamp+'; manuella annoteringar uppdaterade utan rasteromräkning.';
  $('reduction').addEventListener('input',render);
  $('download-csv').addEventListener('click',exportCsv);
  render();
 }catch(e){status.textContent='Kunde inte skapa avstämningen: '+e.message;$('download-csv').disabled=true;}
})();

(async()=>{
 const status=document.getElementById('verified-corrections-status');
 const count=document.getElementById('verified-corrections-count');
 const delta=document.getElementById('verified-corrections-delta');
 const nodata=document.getElementById('verified-corrections-nodata');
 try{
  const resp=await fetch('data/biomass_verified_corrections.json',{cache:'no-store'});
  if(!resp.ok)throw Error('HTTP '+resp.status);
  const overlay=await resp.json();
  if(overlay.schema_version!==1||overlay.source_crs!=='EPSG:3006'||!Array.isArray(overlay.corrections))
   throw Error('Okänt korrigeringsformat eller koordinatsystem');
  let numericDelta=0,nodataCount=0,keys=new Set();
  for(const row of overlay.corrections){
   const key=row.east_epsg3006+','+row.north_epsg3006;
   if(keys.has(key))throw Error('Dubbel korrigering för '+key);
   keys.add(key);
   if(row.verified!==true||!row.evidence_reference||!row.verification_date||!row.verifier)
    throw Error('Korrigeringsbeslut utan tillräcklig verifiering: '+key);
   if(!['replace_value','set_zero','set_nodata'].includes(row.decision))
    throw Error('Ogiltigt korrigeringsbeslut: '+key);
   if(row.decision==='set_nodata')nodataCount++;
   // A delta is computed only by the source-aware validator, not from unverified JS assumptions.
  }
  count.textContent=overlay.corrections.length.toLocaleString('sv-SE');
  nodata.textContent=nodataCount.toLocaleString('sv-SE');
  delta.textContent=overlay.corrections.length===0?'0 (inga beslut)':'Se validerad avstämning';
  status.textContent=overlay.corrections.length===0
    ?'Inga oberoende verifierade korrigeringar är registrerade. Rastervärden är oförändrade.'
    :'Det finns verifierade korrigeringsbeslut. Kontrollera deras cellvisa beräkning med scripts/validate_biomass_corrections.py; inga rasterfiler skrivs om.';
 }catch(e){
  status.textContent='Kunde inte kontrollera korrigeringslagret: '+e.message;
  count.textContent='Okänt';delta.textContent='Okänt';nodata.textContent='Okänt';
 }
})();
