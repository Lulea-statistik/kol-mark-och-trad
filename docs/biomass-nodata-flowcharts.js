/* Three verified NMD2018 fixed-class flow views for the 2015 NoData cohort. */
(()=>{
"use strict";
const SOURCE="data/biomass_coverage_nmd2018_2010_2018.json";
const CELL_HA=0.0625;
const COLORS={"Skog utanför våtmark":"#277456","Temporärt ej skog":"#c88c5d","Skog på våtmark":"#718f31","Öppen våtmark":"#8cbf7c","Åkermark":"#dfbb53","Övrig öppen mark":"#c8ac60","Exploaterad mark":"#7e858c","Vatten":"#438cbe"};
const order=Object.keys(COLORS);
const fmt=(n,d=1)=>Number(n).toLocaleString("sv-SE",{minimumFractionDigits:d,maximumFractionDigits:d});
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function render(id,rows,metric,title,unit){
 const svg=document.getElementById(id);if(!svg)return;
 const vals=rows.map(r=>({r,a:metric(r,"2010"),b:metric(r,"2018")}));
 const totalA=vals.reduce((s,v)=>s+v.a,0),totalB=vals.reduce((s,v)=>s+v.b,0);
 const max=Math.max(totalA,totalB,0.00001),scale=330/max,top=105;
 let left=top,right=top;
 const h=520,w=1100, x1=260,x2=835,bandWidth=65;
 let paths="",blocks="",labels="";
 vals.forEach(({r,a,b})=>{
  const ah=a*scale,bh=b*scale,ly=left+ah/2,ry=right+bh/2;
  const color=COLORS[r.group],paint=esc(color);
  // Two ends represent measured data, never imply any measured 2015 biomass.
  const c1=x1+bandWidth,c2=x2;
  const p="M "+c1+" "+left+" C "+(c1+165)+" "+left+", "+(c2-165)+" "+right+", "+c2+" "+right+
          " L "+c2+" "+(right+bh)+" C "+(c2-165)+" "+(right+bh)+", "+(c1+165)+" "+(left+ah)+", "+c1+" "+(left+ah)+" Z";
  paths+='<path d="'+p+'" fill="'+paint+'" fill-opacity=".45"><title>'+esc(r.group)+': 2010 '+fmt(a,2)+' '+unit+'; 2015 NoData; 2018 '+fmt(b,2)+' '+unit+'</title></path>';
  blocks+='<rect x="'+x1+'" y="'+left+'" width="'+bandWidth+'" height="'+Math.max(ah,0.7)+'" fill="'+paint+'"/>'+
          '<rect x="'+x2+'" y="'+right+'" width="'+bandWidth+'" height="'+Math.max(bh,0.7)+'" fill="'+paint+'"/>';
  labels+='<rect x="15" y="'+(top+rows.indexOf(r)*28-7)+'" width="11" height="11" fill="'+paint+'"/>'+
          '<text x="32" y="'+(top+rows.indexOf(r)*28+3)+'" font-size="13" fill="#243b30">'+esc(r.group)+'</text>';
  left+=ah;right+=bh;
 });
 const sub=metric===area?"Samma celler: areal oförändrad, men 2015 saknar rastervärde.":metric===mass?"Bandens ändbredd visar ton TS 2010 respektive 2018; 2015 är okänd.":"Ändbredd visar klassvis medelvärde i ton TS/ha; dessa medelvärden är inte additiva.";
 // White gap at 2015 prevents implying a measured 2015 mass/density.
 svg.setAttribute("viewBox","0 0 "+w+" "+h);svg.setAttribute("role","img");
 svg.innerHTML='<title>'+esc(title)+'</title><desc>'+esc(sub)+'</desc>'+
 '<rect width="'+w+'" height="'+h+'" fill="#fcfdfa"/>'+
 '<text x="292" y="40" font-size="19" font-weight="700" fill="#243b30" text-anchor="middle">2010 – giltigt</text>'+
 '<text x="580" y="40" font-size="19" font-weight="700" fill="#81543a" text-anchor="middle">2015 – NoData</text>'+
 '<text x="870" y="40" font-size="19" font-weight="700" fill="#243b30" text-anchor="middle">2018 – giltigt</text>'+
 paths+blocks+
 '<rect x="535" y="76" width="93" height="377" rx="10" fill="#fcfdfa" stroke="#9a6e58" stroke-width="2" stroke-dasharray="7 5"/>'+
 '<text x="581" y="258" font-size="17" fill="#81543a" text-anchor="middle" transform="rotate(-90 581 258)">Inga observerade värden 2015</text>'+
 '<text x="292" y="484" font-size="17" font-weight="600" text-anchor="middle" fill="#243b30">'+(metric===density?'Klassmedelvärden, ej summerbara':fmt(totalA,0)+' '+esc(unit))+'</text>'+
 '<text x="870" y="484" font-size="17" font-weight="600" text-anchor="middle" fill="#243b30">'+(metric===density?'Klassmedelvärden, ej summerbara':fmt(totalB,0)+' '+esc(unit))+'</text>'+
 labels+
 '<text x="550" y="512" font-size="13" text-anchor="middle" fill="#52635b">'+esc(sub)+'</text>';
}
const area=(r,y)=>r.missing_2015_cells*CELL_HA;
const mass=(r,y)=>r.missing_2015_tonnes_TS[y];
const density=(r,y)=>mass(r,y)/area(r,y);
async function init(){
 const status=document.getElementById("biomassNoDataFlowStatus");
 try{
  const resp=await fetch(SOURCE,{cache:"no-store"});if(!resp.ok)throw Error("Resultatfil saknas");
  const d=await resp.json();
  if(d.status!=="VERIFIED_COVERAGE_2015_NODATA_AND_POSITIVE_2010_MASS"||d.analysis_crs!=="EPSG:3006"||d.cell_m!==25||d.missing_2015_valid_2010_2018_cells!==264484)throw Error("Fel verifieringsstatus eller rasterreferens");
  const rows=order.map(n=>d.groups.find(r=>r.group===n));
  if(rows.some(r=>!r)||rows.reduce((s,r)=>s+r.missing_2015_cells,0)!==264484)throw Error("Ofullständiga klassvärden");
  render("biomassNoDataFlowArea",rows,area,"2015 NoData: areal per NMD2018-klass","ha");
  render("biomassNoDataFlowDensity",rows,density,"2015 NoData: biomassadensitet i ton TS per hektar","ton TS/ha");
  render("biomassNoDataFlowMass",rows,mass,"2015 NoData: biomassa per NMD2018-klass","ton TS");
  const hectare=d.missing_2015_valid_2010_2018_cells*CELL_HA;
  status.textContent="Verifierat urval: "+fmt(hectare,2)+" ha med giltiga 2010/2018-värden men NoData 2015. 2010 års positiva biomassa omfattar "+fmt(d.positive_2010_missing_2015_valid_2018_cells*CELL_HA,2)+" ha. Inga saknade 2015-värden är skattade.";
 }catch(e){status.textContent="Flödesdiagrammen kunde inte läsas: "+e.message;status.style.color="#a43b25";}
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();