'use strict';
(() => {
 const table=document.getElementById('previewStatisticsTable');
 const status=document.getElementById('previewStatisticsStatus');
 const selector=document.getElementById('rawHistogramLayer');
 let stats=null, chart=null;
 const names={biomass:'Trädbiomassa ovan mark (SGD2)',soil:'Kolförråd – markkol (Stock_SOC)',soil_all:'Kolförråd (totalt, inkl. dött material) – Stock_All'};
 const num=x=>x==null?'—':Number(x).toLocaleString('sv-SE',{maximumFractionDigits:4});
 function draw(){
   const key=selector.value,r=stats?.layers?.[key],canvas=document.getElementById('rawHistogram');
   if(chart){chart.destroy();chart=null;}
   if(!r?.histogram||!window.Chart){canvas.hidden=true;return;}
   canvas.hidden=false;
   const h=r.histogram;
   const labels=h.counts.map((_,i)=>num(h.edges[i])+'–'+num(h.edges[i+1]));
   chart=new Chart(canvas,{type:'bar',data:{labels,datasets:[{
     label:'Antal giltiga samplade gridpixlar',data:h.counts,
     backgroundColor:h.counts.map((_,i)=>'rgb('+Math.round(255*(1-i/Math.max(1,h.counts.length-1)))+',0,0)')
   }]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},
       tooltip:{callbacks:{title:items=>'Råvärdesintervall: '+items[0].label}}},
       scales:{y:{beginAtZero:true,title:{display:true,text:'Samplade gridpixlar'}},
               x:{title:{display:true,text:'Råvärde – okänd fysisk enhet'},ticks:{maxRotation:45,minRotation:45}}}}});
 }
 fetch('data/preview/preview_statistics.json',{cache:'no-store'})
 .then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json();})
 .then(data=>{
   if(data.physical_units_verified!==false)throw Error('Oväntad datastatus');
   stats=data;table.replaceChildren();
   for(const key of ['biomass','soil','soil_all']){
     const r=stats.layers?.[key];if(!r)continue;
     const tr=document.createElement('tr');
     for(const value of [names[key],num(r.valid_preview_pixels),num(r.null_inside_pixels),
       num(r.min_raw),num(r.median_raw),num(r.mean_raw),num(r.sum_raw),num(r.max_raw)]){
       const td=document.createElement('td');td.textContent=value;tr.appendChild(td);
     }
     table.appendChild(tr);
   }
   status.textContent='Verifierad rasterbaserad förhandsstatistik laddad. Råvärdenas enhet är ännu okänd; inga ton C visas.';
   draw();
 }).catch(e=>{status.textContent='Förhandsstatistik är ännu inte publicerad: '+e.message;});
 selector.addEventListener('change',draw);
})();
