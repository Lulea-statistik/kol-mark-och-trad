/* NMD2018 biomass footprint coverage: independent source-gated cohorts. */
(()=>{
"use strict";
const YEARS=["2010","2015","2018"],CELL_HA=.0625;
const sv=(value,d=0)=>value.toLocaleString("sv-SE",{minimumFractionDigits:d,maximumFractionDigits:d});
const COLOR={"Skog utanför våtmark":"#277456","Temporärt ej skog":"#c88c5d",
 "Skog på våtmark":"#718f31","Öppen våtmark":"#8cbf7c","Åkermark":"#dfbb53",
 "Övrig öppen mark":"#c8ac60","Exploaterad mark":"#7e858c","Vatten":"#438cbe"};
const order=Object.keys(COLOR);
function addTable(rows){
 const body=document.getElementById("biomassCoverageRows");body.replaceChildren();
 rows.forEach(r=>{
  const cells=[r.group,r.common_cells*CELL_HA,r.missing_2015_cells*CELL_HA,
    r.positive_biomass_2010_missing_2015_cells*CELL_HA,
    r.missing_2015_tonnes_TS["2010"],null,r.missing_2015_tonnes_TS["2018"]];
  const tr=document.createElement("tr");
  cells.forEach((value,i)=>{
    const td=document.createElement(i===0?"th":"td");
    if(i===0)td.scope="row";
    td.textContent=i===0?value:i===5?"NoData":sv(value, i<=3?2:0);
    tr.appendChild(td);
  });body.appendChild(tr);
 });
}
function createChart(id,config){
 const canvas=document.getElementById(id);
 if(!canvas)throw Error("Saknar diagram "+id);
 new Chart(canvas,config);
}
function options(yTitle,stacked=false){
 return {responsive:true,maintainAspectRatio:false,
  interaction:{mode:"index",intersect:false},plugins:{
   legend:{position:"bottom",labels:{boxWidth:13,padding:12}},
   tooltip:{callbacks:{label:c=>c.dataset.label+": "+sv(c.parsed.y,2)+(yTitle.includes("ton")?" ton TS":" ha")}}
  },scales:{x:{stacked},y:{stacked,beginAtZero:true,title:{display:true,text:yTitle}}}};
}
async function init(){
 const status=document.getElementById("biomassCoverageStatus");
 try{
  const request=await fetch("data/biomass_coverage_nmd2018_2010_2018.json",{cache:"no-store"});
  if(!request.ok)throw Error("Publicerad resultatfil saknas ("+request.status+")");
  const d=await request.json();
  if(d.status!=="VERIFIED_COVERAGE_2015_NODATA_AND_POSITIVE_2010_MASS"||d.analysis_crs!=="EPSG:3006"||d.cell_m!==25||d.common_cells!==2456410||d.missing_2015_valid_2010_2018_cells!==264484)throw Error("Fel verifieringsstatus, CRS eller referenspopulation");
  if(typeof Chart==="undefined")throw Error("Diagrammotorn saknas");
  const rows=order.map(label=>d.groups.find(r=>r.group===label));
  if(rows.some(x=>!x))throw Error("En eller flera NMD2018-klasser saknas");
  if(rows.reduce((s,r)=>s+r.missing_2015_cells,0)!==264484)throw Error("NoData cellantal summerar inte");
  if(rows.reduce((s,r)=>s+r.positive_biomass_2010_missing_2015_cells,0)!==d.positive_2010_missing_2015_valid_2018_cells)throw Error("Positiva 2010-celler summerar inte");
  const nmdCells=7925547;
  YEARS.forEach(y=>{if(!Number.isInteger(d.year_valid_cells[y])||d.year_valid_cells[y]>nmdCells)throw Error("Fel källrastertäckning "+y);});
  createChart("biomassCoverageYearChart",{
    type:"bar",data:{labels:YEARS,datasets:[
      {label:"Giltiga rastervärden",data:YEARS.map(y=>d.year_valid_cells[y]*CELL_HA),backgroundColor:"#277456"},
      {label:"Ingen giltig täckning",data:YEARS.map(y=>(nmdCells-d.year_valid_cells[y])*CELL_HA),backgroundColor:"#c1c8c4"}
    ]},options:options("Hektar inom NMD-giltigt undersökningsområde",true)
  });
  createChart("biomassCoverageCohortChart",{
   type:"bar",data:{labels:order,datasets:[
    {label:"Gemensamt giltig alla tre år",data:rows.map(r=>r.common_cells*CELL_HA),backgroundColor:"#277456"},
    {label:"Giltig 2010 + 2018, NoData 2015",data:rows.map(r=>r.missing_2015_cells*CELL_HA),backgroundColor:"#c88c5d"}
   ]},options:{...options("Hektar i två disjunkta urval"),indexAxis:"y",
    plugins:{legend:{position:"bottom"},tooltip:{callbacks:{label:c=>c.dataset.label+": "+sv(c.parsed.x,2)+" ha"}}},
    scales:{x:{beginAtZero:true,title:{display:true,text:"Hektar"}},y:{stacked:false}}}
  });
  createChart("biomassCoverageMissingMassChart",{
   type:"bar",data:{labels:order,datasets:[
    {label:"2010 – skattad massa",data:rows.map(r=>r.missing_2015_tonnes_TS["2010"]),backgroundColor:"#296c51"},
    {label:"2018 – skattad massa",data:rows.map(r=>r.missing_2015_tonnes_TS["2018"]),backgroundColor:"#c88c5d"}
   ]},options:{...options("Modellerade ton torrsubstans"),indexAxis:"y",
    plugins:{legend:{position:"bottom"},tooltip:{callbacks:{label:c=>c.dataset.label+": "+sv(c.parsed.x,0)+" ton TS"}}},
    scales:{x:{beginAtZero:true,title:{display:true,text:"Ton TS"}},y:{stacked:false}}}
  });
  addTable(rows);
  const count=d.positive_2010_missing_2015_valid_2018_cells,
    missing=d.missing_2015_valid_2010_2018_cells;
  const total2010=rows.reduce((s,r)=>s+r.missing_2015_tonnes_TS["2010"],0);
  const total2018=rows.reduce((s,r)=>s+r.missing_2015_tonnes_TS["2018"],0);
  document.getElementById("biomassCoverageHighlights").textContent=
    "2015 saknar data på "+sv(missing*CELL_HA,2)+" ha med giltiga värden 2010 och 2018. Av dessa har "+sv(count)+" celler ("+sv(count*CELL_HA,2)+" ha) positiv skattad biomassa 2010. På de "+sv(missing*CELL_HA,2)+" hektaren skattas "+sv(total2010,0)+" ton TS 2010 och "+sv(total2018,0)+" ton TS 2018; 2015 är NoData, inte noll.";
  status.textContent="Källkontrollerad rasterstatistik: "+sv(nmdCells)+" NMD-giltiga 25m-celler, full 25m EPSG:3006-reprojicering, inga skattade 2015-värden.";
 }catch(err){status.textContent="Täckningsdiagrammen kunde inte visas: "+err.message;status.style.color="#a43b25";console.error(err);}
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();