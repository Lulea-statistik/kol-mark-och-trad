'use strict';
(async()=>{
 const status=document.getElementById('biomassTrendStatus');
 const commonNote=document.getElementById('commonAreaNote');
 const extendedNote=document.getElementById('extendedAreaNote');
 const coverageNote=document.getElementById('biomassCoverageNote');
 const body=document.getElementById('biomassTrendTable');
 const keys=['biomass_2010','biomass_2015_leaf','biomass'];
 const labels=['2010 – Skogskarta biomassa','2015 – SLU total biomassa ovan jord','2018 – SGD2 Biomassa (omdrev 2)'];
 const xLabels=['2010','2015','2018'];
 const colors=['#2d729e','#bc742f','#226f50'];
 const num=x=>Number(x).toLocaleString('sv-SE',{maximumFractionDigits:0});
 const pct=x=>Number(x*100).toLocaleString('sv-SE',{maximumFractionDigits:1})+' %';
 const addCell=(tr,value)=>{const td=document.createElement('td');td.textContent=value;tr.appendChild(td);};
 const invalid=v=>v===-9999||!Number.isFinite(v)||v<0;
 function draw(id,values,yLabel){
   if(!window.Chart)throw Error('Chart.js kunde inte laddas.');
   new Chart(document.getElementById(id),{
     type:'line',
     data:{labels:xLabels,datasets:[{
       label:'Medelvärde samplade rasterråvärden – inte ton',
       data:values,
       borderColor:'#165c72',
       backgroundColor:'#165c72',
       borderWidth:3,pointRadius:6,pointHoverRadius:8,tension:0,fill:false,
       segment:{borderDash:ctx=>ctx.p1DataIndex===1?[7,4]:[]}
     }]},
     options:{responsive:true,maintainAspectRatio:false,interaction:{intersect:false,mode:'nearest'},
       plugins:{legend:{display:false},
         tooltip:{callbacks:{title:items=>labels[items[0].dataIndex],label:item=>Number(item.parsed.y).toLocaleString('sv-SE',{maximumFractionDigits:2})+' råvärde i medeltal (ej ton)'}}},
       scales:{y:{title:{display:true,text:yLabel},ticks:{callback:v=>Number(v).toLocaleString('sv-SE',{notation:'compact',maximumFractionDigits:2})}},
               x:{title:{display:true,text:'Källår / omdrev (SGD2-skanning 2018)'}}}
     }
   });
 }
 try{
   const response=await fetch('data/preview/preview_layers.json',{cache:'no-store'});
   if(!response.ok)throw Error('Rastermetadata kan inte hämtas (HTTP '+response.status+').');
   const manifest=await response.json();
   const recs=keys.map(k=>{
     const r=manifest.layers?.[k];
     if(!r?.numeric_file)throw Error('Rasterdata saknas: '+k);
     if(r.raster_grid_crs!=='EPSG:3857')throw Error('Kartgrid har fel CRS: '+k);
     return r;
   });
   const n=recs[0].raster_grid_width*recs[0].raster_grid_height;
   const bounds=JSON.stringify(recs[0].raster_grid_bounds_m);
   for(const r of recs){
     if(r.raster_grid_width*r.raster_grid_height!==n ||
        r.raster_grid_width!==recs[0].raster_grid_width ||
        r.raster_grid_height!==recs[0].raster_grid_height ||
        JSON.stringify(r.raster_grid_bounds_m)!==bounds){
       throw Error('Rastergridens dimensioner eller koordinater överensstämmer inte. Inga summor görs.');
     }
   }
   if(typeof DecompressionStream==='undefined')throw Error('Webbläsaren saknar stöd för gzip.');
   async function readGrid(rec){
     const resp=await fetch(rec.numeric_file);
     if(!resp.ok)throw Error('Numeriskt raster saknas: '+rec.numeric_file);
     const b=await new Response(resp.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
     if(b.byteLength!==n*4)throw Error('Oväntad datastorlek för '+rec.numeric_file);
     return new Float32Array(b);
   }
   const [old,leaf,latest]=await Promise.all(recs.map(readGrid));
   // Two explicit geographic populations:
   // 1. Cells where all three datasets are valid (common footprint).
   // 2. Every cell valid in SGD2 (larger footprint, NO claim of full municipality).
   // Summing comparable grid samples is only an exploratory proxy. No area integrals.
   const common=[0,0,0],observed=[0,0,0],missingCount=[0,0,0],missingSum=[0,0,0],observedCount=[0,0,0];
   let commonCount=0,referenceCount=0;
   const rasters=[old,leaf,latest];
   for(let i=0;i<n;i++){
     const v0=old[i],v1=leaf[i],v2=latest[i];
     const ok0=!invalid(v0),ok1=!invalid(v1),ok2=!invalid(v2);
     if(ok0&&ok1&&ok2){
       common[0]+=v0;common[1]+=v1;common[2]+=v2;commonCount++;
     }
     if(ok2){
       referenceCount++;
       for(let k=0;k<3;k++){
         if(!invalid(rasters[k][i])){observed[k]+=rasters[k][i];observedCount[k]++;}
         else{missingCount[k]++;missingSum[k]+=v2;}
       }
     }
   }
   if(commonCount===0||referenceCount===0||common[2]<=0)
     throw Error('Inga jämförbara rasterpixlar eller nollsumma i SGD2:s gemensamma yta.');
   const ratios=[common[0]/common[2],common[1]/common[2],1];
   if(ratios.some(v=>!Number.isFinite(v)||v<0))
     throw Error('Kunde inte beräkna rimliga kvoter för täckningsskattning.');
   const estimated=ratios.map((r,k)=>r*missingSum[k]);
   const expanded=observed.map((sum,k)=>sum+estimated[k]);
   // Divide each sum by the identical geographic cell count. This explicitly
   // compares mean sampled density rather than mislabelling raw sums as biomass.
   // This is NOT a physical area integral; native rasters remain unharmonised.
   const commonMean=common.map(sum=>sum/commonCount);
   const expandedMean=expanded.map(sum=>sum/referenceCount);
   draw('biomassCommonChart',commonMean,'Medelvärde råvärden, gemensam yta');
   draw('biomassExtendedChart',expandedMean,'Medelvärde råvärden, SGD2-yta');
   status.textContent='Tre publicerade rastergrid jämförda som medelvärden på ett gemensamt EPSG:3857-förhandsgrid. En fysisk arealviktad totalsumma i ton torr biomassa eller kol kan ännu inte beräknas jämförbart.';
   commonNote.textContent='Gemensamma giltiga pixlar: '+num(commonCount)+
      ' (av '+num(referenceCount)+' giltiga SGD2-pixlar, '+pct(commonCount/referenceCount)+
      '). Identisk geografisk avgränsning används för alla tre datapunkterna.';
   extendedNote.textContent='Referensyta: '+num(referenceCount)+' giltiga SGD2-pixlar. Kvot 2010/SGD2 på gemensam yta: '+
      ratios[0].toLocaleString('sv-SE',{maximumFractionDigits:4})+
      '; kvot 2015/SGD2: '+ratios[1].toLocaleString('sv-SE',{maximumFractionDigits:4})+
      '. Saknade äldre värden skattas pixelvis som SGD2 × respektive kvot. Detta är en grov modell och modeller, enheter och rumslig täckning är ännu inte fullt harmoniserade.';
   for(let k=0;k<3;k++){
     const tr=document.createElement('tr');
     addCell(tr,labels[k]);addCell(tr,commonMean[k].toLocaleString('sv-SE',{maximumFractionDigits:2}));addCell(tr,expandedMean[k].toLocaleString('sv-SE',{maximumFractionDigits:2}));
     addCell(tr,num(missingCount[k])+' ('+pct(missingCount[k]/referenceCount)+')');
     addCell(tr,pct(expanded[k]===0?0:estimated[k]/expanded[k]));
     body.appendChild(tr);
   }
   coverageNote.textContent='Källa: publicerade EPSG:3857-förhandsgrid med '+num(n)+
      ' cellpositioner. Referensytan är där SGD2 har giltiga rastervärden, inte exakt hela Luleå kommuns markyta. Rasterupplösning i källorna är 25 m (2010), 12,5 m (2015) och 10 m (2018). Alla tre har samplats med närmaste granne till samma nedskalade 3857-grid. Det gör antalet kartpixlar jämförbart men inte värdenas definition, enhet eller geometriska arealintegral. Saknade värden där inte ens SGD2 har data ingår inte. För 2015 skattas '+num(missingCount[1])+
      ' celler, däribland den nordliga utbredning som saknas i 2015-lagret. Skattning är inte observation; 2015 Biomass_leaf avser total biomassa ovan jord enligt SLU, men är ännu inte metodharmoniserad med SGD2.';
 }catch(e){status.textContent='Biomassatrenden kunde inte beräknas: '+e.message;status.classList.add('warning');}
})();