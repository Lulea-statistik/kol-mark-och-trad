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
let distributionChart=null,biomassChart=null,changeChart=null,directionChart=null,controlChart=null,source=null;
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
function paintControlled(){
  const el=document.getElementById('granTallControlledChart');
  const statusEl=document.getElementById('granTallControlledStatus');
  if(controlChart){controlChart.destroy();controlChart=null;}
  if(!source||!source.age_volume_control){
    if(statusEl)statusEl.textContent='Inväntar verifierade rasterresultat för ålder × volym från PR #127.';
    return;
  }
  const d=source.age_volume_control;
  const a=document.getElementById('granTallControlledAge').value;
  const v=document.getElementById('granTallControlledVolume').value;
  const selectedA=a==='all'?d.age_bins.map((_,i)=>i):[Number(a)];
  const selectedV=v==='all'?d.volume_2010_bins.map((_,i)=>i):[Number(v)];
  const counts=Array(9).fill(0),m10=Array(9).fill(0),m18=Array(9).fill(0);
  for(const ai of selectedA)for(const vi of selectedV)for(let j=0;j<9;j++){
    counts[j]+=d.cells_by_age_volume_balance[ai][vi][j];
    m10[j]+=d.mass_tTS_by_age_volume_balance['2010'][ai][vi][j];
    m18[j]+=d.mass_tTS_by_age_volume_balance['2018'][ai][vi][j];
  }
  const n=counts.reduce((p,q)=>p+q,0);
  if(statusEl)statusEl.textContent='Gemensamma giltiga celler: '+sv(n,0)+', '+sv(n*.0625,1)+' ha. Tomma klasser visas utan värde. Jämför endast celler inom valt ålders- och volymintervall.';
  if(!el||typeof Chart==='undefined')return;
  const values=counts.map((cnt,j)=>cnt>0&&m10[j]>0?100*(m18[j]/m10[j]-1):null);
  controlChart=new Chart(el,{type:'line',data:{labels,datasets:[{
    label:'Modellerad biomassaskillnad 2018/2010 (%)',
    data:values,borderColor:'#9a473d',backgroundColor:'#9a473d',pointRadius:5,borderWidth:3,spanGaps:false,tension:0}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{tooltip:{callbacks:{
      label:c=>c.parsed.y===null?'Inga jämförbara celler':sv(c.parsed.y,2)+' % ('+sv(counts[c.dataIndex],0)+' celler)'}}},
      scales:{x:{title:{display:true,text:'Gran/tall-balans 2010'}},
       y:{title:{display:true,text:'2018 relativt 2010 (%)'}}}}});
}
document.getElementById('granTallControlledAge')?.addEventListener('change',paintControlled);
document.getElementById('granTallControlledVolume')?.addEventListener('change',paintControlled);
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
  paintHeatmap(cohort);paintCharts(cohort);paintControlled();
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

/* Standardized result is published only after GitHub Actions verifies
 * consistency with the independently verified 2010–2018 raster summaries.
 * The chart never substitutes synthetic observations. */
(function(){
  'use strict';
  const status=document.getElementById('granTallStandardStatus');
  const table=document.getElementById('granTallStandardTable');
  const canvas=document.getElementById('granTallStandardChart');
  if(!status||!table||!canvas)return;
  const fmt=(x,n=1)=>Number(x).toLocaleString('sv-SE',{minimumFractionDigits:n,maximumFractionDigits:n});
  fetch('data/gran_tall_standardisering_2010_2018.json',{cache:'no-store'})
    .then(r=>{if(!r.ok)throw Error('den verifierade standardiseringen är ännu inte publicerad');return r.json()})
    .then(data=>{
      if(data.status!=='DERIVED_FROM_VERIFIED_AGGREGATED_RASTER'||data.analysis_crs!=='EPSG:3006'
         ||data.common_support_strata_count<1||data.axis_classes_gran_tall.length!==9)
        throw Error('ofullständig eller ogiltig standardiseringsfil');
      const labels=data.axis_classes_gran_tall;
      const vals=labels.map(label=>data.standardized_by_balance_class[label]);
      status.textContent='Gemensamt stöd: '+data.common_support_strata_count+' av '+data.total_possible_strata+
        ' ålders–volymgrupper; gemensam referensfördelning med '+fmt(data.standard_population_total_cells,0)+
        ' celler. Lägsta klassvisa täckningsgrad: '+fmt(data.minimum_coverage_percent)+' %. Minst 30 celler i var och en av nio klasser per stratum.';
      table.innerHTML='<table><caption>Observerad modellkvot och direkt standardiserad modellkvot, samma celler 2010 och 2018</caption>'+
      '<thead><tr><th>Gran/tall</th><th>Alla celler (%)</th><th>Gemensamt stöd, oviktad (%)</th><th>Standardiserad (%)</th><th>Täckning (%)</th></tr></thead><tbody>'+
      labels.map((label,i)=>'<tr><th>'+label+'</th><td>'+fmt(vals[i].raw_2018_vs_2010_percent,2)+'</td>'+
      '<td>'+fmt(vals[i].shared_unstandardized_percent,2)+'</td>'+
      '<td><strong>'+fmt(vals[i].standardized_2018_vs_2010_percent,2)+'</strong></td>'+
      '<td>'+fmt(vals[i].coverage_percent,1)+'</td></tr>').join('')+'</tbody></table>';
      if(typeof Chart==='undefined')return;
      new Chart(canvas,{type:'line',data:{labels,datasets:[
        {label:'Utan standardisering',data:vals.map(v=>v.raw_2018_vs_2010_percent),borderColor:'#a95b39',backgroundColor:'#a95b39',borderWidth:2,pointRadius:4,tension:0},
        {label:'Standardiserad ålder och volym',data:vals.map(v=>v.standardized_2018_vs_2010_percent),borderColor:'#216c66',backgroundColor:'#216c66',borderWidth:3,pointRadius:5,tension:0}
      ]},options:{responsive:true,maintainAspectRatio:false,plugins:{tooltip:{callbacks:{
        label:c=>c.dataset.label+': '+fmt(c.parsed.y,2)+' %; täckning '+fmt(vals[c.dataIndex].coverage_percent,1)+' %'}}},
        scales:{x:{title:{display:true,text:'Modellerad gran/tall-balans 2010'}},
        y:{title:{display:true,text:'Skillnad modellerad biomassa 2018/2010 (%)'}}}}});
    }).catch(err=>{status.textContent='Standardiseringen visas när resultatfilen godkänts och publicerats: '+err.message;});
})();
