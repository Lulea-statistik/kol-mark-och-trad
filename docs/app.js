'use strict';
(() => {
  const status=document.getElementById('availability');
  const summary=document.getElementById('summary');
  const units=document.getElementById('units');
  const quality=document.getElementById('quality');
  const select=document.getElementById('layer');
  const opacity=document.getElementById('overlayOpacity');
  const opacityLabel=document.getElementById('opacityValue');
  const showRaster=document.getElementById('showRaster');
  const zoomButton=document.getElementById('zoomLulea');
  const mapNode=document.getElementById('map');
  const error=(message)=>{status.textContent=message;status.classList.add('warning')};
  if(typeof window.L==='undefined'){
    error('Kartbiblioteket Leaflet kunde inte laddas. Kontrollera nätverksanslutningen och ladda om sidan.');
    mapNode.textContent='Kartan kan inte visas just nu – Leaflet saknas.';
    return;
  }
  const map=L.map('map',{preferCanvas:true,zoomControl:true}).setView([65.59,22.15],9);
  const osm=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
    attribution:'© OpenStreetMap contributors',maxZoom:19,maxNativeZoom:19,
    crossOrigin:true
  }).addTo(map);
  const layersControl=L.control.layers(
    {'OpenStreetMap':osm},
    {},
    {collapsed:false,position:'topright'}
  ).addTo(map);
  osm.on('tileerror',()=>{error('OpenStreetMap kunde inte ladda alla kartplattor. Kontrollera uppkopplingen.')});
  let municipality=null, overlay=null, overlayName=null, manifest={layers:{}}, previews={layers:{}};
  const bounds=L.latLngBounds([[65.06965,21.33572],[66.28329,23.13835]]);
  function fitMunicipality(){
    if(municipality&&municipality.getBounds().isValid()){
      map.fitBounds(municipality.getBounds(),{padding:[18,18],maxZoom:10});
    }else{
      map.fitBounds(bounds,{padding:[18,18],maxZoom:10});
    }
  }
  zoomButton.addEventListener('click',fitMunicipality);
  opacity.addEventListener('input',()=>{
    opacityLabel.textContent=opacity.value+' %';
    if(overlay)overlay.setOpacity(Number(opacity.value)/100);
  });
  showRaster.addEventListener('change',()=>render());
  async function getJson(url){
    const res=await fetch(url,{cache:'no-store'});
    if(!res.ok)throw Error('HTTP '+res.status);
    return res.json();
  }
  function removeOverlay(){
    if(overlay){
      map.removeLayer(overlay);
      if(overlayName)layersControl.removeLayer(overlay);
    }
    overlay=null;overlayName=null;
  }
  function render(){
    removeOverlay();
    const key=select.value;
    const isPreview=key.startsWith('preview_');
    const record=isPreview?previews.layers?.[key.slice(8)]:manifest.layers?.[key];
    if(!record?.image||!Array.isArray(record.bounds)){
      status.textContent='OpenStreetMap visas. Det valda datalagret är ännu inte tillgängligt.';
      status.classList.remove('warning');
      summary.textContent='Endast baskartan och kommungränsen visas. Inga kolvärden har beräknats för valt lager.';
      units.textContent='';quality.textContent='';
      return;
    }
    if(!showRaster.checked){
      status.textContent='OpenStreetMap visas utan rasteröverlägg.';
      status.classList.remove('warning');
      summary.textContent='Aktivera ”Visa markkolslagret” för att lägga SLU:s raster ovanpå baskartan.';
      units.textContent='';quality.textContent='';
      return;
    }
    // Raster source has already been fully reprojected to EPSG:3857,
    // then its geographic bounding coordinates are supplied to Leaflet.
    // Never put a source-CRS raster into imageOverlay using merely transformed bounds.
    overlay=L.imageOverlay(record.image,record.bounds,{
      opacity:Number(opacity.value)/100,
      interactive:false,
      alt:'SLU:s kommunmaskade rasterförhandskarta',
      crossOrigin:true,
      errorOverlayUrl:''
    });
    overlay.once('error',()=>{
      error('SLU:s rasterbild kunde inte laddas. OpenStreetMap visas fortfarande. Försök ladda om sidan.');
    });
    overlay.addTo(map);
    overlayName=select.selectedOptions[0]?.textContent||'SLU raster';
    layersControl.addOverlay(overlay,overlayName);
    status.classList.remove('warning');
    if(isPreview){
      status.textContent='OpenStreetMap + SLU:s verkliga rasterförhandsbild visas.';
      summary.textContent='Färgerna visar relativ variation i råvärden inom Luleå, inte ton kol. SOC och Stock_All har olika skalor.';
      units.textContent='Fysisk kolenhet ej verifierad. Inga ton C eller CO₂ beräknas ännu.';
      quality.textContent='SLU källraster: '+(record.source_crs||'ej känt')+' · fullt reprojicerad förhandsbild: EPSG:3857 · Luleås arbetsgräns.';
      return;
    }
    status.textContent='OpenStreetMap + bearbetat kolraster visas.';
    const coverage=record.coverage_pct_of_municipality;
    summary.textContent=record.total_tonnes_C==null
      ?'Raster tillgängligt. Ingen verifierad kolsumma.'
      :'Kolförråd för datatäckta rasterceller inom Luleå: '+Number(record.total_tonnes_C).toLocaleString('sv-SE',{maximumFractionDigits:0})+' ton C.';
    if(coverage!=null)summary.textContent+=' Datalagrets täckning av kommunytan: '+Number(coverage).toLocaleString('sv-SE',{maximumFractionDigits:1})+' %.';
    units.textContent='Kartans enhet: '+(record.units||'ej angiven');
    quality.textContent='Källa: '+(record.source||'okänd')+' · Käll-CRS: '+(record.source_crs||'ej känt');
  }
  select.addEventListener('change',render);
  async function init(){
    fitMunicipality();
    try{
      const b=await getJson('data/lulea_boundary.geojson');
      municipality=L.geoJSON(b,{
        style:{color:'#0b6346',weight:2.5,fill:false,opacity:1}
      }).addTo(map);
      layersControl.addOverlay(municipality,'Luleå kommungräns');
      fitMunicipality();
    }catch(e){error('Kommungränsen kunde inte läsas: '+e.message);}
    try{manifest=await getJson('data/layers.json');}
    catch(e){console.warn('Vanliga kolraster är ännu inte tillgängliga:',e);}
    try{previews=await getJson('data/preview/preview_layers.json');}
    catch(e){console.warn('SLU:s förhandskartor kan inte läsas:',e);error('Rastermetadata kunde inte laddas. OpenStreetMap ska ändå synas.');}
    render();
    requestAnimationFrame(()=>map.invalidateSize());
  }
  init();
})();
