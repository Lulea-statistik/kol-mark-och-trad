'use strict';
const map=L.map('map').setView([65.6,22.1],8);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:18}).addTo(map);
let boundary=null,overlay=null,manifest={layers:{}},previews={layers:{}};
async function json(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(url+' (HTTP '+r.status+')');return r.json();}
function show(){
 const key=document.getElementById('layer').value,isPreview=key.startsWith('preview_');
 const d=isPreview?previews.layers?.[key.slice(8)]:manifest.layers?.[key];
 if(overlay){map.removeLayer(overlay);overlay=null;}
 const availability=document.getElementById('availability'),summary=document.getElementById('summary');
 const units=document.getElementById('units'),quality=document.getElementById('quality');
 if(!d?.image||!d?.bounds||!Array.isArray(d.bounds)){
   availability.textContent='Ännu inga verifierade rasterdata för detta lager.';
   summary.textContent='Kartan visar enbart Luleås avgränsning. Inget kolförråd har beräknats eller interpolerats.';
   units.textContent='';quality.textContent='';return;
 }
 overlay=L.imageOverlay(d.image,d.bounds,{opacity:.8,interactive:false}).addTo(map);
 if(isPreview){
  availability.textContent='Verkliga rasterpixlar från SLU; FÖRHANDSVISNING utan verifierad kolenhet.';
  summary.textContent='Relativ färgskala inom detta lager. Inga ton C eller CO₂ har beräknats. Färgerna mellan SOC och Stock_All är inte direkt jämförbara.';
  units.textContent='Fysisk enhet: ännu inte verifierad. Kartan visar endast variation i källans råvärden.';
  quality.textContent='Källraster: '+d.source_crs+' · Webbvisning: EPSG:3857 · Endast Luleå kommun (arbetsgräns).';
  return;
 }
 availability.textContent='Bearbetat raster tillgängligt · '+(d.source||'källa ej angiven');
 const complete=d.coverage_pct_of_municipality!=null&&Number(d.coverage_pct_of_municipality)>=99.5;
 summary.textContent=d.total_tonnes_C!=null
   ?(complete?'Beräknat förråd inom Luleå kommun: ':'Delsumma för datatäckt del av Luleå kommun: ')+Number(d.total_tonnes_C).toLocaleString('sv-SE',{maximumFractionDigits:0})+' ton C.'
   :'Raster publicerat; ingen verifierad totalsumma.';
 if(d.coverage_pct_of_municipality!=null)summary.textContent+=' Rastertäckning: '+Number(d.coverage_pct_of_municipality).toLocaleString('sv-SE',{maximumFractionDigits:1})+' % av kommunytan.';
 units.textContent='Kartans enhet: '+(d.units||'ej angiven');
 quality.textContent='Metod: '+(d.method||'ej angiven')+' · Källa CRS: '+(d.source_crs||'ej angivet')+'.';
}
async function init(){
 try{const b=await json('data/lulea_boundary.geojson');boundary=L.geoJSON(b,{style:{color:'#174f3e',weight:2,fillColor:'#327d63',fillOpacity:.07}}).addTo(map);map.fitBounds(boundary.getBounds(),{padding:[15,15]});}
 catch(e){document.getElementById('availability').textContent='Kunde inte läsa kommungränsen: '+e.message;}
 try{manifest=await json('data/layers.json');}catch(e){document.getElementById('availability').textContent='Lagermetadata saknas: '+e.message;}
 try{previews=await json('data/preview/preview_layers.json');}catch(e){console.info('Förhandskartorna är ännu inte publicerade:',e.message);}
 show();
}
document.getElementById('layer').addEventListener('change',show);init();