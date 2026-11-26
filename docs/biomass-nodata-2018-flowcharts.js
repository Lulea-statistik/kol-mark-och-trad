/* 2018 NoData: verified 2010-positive biomass cohorts, NMD2018 fixed classes. */
(()=>{
"use strict";
const COLORS={"Skog utanför våtmark":"#277456","Temporärt ej skog":"#c88c5d","Skog på våtmark":"#718f31","Öppen våtmark":"#8cbf7c","Åkermark":"#dfbb53","Övrig öppen mark":"#c8ac60","Exploaterad mark":"#7e858c","Vatten":"#438cbe"};
const order=Object.keys(COLORS);
const sv=(n,d=1)=>Number(n).toLocaleString("sv-SE",{minimumFractionDigits:d,maximumFractionDigits:d});
const escape=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const valid="lost2018_2015valid",missing="lost2018_2015missing";
function make(id,rows,kind){
 const svg=document.getElementById(id);if(!svg)return;
 const unit=kind==="area"?"ha":kind==="mass"?"ton TS":"ton TS/ha";
 const metric=(v,year)=>{
  if(year==="2010")return kind==="area"?v.area_ha:kind==="mass"?v.tonnes_TS_2010:(v.cells?v.tonnes_TS_2010/v.area_ha:0);
  if(v.tonnes_TS_2015===null)return null;
  return kind==="area"?v.area_ha:kind==="mass"?v.tonnes_TS_2015:(v.cells?v.tonnes_TS_2015/v.area_ha:0);
 };
 let all=rows.flatMap(r=>[valid,missing].map(k=>({name:r.group,color:COLORS[r.group],status:k,v:r.cohorts[k]}))).filter(e=>e.v.cells>0);
 const maximum=Math.max(...all.flatMap(e=>[metric(e.v,"2010"),metric(e.v,"2015")||0]),1);
 const maxStroke=kind==="density"?16:26;
 const width=x=>Math.max(1.8,Math.sqrt(x/maximum)*maxStroke);
 const height=110+all.length*37+65,w=1120;
 let content='<rect width="'+w+'" height="'+height+'" fill="#fcfdfa"/>'+
  '<text x="345" y="35" font-size="18" font-weight="700" text-anchor="middle" fill="#243b30">2010: biomassa finns</text>'+
  '<text x="675" y="35" font-size="18" font-weight="700" text-anchor="middle" fill="#243b30">2015: giltigt / NoData</text>'+
  '<text x="995" y="35" font-size="18" font-weight="700" text-anchor="middle" fill="#81543a">2018: NoData</text>';
 all.forEach((e,i)=>{
  const y=92+i*37, v0=metric(e.v,"2010"),v1=metric(e.v,"2015"),color=e.color;
  const label=e.name+(e.status===valid?" · 2015 giltig":" · 2015 NoData");
  content+='<rect x="10" y="'+(y-8)+'" width="12" height="12" fill="'+color+'"/>'+
    '<text x="28" y="'+(y+3)+'" font-size="12" fill="#23382c">'+escape(label)+'</text>'+
    '<path d="M 270 '+y+' C 420 '+y+', 465 '+y+', 570 '+y+'" fill="none" stroke="'+color+'" stroke-opacity=".75" stroke-width="'+width(v0)+'"><title>'+escape(e.name)+': 2010 '+sv(v0,2)+' '+unit+'</title></path>';
  if(v1===null){
    content+='<path d="M 570 '+y+' L 885 '+y+'" fill="none" stroke="#ac8a78" stroke-width="2" stroke-dasharray="5 6"/>'+
      '<text x="650" y="'+(y-9)+'" font-size="11" fill="#845e49">NoData</text>';
  }else{
    content+='<path d="M 570 '+y+' C 710 '+y+', 760 '+y+', 885 '+y+'" fill="none" stroke="'+color+'" stroke-opacity=".50" stroke-width="'+width(v1)+'"><title>2015: '+sv(v1,2)+' '+unit+'</title></path>';
  }
  content+='<rect x="897" y="'+(y-13)+'" width="93" height="24" rx="5" fill="#f4ebe5" stroke="#ad8b75" stroke-dasharray="4 3"/>'+
   '<text x="943" y="'+(y+3)+'" font-size="11" text-anchor="middle" fill="#745440">NoData</text>';
  content+='<text x="1010" y="'+(y+3)+'" font-size="12" fill="#304438">'+sv(v0,kind==="area"?2:1)+' '+unit+'</text>';
 });
 content+='<text x="560" y="'+(height-15)+'" font-size="14" text-anchor="middle" fill="#53645b">Linjetjocklek visar '+escape(unit)+' för respektive tillgängligt rasterår. 2018 är NoData, inte noll.</text>';
 svg.setAttribute("viewBox","0 0 "+w+" "+height);
 svg.setAttribute("role","img");
 svg.innerHTML='<title>2018 års NoData efter NMD2018, '+escape(unit)+'</title>'+content;
}
async function init(){
 const status=document.getElementById("biomassNoData2018Status");if(!status)return;
 try{
  const response=await fetch("data/biomass_2018_nodata_nmd2018.json",{cache:"no-store"});
  if(!response.ok)throw Error("Verifierad resultatfil saknas (HTTP "+response.status+"). Rasteranalysen behöver köras och resultatfilen publiceras.");
  const d=await response.json();
  if(d.status!=="VERIFIED_POSITIVE_2010_BIOMASS_2018_NODATA"||d.analysis_crs!=="EPSG:3006"||d.cell_m!==25)throw Error("Fel datastatus, CRS eller grid.");
  const lost=d.totals[valid].cells+d.totals[missing].cells;
  if(lost===0){
   status.textContent="Verifierat resultat: 0 celler (0 ha) med positiv biomassa 2010 saknar rastervärde 2018. Inget 2018-bortfall har påvisats inom den undersökta NMD2018-giltiga ytan och gemensamma 25 m-gridden. Därför finns inga värden att illustrera med flödesdiagram.";
   for(const id of ["biomassNoData2018Area","biomassNoData2018Density","biomassNoData2018Mass"]){
     const svg=document.getElementById(id);
     if(svg){svg.setAttribute("viewBox","0 0 850 115");svg.innerHTML='<rect width="850" height="115" rx="9" fill="#f3f7f3"/><text x="425" y="50" text-anchor="middle" font-size="21" fill="#277456" font-weight="700">Inget 2018-bortfall: 0 ha</text><text x="425" y="79" text-anchor="middle" font-size="15" fill="#4a6654">Positiv biomassa 2010 och NoData 2018 – inga sådana celler</text>';}
   }
   return;
  }
  const rows=order.map(name=>{
   const subset=d.rows.filter(x=>x.group===name),cohorts={};
   for(const k of [valid,missing]){
    const a=subset.map(x=>x.cohorts[k]);
    cohorts[k]={cells:a.reduce((s,x)=>s+x.cells,0),area_ha:a.reduce((s,x)=>s+x.area_ha,0),
      tonnes_TS_2010:a.reduce((s,x)=>s+x.tonnes_TS_2010,0),
      tonnes_TS_2015:k===valid?a.reduce((s,x)=>s+x.tonnes_TS_2015,0):null};
   }
   return {group:name,cohorts};
  });
  for(const kind of ["area","density","mass"])make("biomassNoData2018"+kind[0].toUpperCase()+kind.slice(1),rows,kind);
  const n=d.totals[valid].cells+d.totals[missing].cells;
  status.textContent="Verifierat 2018-bortfall: "+sv(n)+" celler ("+sv(n*.0625,2)+" ha) med positiv biomassa 2010 och NoData 2018. Därav "+sv(d.totals[valid].cells)+" giltiga 2015-celler och "+sv(d.totals[missing].cells)+" NoData även 2015.";
 }catch(err){status.textContent=err.message;status.style.color="#9e492d";}
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();