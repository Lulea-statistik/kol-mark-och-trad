/* Read-only sample map. Pixel polygons were generated from the source raster affine
   in EPSG:3006, not synthesized from transformed bounds or rounded corners. */
(function(){
  "use strict";
  const map=L.map("map").setView([65.572,22.171],14);
  const osm=L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{
    maxZoom:19,attribution:"© OpenStreetMap contributors"
  });
  const imagery=L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",{
    maxZoom:19,attribution:"Esri World Imagery; acquisition date varies"
  });
  osm.addTo(map);
  const kind=document.getElementById("kind");
  const stratum=document.getElementById("stratum");
  const status=document.getElementById("review-status");
  let data=null;
  let selected=L.featureGroup().addTo(map);
  const harbor=L.latLngBounds([[65.571144,22.171025],[65.572057,22.170352]]).pad(.8);
  const nice={
    water_core_positive:"Sammanhängande vatten",
    water_edge_positive:"Vattenkant",
    building_positive:"Byggnad",
    road_positive:"Väg",
    developed_positive:"Annan exploaterad mark",
    high_other_positive:"Höga värden, annan mark",
    ordinary_positive:"Oflaggad biomassa",
    zero_control:"Nollvärde"
  };
  const text=v=>String(v??"");
  const safe=v=>text(v).replace(/[&<>"']/g,x=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[x]));
  function props(p){
    if(p.origin==="harbor_hypothesis"){
      return "<strong>"+safe(p.name)+"</strong><p>Hypotes: isbrytare eller andra höga fartyg kan påverka höjdmodeller. Inte verifierat som biomassaavvikelse.</p><p>Kontrollera datum för laserskanning och ortofoto.</p><p>Koordinater i grader, antagna EPSG:4326.</p>";
    }
    return "<strong>"+safe(nice[p.stratum]||p.flag_rules||p.origin)+"</strong>"+
      "<p>Råvärde: "+safe(p.raw_biomass)+" (ej verifierad fysisk enhet)<br>NMD2018: "+safe(p.nmd_code)+
      "<br>Centrum (EPSG:3006): "+safe(p.east_epsg3006)+", "+safe(p.north_epsg3006)+
      "<br>Urval: "+safe(p.origins.join(" + "))+"<br>Status: ej granskad</p>"+
      "<p>Bedöm mot daterat ortofoto och andra oberoende geodata; registrera manuellt i CSV.</p>";
  }
  function render(){
    if(!data)return;
    selected.clearLayers();
    let count=0;
    for(const feature of data.features){
      const p=feature.properties;
      if(kind.value!=="all"&&!p.origins.includes(kind.value))continue;
      if(stratum.value!=="all"&&p.stratum!==stratum.value)continue;
      const point=p.origin==="harbor_hypothesis";
      const layer=L.geoJSON(feature,{
        style:()=>({color:point?"#be123c":(p.origins.includes("risk")?"#ea580c":"#2563eb"),
          weight:point?2:2,fillOpacity:.23}),
        pointToLayer:(_f,ll)=>L.circleMarker(ll,{radius:9,color:"#be123c",fillColor:"#be123c",fillOpacity:.8})
      });
      layer.bindPopup(props(p),{maxWidth:340});
      selected.addLayer(layer);count++;
    }
    status.textContent="Visar "+count+" geografiska objekt. Inga av dem är oberoende verifierade fel. Underlag från "+safe(data.metadata.audit_timestamp||"senaste audit")+".";
  }
  kind.addEventListener("change",render);
  stratum.addEventListener("change",render);
  document.getElementById("basemap").addEventListener("change",e=>{
    map.removeLayer(osm);map.removeLayer(imagery);
    (e.target.value==="imagery"?imagery:osm).addTo(map);
  });
  document.getElementById("allMap").addEventListener("click",()=>{
    if(data&&selected.getLayers().length)map.fitBounds(selected.getBounds().pad(.1));
  });
  document.getElementById("harborMap").addEventListener("click",()=>map.fitBounds(harbor));
  fetch("data/biomass_review_snapshot.geojson",{cache:"no-store"})
    .then(r=>{if(!r.ok)throw Error("Kartan saknar publicerad granskningsexport");return r.json();})
    .then(v=>{
      if(v.type!=="FeatureCollection"||!Array.isArray(v.features))throw Error("Ogiltig kartfil");
      data=v;
      const names=new Set(v.features.map(f=>f.properties.stratum).filter(Boolean));
      for(const name of names){const option=document.createElement("option");option.value=name;option.textContent=nice[name]||name;stratum.appendChild(option);}
      render();
      map.fitBounds(harbor);
    })
    .catch(err=>{
      status.textContent="Granskningsdata är ännu inte publicerade. "+err.message+"; kör NMD2018-flödet på main efter att PR:n slagits samman.";
      L.circleMarker([65.571144,22.171025],{radius:9,color:"#be123c"}).bindPopup("Hamnposition A – ej verifierad").addTo(map);
      L.circleMarker([65.572057,22.170352],{radius:9,color:"#be123c"}).bindPopup("Hamnposition B – ej verifierad").addTo(map);
    });
})();