'use strict';
const map=L.map('map').setView([65.6,22.1],8);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:18}).addTo(map);
let boundary=null,overlay=null,manifest={layers:{}};
async function json(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(url+' (HTTP '+r.status+')');return r.json();}
function show(){
 const key=document.getElementById('layer').value,d=manifest.layers?.[key];
 if(overlay){map.removeLayer(overlay);overlay=null;}
 const availability=document.getElementById('availability'),summary=document.getElementById('summary');
 const units=document.getElementById('units'),quality=document.getElementById('quality');
 if(!d?.image||!d?.bounds||!Array.isArray(d.bounds)){
   availability.textContent='Ännu inga verifierade rasterdata för detta lager.';
   summary.textContent='Kartan visar enbart Luleås avgränsning. Inget kolförråd har beräknats eller interpolerats.';
   units.textContent='';quality.textContent='';return;
 }
 overlay=L.imageOverlay(d.image,d.bounds,{opacity:.8,interactive:false}).addTo(map);
 availability.textContent='Bearbetat raster tillgängligt · '+(d.source||'källa ej angiven');
 summary.textContent=d.total_tonnes_C!=null?'Beräknat förråd: '+Number(d.total_tonnes_C).toLocaleString('sv-SE',{maximumFractionDigits:0})+' ton C.':'Raster publicerat; ingen verifierad totalsumma.';
 units.textContent='Kartans enhet: '+(d.units||'ej angiven');
 quality.textContent='Metod: '+(d.method||'ej angiven')+' · Källa CRS: '+(d.source_crs||'ej angivet')+'.';
}
async function init(){
 try{const b=await json('data/lulea_boundary.geojson');boundary=L.geoJSON(b,{style:{color:'#174f3e',weight:2,fillColor:'#327d63',fillOpacity:.07}}).addTo(map);map.fitBounds(boundary.getBounds(),{padding:[15,15]});}
 catch(e){document.getElementById('availability').textContent='Kunde inte läsa kommungränsen: '+e.message;}
 try{manifest=await json('data/layers.json');}catch(e){document.getElementById('availability').textContent='Lagermetadata saknas: '+e.message;}
 show();
}
document.getElementById('layer').addEventListener('change',show);init();