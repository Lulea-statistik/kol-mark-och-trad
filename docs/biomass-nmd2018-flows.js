/* Source-verified NMD2018 fixed-mask flows; no raster reprojection in browser. */
(()=>{
"use strict";
const YEARS=["2010","2015","2018"], AREA_CELL_HA=0.0625;
const COLORS={"Skog utanför våtmark":"#277456","Temporärt ej skog":"#c88c5d","Skog på våtmark":"#718f31","Öppen våtmark":"#8cbf7c","Åkermark":"#dfbb53","Övrig öppen mark":"#c8ac60","Exploaterad mark":"#7e858c","Vatten":"#438cbe"};
const nf=(n,dec=0)=>n.toLocaleString("sv-SE",{minimumFractionDigits:dec,maximumFractionDigits:dec});
function el(tag,attrs={},parent){
 const e=document.createElementNS("http://www.w3.org/2000/svg",tag);
 for(const [k,v] of Object.entries(attrs)) e.setAttribute(k,String(v));
 if(parent)parent.appendChild(e);
 return e;
}
function svgText(svg,text,x,y,attrs={}){
 const e=el("text",{x,y,...attrs},svg); e.textContent=text;return e;
}
function quantities(rows,mode,year){
 return rows.map(r=>mode==="area"?r.area_ha:r.area_ha*r.mean_tTS_ha[year]);
}
function buildFlow(target,rows,mode){
 const svg=document.getElementById(target),width=1010,height=470;
 if(!svg)throw Error("Saknar diagramyta "+target);
 svg.replaceChildren();
 svg.setAttribute("viewBox",`0 0 ${width} ${height}`);
 svg.setAttribute("role","img");
 svg.setAttribute("aria-label",mode==="area"?"Sankeydiagram över fasta hektar efter 2018 års marktäcke för tre rasterår":"Sankeydiagram med biomassans ton torrsubstans 2010 2015 2018 efter fast NMD2018-marktäcke");
 const xs=[75,490,905],bw=24,top=68,plotHeight=340;
 const qs=YEARS.map(year=>quantities(rows,mode,year));
 const totals=qs.map(q=>q.reduce((s,n)=>s+n,0)),max=Math.max(...totals);
 if(max<=0)throw Error("Ogiltiga totalvärden för "+mode);
 const pos=qs.map(q=>{
   const scaled=q.map(v=>v/max*plotHeight);
   let bottom=top+plotHeight;return scaled.map(h=>{const r=[bottom-h,bottom];bottom-=h;return r;});
 });
 const textUnit=mode==="area"?"ha":"ton TS";
 const title=mode==="area"?"Areal – fast NMD2018-marktäcke":"Modellerad torrmassa – samma celler";
 el("title",{},svg).textContent=title;
 YEARS.forEach((y,j)=>svgText(svg,y,xs[j],29,{"font-size":22,"font-weight":700,"text-anchor":"middle",fill:"#143b2e"}));
 YEARS.forEach((y,j)=>svgText(svg,mode==="area"?nf(totals[j])+" ha":nf(totals[j]/1e6,2)+" miljoner ton TS",xs[j],50,{"font-size":13,"text-anchor":"middle",fill:"#465a50"}));
 for(let j=0;j<2;j++){
  rows.forEach((r,i)=>{
   const a=pos[j][i],b=pos[j+1][i],x0=xs[j]+bw/2,x1=xs[j+1]-bw/2,dx=(x1-x0)*0.45;
   const path=`M ${x0} ${a[0]} C ${x0+dx} ${a[0]} ${x1-dx} ${b[0]} ${x1} ${b[0]} L ${x1} ${b[1]} C ${x1-dx} ${b[1]} ${x0+dx} ${a[1]} ${x0} ${a[1]} Z`;
   const e=el("path",{d:path,fill:COLORS[r.label],"fill-opacity":0.50},svg);
   el("title",{},e).textContent=r.label+" • "+YEARS[j]+": "+nf(qs[j][i],mode==="area"?2:0)+" "+textUnit+" • "+YEARS[j+1]+": "+nf(qs[j+1][i],mode==="area"?2:0)+" "+textUnit;
  });
 }
 YEARS.forEach((y,j)=>rows.forEach((r,i)=>{
    const p=pos[j][i],v=qs[j][i];
    const rect=el("rect",{x:xs[j]-bw/2,y:p[0],width:bw,height:Math.max(.15,p[1]-p[0]),fill:COLORS[r.label],stroke:"#fff","stroke-width":0.55},svg);
    el("title",{},rect).textContent=r.label+" • "+y+": "+nf(v,mode==="area"?2:0)+" "+textUnit;
 }));
 svgText(svg,"Marktäckeklassning: 2018 (oförändrad referens för alla år)",width/2,455,{"text-anchor":"middle","font-size":12,fill:"#506359"});
}
function buildDensity(rows){
 const canvas=document.getElementById("nmdFlowDensityChart");
 if(!canvas)throw Error("Saknar täthetsdiagram");
 if(typeof Chart==="undefined")throw Error("Chart.js kunde inte laddas");
 const datasets=rows.map(r=>({label:r.label,data:YEARS.map(y=>r.mean_tTS_ha[y]),borderColor:COLORS[r.label],backgroundColor:COLORS[r.label],borderWidth:2.5,pointRadius:4,pointHoverRadius:7,tension:.25}));
 new Chart(canvas,{type:"line",data:{labels:YEARS,datasets},options:{
  responsive:true,maintainAspectRatio:false,interaction:{mode:"nearest",intersect:false},
  plugins:{legend:{position:"bottom",labels:{boxWidth:13,boxHeight:13,padding:12}},
    tooltip:{callbacks:{label:c=>c.dataset.label+": "+nf(c.parsed.y,2)+" ton TS/ha"}}},
  scales:{x:{title:{display:true,text:"Rasterår"}},y:{beginAtZero:true,title:{display:true,text:"Ton TS/ha"}}}
 }});
}
function buildTable(rows){
 const body=document.getElementById("nmdFlowTableRows");
 if(!body)throw Error("Saknar tabell");
 body.replaceChildren();
 function row(cells,header=false){
  const tr=document.createElement("tr");
  cells.forEach((value,i)=>{const td=document.createElement(i===0?"th":"td");if(i===0)td.scope="row";td.textContent=value;tr.appendChild(td);});body.appendChild(tr);
 }
 rows.forEach(r=>row([r.label,nf(r.area_ha,2),...YEARS.map(y=>nf(r.area_ha*r.mean_tTS_ha[y],0)),...YEARS.map(y=>nf(r.mean_tTS_ha[y],2))]));
 const ha=rows.reduce((s,r)=>s+r.area_ha,0),mass=YEARS.map(y=>rows.reduce((s,r)=>s+r.area_ha*r.mean_tTS_ha[y],0));
 row(["Totalt",nf(ha,2),...mass.map(v=>nf(v,0)),...mass.map(v=>nf(v/ha,2))]);
}
async function start(){
 const status=document.getElementById("nmdFlowStatus");
 try{
  const res=await fetch("data/biomass_nmd2018_flow_2010_2018.json",{cache:"no-cache"});
  if(!res.ok)throw Error("Kunde inte ladda källverifierad tabell ("+res.status+")");
  const data=await res.json();
  if(data.status!=="VERIFIED_NMD2018_COMMON_MASK_2010_2015_2018"||data.analysis_crs!=="EPSG:3006"||data.pixel_size_m!==25||data.cells!==2456410)throw Error("Fel analysproveniens eller rasterpopulation");
  const rows=data.groups.map(r=>({...r,area_ha:r.cells*AREA_CELL_HA}));
  if(rows.length!==8||rows.some(r=>!COLORS[r.label]||YEARS.some(y=>!Number.isFinite(r.mean_tTS_ha[y])||r.mean_tTS_ha[y]<0)))throw Error("Ofullständiga NMD2018-grupper");
  const cells=rows.reduce((s,r)=>s+r.cells,0);
  if(cells!==data.cells)throw Error("Marktäckegruppernas cellantal summerar inte");
  const known={2010:11804189.7704,2015:9938103.599,2018:10643793.3499};
  for(const y of YEARS){
    const mass=rows.reduce((s,r)=>s+r.area_ha*r.mean_tTS_ha[y],0);
    if(Math.abs(mass-known[y])>2)throw Error("Ton TS avviker från verifierad referens för "+y);
  }
  buildFlow("nmdFlowArea",rows,"area");
  buildFlow("nmdFlowMass",rows,"mass");
  buildDensity(rows);buildTable(rows);
  const legend=document.getElementById("nmdFlowLegend");
  if(legend){legend.replaceChildren();rows.forEach(r=>{const node=document.createElement("span");node.className="nmd-flow-legend-item";const swatch=document.createElement("i");swatch.style.background=COLORS[r.label];swatch.setAttribute("aria-hidden","true");node.append(swatch,document.createTextNode(r.label));legend.append(node);});}
  status.textContent="Verifierat: "+nf(data.cells)+" gemensamt giltiga 25-metersceller ("+nf(cells*.0625,2)+" ha) i EPSG:3006. De tre diagrammen utgår från samma datatabell.";
  const link=document.getElementById("nmdFlowSource");if(link)link.href=data.source;
 }catch(err){
  if(status){status.textContent="Diagrammen kunde inte visas: "+err.message;status.style.color="#a43b25";}
  console.error(err);
 }
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start);else start();
})();