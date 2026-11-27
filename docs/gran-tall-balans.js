/* Gran/tall balance 2005 -> 2010; verified raster JSON only.
 * Nothing in this module infers true historical species transitions.
 */
(function(){
'use strict';
const root=document.getElementById('granTallBalans');
if(!root)return;
const status=document.getElementById('granTallBalansStatus');
const ageSelect=document.getElementById('granTallBalansAge');
const matrix=document.getElementById('granTallBalansMatrix');
const summary=document.getElementById('granTallBalansSummary');
const labels=['10/90','20/80','30/70','40/60','50/50','60/40','70/30','80/20','90/10'];
const sv=(x,dec=1)=>Number(x).toLocaleString('sv-SE',{maximumFractionDigits:dec,minimumFractionDigits:dec});
let distributionChart=null,biomassChart=null,changeChart=null,directionChart=null,source=null;
const sourceURL='data/gran_tall_balans_2005_2010.json';
function paintHeatmap(cohort){
  const counts=cohort.matrix_cells;
  const max=Math.max(...counts.flat(),1);
  let html='<table class="gran-tall-heatmap"><caption>Hektar – rader: gran/tall 2005, kolumner: gran/tall 2010</caption><thead><tr><th scope="col">2005 ↓ / 2010 →</th>'+
    labels.map(x=>'<th scope="col">'+x+'</th>').join('')+'<th scope="col">Summa 2005 (ha)</th></tr></thead><tbody>';
  for(let i=0;i<9;i++){
    html+='<tr><th scope="row">'+labels[i]+'</th>';
    for(let j=0;j<9;j++){
      const ha=counts[i][j]*.0625;
      const intensity=Math.sqrt(counts[i][j]/max);
      const alpha=(0.06+.80*intensity).toFixed(3);
      const diagonal=i===j;
      html+='<td title="2005: '+labels[i]+', 2010: '+labels[j]+', '+sv(ha,2)+' ha ('+sv(counts[i][j],0)+' celler)" style="background:rgba(39,114,84,'+alpha+');'+(diagonal?'outline:2px solid #1b654f;outline-offset:-2px;':'')+'">'+(counts[i][j]>0?sv(ha,1):'–')+'</td>';
    }
    html+='<td><strong>'+sv(cohort.row_2005_cells[i]*.0625,1)+'</strong></td></tr>';
  }
  html+='</tbody><tfoot><tr><th scope="row">Summa 2010 (ha)</th>'+
    cohort.col_2010_cells.map(n=>'<th>'+sv(n*.0625,1)+'</th>').join('')+
    '<th>'+sv(cohort.area_ha,1)+'</th></tr></tfoot></table>';
  matrix.innerHTML=html;
}
function paintCharts(cohort){
  if(typeof Chart==='undefined')return;
  if(distributionChart){distributionChart.destroy();distributionChart=null;}
  if(biomassChart){biomassChart.destroy();biomassChart=null;}
  if(changeChart){changeChart.destroy();changeChart=null;}
  if(directionChart){directionChart.destroy();directionChart=null;}
  const bars=document.getElementById('granTallBalansDistribution');
  const bio=document.getElementById('granTallBalansBiomassa');
  if(bars){
    distributionChart=new Chart(bars,{type:'bar',data:{labels,
      datasets:[
        {label:'2005 – hektar',data:cohort.row_2005_cells.map(n=>n*.0625),backgroundColor:'#7c9cb6'},
        {label:'2010 – hektar',data:cohort.col_2010_cells.map(n=>n*.0625),backgroundColor:'#bc6c4b'}]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{tooltip:{callbacks:{label:c=>c.dataset.label+': '+sv(c.parsed.y,2)+' ha'}}},
       scales:{x:{title:{display:true,text:'Balans gran/tall'}},y:{beginAtZero:true,title:{display:true,text:'Hektar'}}}}});
  }
  if(bio){
    const means=cohort['2010_balance_class_density_tTS_ha'];
    biomassChart=new Chart(bio,{type:'bar',data:{labels,
      datasets:[
        {label:'2010 – ton TS/ha',data:means['2010'],backgroundColor:'#7c9cb6'},
        {label:'2018 – ton TS/ha',data:means['2018'],backgroundColor:'#bc6c4b'}]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{tooltip:{callbacks:{label:c=>c.parsed.y===null?'Saknar celler':c.dataset.label+': '+sv(c.parsed.y,2)}}},
       scales:{x:{title:{display:true,text:'Balans gran/tall enligt 2010'}},y:{beginAtZero:true,title:{display:true,text:'Ton TS/ha'}}}}});
  }

  const changeEl=document.getElementById('granTallBalansDifference');
  if(changeEl){
    changeChart=new Chart(changeEl,{type:'line',data:{labels,datasets:[{
      label:'Biomassaskillnad 2018/2010, %',
      data:cohort.density_change_2018_vs_2010_pct,
      borderColor:'#9a473d',backgroundColor:'#9a473d',borderWidth:3,pointRadius:4,tension:0}]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{tooltip:{callbacks:{label:c=>c.parsed.y===null?'Inga celler':sv(c.parsed.y,2)+' %'}}},
      scales:{x:{title:{display:true,text:'Gran/tall-balans enligt 2010'}},
      y:{title:{display:true,text:'Skillnad i modellerad torrmassa (%)'}}}}});
  }
  const directionEl=document.getElementById('granTallBalansDirection');
  const transition=cohort.matrix_biomass_tTS;
  const transitionStatus=document.getElementById('granTallBalansDirectionStatus');
  if(directionEl&&transition){
    const groups=[{name:'Mot mer tall',check:(i,j)=>j<i,color:'#6e92b6'},
      {name:'Samma balansklass',check:(i,j)=>j===i,color:'#888b8b'},
      {name:'Mot mer gran',check:(i,j)=>j>i,color:'#af654f'}];
    const data=groups.map(g=>({
      label:g.name,backgroundColor:g.color,
      data:labels.map((_,j)=>{
        let mass10=0,mass18=0,cells=0;
        for(let i=0;i<9;i++)if(g.check(i,j)){
          cells+=cohort.matrix_cells[i][j];
          mass10+=transition['2010'][i][j];mass18+=transition['2018'][i][j];
        }
        return cells>0&&mass10>0?100*(mass18/mass10-1):null;
      })}));
    directionChart=new Chart(directionEl,{type:'bar',data:{labels,datasets:data},
      options:{responsive:true,maintainAspectRatio:false,plugins:{tooltip:{callbacks:{
        label:c=>c.parsed.y===null?'Inga celler':c.dataset.label+': '+sv(c.parsed.y,2)+' %'}}},
        scales:{x:{title:{display:true,text:'Gran/tall-balans enligt 2010'}},
        y:{title:{display:true,text:'Skillnad 2018/2010 (%)'}}}}});
    if(transitionStatus)transitionStatus.textContent='Verifierad jämförelse inom respektive 2010-klass. Grupperna utgår från hur cellens modellerade balansklass förändrades 2005–2010. Saknas en grupp visas inget värde.';
  }else if(transitionStatus){
    transitionStatus.textContent='Detaljerad jämförelse av balansförskjutningar kräver den nya verifierade rasterfilen från PR #125.';
  }

}
function render(){
  if(!source)return;
  const cohort=source.cohorts[ageSelect.value];
  if(!cohort){status.textContent='Saknar resultat för valt åldersurval';return;}
  const included=cohort.cells,excluded=cohort.excluded_zero_pine_plus_spruce;
  const diagonal=cohort.matrix_cells.reduce((acc,row,i)=>acc+row[i],0);
  status.textContent='Verifierade rasterdata – '+sv(included,0)+' celler ('+sv(cohort.area_ha,2)+' ha), '+
    sv(excluded,0)+' celler exkluderade eftersom gran + tall var 0 i minst ett av åren. '+
    sv(diagonal/included*100||0,1)+' % ligger på balansmatrisens diagonal.';
  summary.textContent='Diagonalens andel visar oförändrad modellerad balansklass, inte bekräftat oförändrad skog. '+
    'Fördelningsdiagrammet har identisk area 2005/2010. Biomassadiagrammet grupperar samma celler efter balansklass 2010.';
  paintHeatmap(cohort);paintCharts(cohort);
}
ageSelect.addEventListener('change',render);
fetch(sourceURL,{cache:'no-store'}).then(r=>{
  if(!r.ok)throw Error('Resultatfilen är ännu inte publicerad (HTTP '+r.status+').');
  return r.json();
}).then(d=>{
  if(!d.cohorts||d.analysis_crs!=='EPSG:3006'||d.cell_m!==25||
     JSON.stringify(d.axis_classes_gran_tall)!==JSON.stringify(labels))
    throw Error('Resultatfilens format eller käll-CRS-avstämning är fel.');
  source=d;
  render();
}).catch(err=>{
  status.textContent='Balansdiagrammen kan inte laddas: '+err.message+
    ' Diagrammen visas först när originalrasteranalysen har körts och publicerat verifierad JSON.';
});
})();
