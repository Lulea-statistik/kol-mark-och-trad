'use strict';
(() => {
  const status=document.getElementById('trendStatus');
  const tbody=document.getElementById('trendTable');
  const note=document.getElementById('trendNote');
  const consistency=document.getElementById('consistencyCheck');
  const years=[2000,2005,2010,2015,2020,2025,2030,2035,2040,2045];
  const series=[
    {stock:'soil',change:'change_soc',name:'Markkol (Stock_SOC)',color:'#2676a5'},
    {stock:'stock_dom',change:'change_dom',name:'Dött organiskt material (Stock_DOM)',color:'#bd752e'},
    {stock:'soil_all',change:'change_all',name:'Totalt markförråd (Stock_All)',color:'#27764d'}
  ];
  const format=n=>Number(n).toLocaleString('sv-SE',{maximumFractionDigits:0});
  const closeEnough=(a,b)=>Math.abs(a-b)<=Math.max(1,Math.abs(a)*0.0001);
  const error=msg=>{status.textContent='Trend kan inte beräknas: '+msg;status.classList.add('warning');};
  const cell=(tr,value)=>{const td=document.createElement('td');td.textContent=value;tr.appendChild(td);};
  fetch('data/preview/preview_statistics.json',{cache:'no-store'})
    .then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json();})
    .then(doc=>{
      if(doc.physical_units_verified!==false || doc.data_type!=='raw_source_samples_in_reprojected_preview_grid'){
        throw Error('Oväntad datatyp: avbryter hellre än att ange felaktiga ton C.');
      }
      const values=series.map(s=>{
        const stock=doc.layers?.[s.stock],change=doc.layers?.[s.change];
        if(!stock||!change)throw Error('Lager saknas: '+s.stock+' / '+s.change);
        if(stock.raster_grid_width!==change.raster_grid_width ||
           stock.raster_grid_height!==change.raster_grid_height ||
           stock.valid_preview_pixels!==change.valid_preview_pixels ||
           stock.municipal_preview_pixels!==change.municipal_preview_pixels ||
           stock.null_inside_pixels!==change.null_inside_pixels){
          throw Error('Rastermask eller förhandsgrid skiljer mellan '+s.stock+' och '+s.change);
        }
        if(!Number.isFinite(stock.sum_raw)||!Number.isFinite(change.sum_raw))
          throw Error('Ogiltigt summafält: '+s.stock);
        return {...s,base:stock.sum_raw,delta:change.sum_raw,
          data:years.map(y=>stock.sum_raw+(y-2020)*change.sum_raw)};
      });
      // Stock_All and Change_All should consist of SOC + DOM, not a fourth pool.
      const b=values[0].base+values[1].base;
      const d=values[0].delta+values[1].delta;
      const stockMatches=closeEnough(b,values[2].base);
      const changeMatches=closeEnough(d,values[2].delta);
      const all=values[2];
      consistency.textContent='Kontroll av ingående komponenter: Stock_SOC + Stock_DOM '+(stockMatches?'motsvarar':'avviker från')+' Stock_All; Change_SOC + Change_DOM '+(changeMatches?'motsvarar':'avviker från')+' Change_All i förhandsgridet. Stock_All används som separat total och adderas inte igen.';
      if(!stockMatches||!changeMatches)consistency.classList.add('warning');
      for(let i=0;i<years.length;i++){
        const tr=document.createElement('tr');
        const year=years[i];
        cell(tr,year);
        for(const s of values)cell(tr,format(s.data[i]));
        cell(tr,year===2020?'Beräkningsankare (ej uppmätt 2020)':year<2020?'Tillbakaskrivet scenario':'Framskrivet scenario');
        tbody.appendChild(tr);
      }
      status.textContent='Beräknad illustrativ trend för samplade råvärden inom Luleås arbetsgräns. Stock_All är enda totallinjen; de två övriga linjerna är dess komponenter.';
      note.textContent='2020 är endast ett beräkningsankare. Streckade linjedelar bakåt är tillbakaskrivna scenarier; heldragna framåt är framskrivningar med oförändrad antagen årlig råvärdesförändring. Totalen är Stock_All, inte summan av samtliga tre kurvor. Enhet: summa rasterråvärden i nedskalat förhandsgrid, ej ton C.';
      if(!window.Chart){throw Error('Diagrammodulen kunde inte laddas. Tabellvärden finns ovan.');}
      const chart=new Chart(document.getElementById('trendChart'),{
        type:'line',
        data:{
          labels:years.map(String),
          datasets:values.map(s=>({
            label:s.name,
            data:s.data,
            borderColor:s.color,
            backgroundColor:s.color,
            borderWidth:s.stock==='soil_all'?3:2,
            tension:0,
            pointRadius:years.map(y=>y===2020?5:3),
            pointHoverRadius:6,
            fill:false,
            segment:{borderDash:ctx=>ctx.p1DataIndex<=4?[6,4]:[]}
          }))
        },
        options:{
          responsive:true,maintainAspectRatio:false,
          interaction:{mode:'index',intersect:false},
          plugins:{legend:{position:'bottom'},
            tooltip:{callbacks:{label:ctx=>ctx.dataset.label+': '+format(ctx.parsed.y)+' (summa råvärden, ej ton)'}}},
          scales:{
            x:{title:{display:true,text:'År (scenario; 2020 är beräkningsankare)'}},
            y:{title:{display:true,text:'Summa samplade rasterråvärden (ej ton C)'},ticks:{callback:value=>Number(value).toLocaleString('sv-SE',{notation:'compact',maximumFractionDigits:1})}}
          }
        }
      });
    })
    .catch(e=>error(e.message));
})();