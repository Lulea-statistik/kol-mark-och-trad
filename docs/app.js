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
  const imagery=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{
    attribution:'Imagery © Esri, Maxar, Earthstar Geographics, GIS User Community',
    maxZoom:19,maxNativeZoom:19
  });
  const layersControl=L.control.layers(
    {'Standard – OpenStreetMap':osm,'Flyg-/satellitbild – Esri World Imagery':imagery},
    {},
    {collapsed:false,position:'topright'}
  ).addTo(map);
  const baseSelector=document.getElementById('baseMap');
  baseSelector?.addEventListener('change',()=>{
    if(baseSelector.value==='imagery'){map.removeLayer(osm);imagery.addTo(map);}
    else{map.removeLayer(imagery);osm.addTo(map);}
  });
  map.on('baselayerchange',event=>{
    if(baseSelector)baseSelector.value=event.layer===imagery?'imagery':'osm';
  });
  osm.on('tileerror',()=>{error('OpenStreetMap kunde inte ladda alla kartplattor. Kontrollera uppkopplingen.')});
  let municipality=null, overlay=null, overlayName=null, manifest={layers:{}}, previews={layers:{}};
  const sampledGrids=new Map();
  const cellStatus=document.getElementById('cellStatus');
  const clickPopup=L.popup({maxWidth:330});
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
      status.textContent=record.color_scale_type==='signed_blue_white_red'?'Förändringsraster: blått = negativt, vitt = noll, rött = positivt, grått = NoData.':record.color_scale_type==='biomass_log_three_color'?'Biomassa: beige = 0, gul → orange/röd → mörkbrun = ökande positiva värden (log-skala), grått = NoData.':'Källbaserat förhandsraster: rött = lägre, svart = högre, grått = NoData.';
      summary.textContent=record.color_scale_type==='signed_blue_white_red'?'Förändringslager från SLU: negativt och positivt råvärde hålls isär med noll i mitten. Tecken och fysisk enhet måste dokumenteras innan kolkälla/kolsänka eller ton C/år kan redovisas.':record.color_scale_type==='biomass_log_three_color'?'Biomassan visar 0 separat från NoData. Endast positiva värden log-skalas för bättre kontrast. Färgskalan är relativ och förändrar inte klickvärden eller rådatastatistik.':'Rött → svart visar ökande råvärden och grått visar NoData. Färgskalan är relativ per lager, inte ton kol.';
      units.textContent=key==='preview_biomass'?'Skogliga grunddata (SGD2): biomassa ovan mark. Nollvärden = beige och NoData = grått; positiva värden visas med logaritmisk färgskala. Fysisk enhet och kolomräkning ej verifierade.':key.startsWith('preview_change_')?'Råvärden för förändring; fysisk enhet, tidsskala och teckenkonvention är ännu inte verifierade.':'Fysisk kolenhet ej verifierad. Inga ton C eller CO₂ beräknas ännu.';
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
  async function loadSampledGrid(key,record){
    if(!record?.numeric_file)throw Error('Numeriska förhandsdata är ännu inte publicerade för lagret.');
    if(!sampledGrids.has(key)){
      const promise=(async()=>{
        const res=await fetch(record.numeric_file);
        if(!res.ok)throw Error('HTTP '+res.status+' för rastervärden');
        if(typeof DecompressionStream==='undefined')throw Error('Webbläsaren saknar stöd för gzip-avkodning.');
        const raw=await new Response(res.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
        const expected=record.raster_grid_width*record.raster_grid_height*4;
        if(raw.byteLength!==expected)throw Error('Rastervärdefilen har oväntad storlek.');
        return new DataView(raw);
      })();
      sampledGrids.set(key,promise);
      promise.catch(()=>sampledGrids.delete(key));
    }
    return sampledGrids.get(key);
  }
  map.on('click',async(event)=>{
    const key=select.value;
    const record=key.startsWith('preview_')?previews.layers?.[key.slice(8)]:null;
    if(!showRaster.checked||!record?.numeric_file){
      cellStatus.textContent='Välj ett tillgängligt förhandslager och aktivera rastervisning för att läsa ett pixelvärde.';
      return;
    }
    const token=key;
    cellStatus.textContent='Läser råvärde ur förhandsraster…';
    try{
      const grid=await loadSampledGrid(key,record);
      if(select.value!==token)return;
      const bb=record.raster_grid_bounds_m, pt=map.options.crs.project(event.latlng);
      const col=Math.floor((pt.x-bb[0])/(bb[2]-bb[0])*record.raster_grid_width);
      const row=Math.floor((bb[3]-pt.y)/(bb[3]-bb[1])*record.raster_grid_height);
      if(col<0||row<0||col>=record.raster_grid_width||row>=record.raster_grid_height){
        cellStatus.textContent='Punkten ligger utanför det publicerade förhandsrastret.';return;
      }
      const value=grid.getFloat32(4*(row*record.raster_grid_width+col),true);
      const valid=Number.isFinite(value)&&value!==record.raster_grid_nodata;
      const desc=valid
        ?'Samplat råvärde: '+value.toLocaleString('sv-SE',{maximumFractionDigits:4})+' (enhet inte verifierad)'
        :'NoData eller utanför kommunpolygonen: inget giltigt samplat rastervärde här.';
      const heading=select.selectedOptions[0]?.textContent||'SLU-raster';
      const coords='Lat '+event.latlng.lat.toFixed(5)+', lon '+event.latlng.lng.toFixed(5);
      cellStatus.textContent=heading+' · '+desc+' · '+coords;
      const popup=L.DomUtil.create('div');
      const title=document.createElement('strong');title.textContent=heading;popup.appendChild(title);
      for(const line of [desc,coords,'Gridposition: kolumn '+(col+1)+', rad '+(row+1),
        'Upplösning för klickvärdet: '+record.raster_grid_width+' × '+record.raster_grid_height+' pixlar över Luleås utbredning.',
        'Värdet är närmaste källrasterpixel samplad till EPSG:3857-förhandsgrid – inte ett originalvärde för en exakt 10 m-cell.']){
        const p=document.createElement('p');p.style.margin='6px 0';p.textContent=line;popup.appendChild(p);
      }
      clickPopup.setLatLng(event.latlng).setContent(popup).openOn(map);
    }catch(err){cellStatus.textContent='Kunde inte läsa klickvärde: '+err.message;}
  });
  select.addEventListener('change',()=>{cellStatus.textContent='Klicka i rasterlagret för samplat råvärde och koordinat.';render();});
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
    // Do not default to an unpublished biomass overlay while published
    // source-backed soil layers are available.
    if(select.value==='preview_biomass'&&!previews.layers?.biomass?.image&&previews.layers?.soil?.image){
      select.value='preview_soil';
      console.info('Biomassa är ännu inte publicerad; visar befintligt markkol tills vidare.');
    }
    render();
    requestAnimationFrame(()=>map.invalidateSize());
  }
  init();
})();
