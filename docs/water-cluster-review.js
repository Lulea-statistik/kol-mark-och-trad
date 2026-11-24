"use strict";
(function(){
const byId=id=>document.getElementById(id);
const status=byId("mapStatus"),selInfo=byId("selectedInfo");
if(typeof L==="undefined" || typeof proj4==="undefined"){
  status.textContent="Kartbibliotek kunde inte laddas. Kontrollera nätverksåtkomsten.";return;
}
// EPSG:3006 SWEREF99 TM, verified from input raster. proj4 uses east,north.
proj4.defs("EPSG:3006","+proj=utm +zone=33 +ellps=GRS80 +units=m +no_defs +type=crs");
const toLatLng=(e,n)=>{const [lon,lat]=proj4("EPSG:3006","EPSG:4326",[e,n]);return [lat,lon];};
const osm=L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{
  attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>-bidragsgivare',maxZoom:19
});
const imagery=L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",{
  attribution:"Bilder © Esri och dataleverantörer. Aktuellt lager – inte bild från 2010.",maxZoom:19
});
const map=L.map("waterMap",{layers:[osm],zoomControl:true}).setView([65.59,22.15],9);
const groups=L.layerGroup().addTo(map);
let selected=null,entries=[],reviews={},markers=new Map(),boxes=new Map();
const storageKey="kol-mark-och-trad-water-cluster-review-v1";
try{reviews=JSON.parse(localStorage.getItem(storageKey)||"{}")||{};}catch(e){reviews={};}
const colorFor=id=>({unreviewed:"#a22326",uncertain:"#d88a28",water:"#21779c",land:"#21815a"})[(reviews[id]||{}).judgement||"unreviewed"]||"#a22326";
const fmt=v=>Number.isFinite(v)?v.toLocaleString("sv-SE",{minimumFractionDigits:2,maximumFractionDigits:2}):"–";
const escapeHtml=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function selectCluster(c){
  selected=c;
  const id=String(c.component_id),r=reviews[id]||{};
  const [lat,lon]=toLatLng(c.centroid_easting_epsg3006,c.centroid_northing_epsg3006);
  selInfo.innerHTML='<div class="metric"><strong>Kluster #'+c.component_id+'</strong> · '+c.cells+' celler · '+fmt(c.area_ha)+' ha</div>'+
    '<div class="metric">Biomassa 2010: <strong>'+fmt(c.mean_biomass_raw_2010)+'</strong><br>Biomassa 2018: <strong>'+fmt(c.mean_biomass_raw_2018)+'</strong><br>Virkesvolym 2010: <strong>'+fmt(c.mean_volume_raw_2010)+'</strong><br><small>Alla är ursprungliga modellråvärden.</small></div>'+
    '<div class="metric">EPSG:3006 (E, N):<br><code>'+fmt(c.centroid_easting_epsg3006)+', '+fmt(c.centroid_northing_epsg3006)+'</code><br>WGS84 (lat, lon): <code>'+lat.toFixed(6)+', '+lon.toFixed(6)+'</code></div>';
  byId("judgement").value=r.judgement||"unreviewed";
  byId("evidenceYear").value=r.evidenceYear||"";
  byId("evidence").value=r.evidence||"";
  byId("note").value=r.note||"";
  byId("saveStatus").textContent="";
  const b=boxes.get(id);if(b)map.fitBounds(b.getBounds().pad(1.2),{maxZoom:16});
  else map.setView([lat,lon],15);
}
function redraw(){
  groups.clearLayers();markers.clear();boxes.clear();
  const filter=byId("filter").value;
  let shown=0;
  for(const c of entries){
    const id=String(c.component_id);
    const state=(reviews[id]||{}).judgement||"unreviewed";
    if(filter!=="all"&&state!==filter)continue;
    const [west,south,east,north]=c.bounds_epsg3006;
    const bounds=L.latLngBounds(toLatLng(west,south),toLatLng(east,north));
    const rectangle=L.rectangle(bounds,{color:colorFor(id),weight:2,fillOpacity:.07});
    rectangle.addTo(groups);
    boxes.set(id,rectangle);
    const [lat,lon]=toLatLng(c.centroid_easting_epsg3006,c.centroid_northing_epsg3006);
    const point=L.circleMarker([lat,lon],{radius:Math.min(14,5+Math.sqrt(c.cells)*2),color:"#fff",weight:2,fillColor:colorFor(id),fillOpacity:.94});
    point.bindTooltip("Kluster #"+id+" · "+c.cells+" celler · råvärde 2010: "+fmt(c.mean_biomass_raw_2010));
    point.on("click",()=>selectCluster(c));rectangle.on("click",()=>selectCluster(c));
    point.addTo(groups);markers.set(id,point);shown++;
  }
  status.textContent=shown+" av "+entries.length+" publicerade kluster visas. Totalt finns 63 kluster.";
}
byId("basemap").addEventListener("change",e=>{
  if(e.target.value==="imagery"){map.removeLayer(osm);imagery.addTo(map);}
  else {map.removeLayer(imagery);osm.addTo(map);}
});
byId("filter").addEventListener("change",redraw);
byId("save").addEventListener("click",()=>{
  if(!selected){byId("saveStatus").textContent="Välj först ett kluster.";return;}
  const id=String(selected.component_id);
  const judgement=byId("judgement").value;
  const evidenceYear=byId("evidenceYear").value.trim();
  const evidence=byId("evidence").value.trim();
  const note=byId("note").value.trim();
  if(judgement==="water"&&!evidence){
    byId("saveStatus").textContent="Ange historisk källa innan du markerar vatten ca 2010 som verifierat.";
    return;
  }
  reviews[id]={judgement,evidenceYear,evidence,note,updatedAt:new Date().toISOString()};
  try{localStorage.setItem(storageKey,JSON.stringify(reviews));byId("saveStatus").textContent="Sparat lokalt i webbläsaren.";}
  catch(e){byId("saveStatus").textContent="Webbläsaren tillåter inte lokal lagring. Exportera CSV för att behålla anteckningar.";}
  redraw();
});
function csvCell(v){return '"'+String(v===undefined||v===null?"":v).replace(/"/g,'""')+'"';}
byId("export").addEventListener("click",()=>{
  const headers=["cluster_id","cells","area_ha","easting_epsg3006","northing_epsg3006","biomass_raw_2010","biomass_raw_2018","volume_raw_2010","judgement","evidence_year","evidence","note","updated_at"];
  const rows=[headers.join(";")];
  for(const c of entries){
    const r=reviews[String(c.component_id)]||{};
    rows.push([c.component_id,c.cells,c.area_ha,c.centroid_easting_epsg3006,c.centroid_northing_epsg3006,c.mean_biomass_raw_2010,c.mean_biomass_raw_2018,c.mean_volume_raw_2010,r.judgement||"unreviewed",r.evidenceYear||"",r.evidence||"",r.note||"",r.updatedAt||""].map(csvCell).join(";"));
  }
  const blob=new Blob(["\ufeff"+rows.join("\r\n")],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob),a=document.createElement("a");
  a.href=url;a.download="nmd2018-vattenkluster-granskning.csv";document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
});
fetch("data/nmd2018-water-clusters-review-epsg3006.json",{cache:"no-store"})
.then(r=>{if(!r.ok)throw Error("HTTP "+r.status);return r.json();})
.then(d=>{
  if(d.crs!=="EPSG:3006"||!Array.isArray(d.clusters)||d.clusters.length!==30||d.total_clusters!==63||d.total_cells!==115)throw Error("Källdata matchar inte den verifierade PR92-analysen");
  entries=d.clusters;
  if(!entries.every(c=>Number.isFinite(c.centroid_easting_epsg3006)&&Number.isFinite(c.centroid_northing_epsg3006)&&c.bounds_epsg3006.length===4))throw Error("Ogiltiga koordinater i källdata");
  redraw();
  const bounds=L.latLngBounds(entries.map(c=>toLatLng(c.centroid_easting_epsg3006,c.centroid_northing_epsg3006)));
  map.fitBounds(bounds.pad(.17),{maxZoom:11});
  selectCluster(entries[0]);
})
.catch(e=>{status.textContent="Kartan kan inte läsa verifierad klusterdata: "+e.message;});
})();