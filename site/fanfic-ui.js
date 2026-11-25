/* Read-only structured inspector, shared by studio screens. */
function sfStudioReadable(value,depth=0){
 const label=k=>String(k).replace(/([a-z])([A-Z])/g,"$1 $2").replace(/[_-]/g," ");
 if(value==null)return h("span",{class:"sub",text:"Not set"});
 if(typeof value!=="object")return h("span",{text:typeof value==="boolean"?(value?"Yes":"No"):String(value)});
 if(depth>=8)return h("pre",{text:JSON.stringify(value,null,2)});
 const entries=Array.isArray(value)?value.map((v,i)=>[String(i+1),v]):Object.entries(value);
 if(!entries.length)return h("p",{class:"sub",text:"None"});
 const box=h("div",{class:"sf-readable"});
 function add(items){for(const [k,v] of items){if(v!==null&&typeof v==="object"){const d=h("details",{},h("summary",{text:label(k)+(Array.isArray(v)?" ("+v.length+")":"")}));d.addEventListener("toggle",()=>{if(d.open&&d.children.length===1)d.append(sfStudioReadable(v,depth+1))});box.append(d)}else box.append(h("div",{class:"sf-readable-row"},h("strong",{text:label(k)}),sfStudioReadable(v,depth+1)))}}
 add(entries.slice(0,30));if(entries.length>30){let n=30;const more=h("button",{text:"Show more ("+(entries.length-n)+")",onclick:()=>{more.remove();add(entries.slice(n,n+30));n+=30;if(n<entries.length){more.textContent="Show more ("+(entries.length-n)+")";box.append(more)}}});box.append(more)}return box;
}
/* Fanfiction UI: source library. All writes go through adapters. */
(function(){
"use strict";
function library(se){
 const body=h("div",{class:"ff-ui"}), status=h("p",{class:"sub",role:"status","aria-live":"polite"}), preview=h("div",{}), list=h("div",{}); let pending=null, controller=null, epoch=0;
 const file=h("input",{type:"file",accept:".epub,.txt,.md"}), title=h("input",{placeholder:"Optional source title"}), kind=sel("novel",["novel","manga","anime","wiki","notes"].map(x=>[x,x]),()=>{}), target=h("select",{});
 const run=h("button",{class:"primary",text:"Preview import",onclick:async()=>{
  if(!file.files[0]){status.textContent="Choose a source file first.";return}
  const ticket=++epoch;controller?.abort();controller=new AbortController();pending=null;preview.replaceChildren();run.disabled=true;status.textContent="Reading source…";
  try{
   const result=await ffImportPreview(file.files[0],{title:title.value.trim(),kind:kind.value,universeId:target.value||undefined,signal:controller.signal,onProgress:(i,n)=>{if(ticket===epoch)status.textContent="Indexing "+i+" / "+n}});
   if(ticket!==epoch||!body.isConnected)return;
   if(!result.ok){status.textContent=result.reason||"Import failed";return}
   pending=result;const p=result.preview;status.textContent="Preview ready. Nothing has been saved.";
   preview.append(h("div",{class:"ff-panel"},h("b",{text:"Revision "+p.rev}),h("p",{text:"Added: "+JSON.stringify(p.added)+" · Duplicates: "+JSON.stringify(p.duplicate)}),h("p",{text:"Conflicts: "+JSON.stringify(p.conflicts)}),h("p",{text:"Detected names: "+(p.names||[]).join(", ")}),h("details",{},h("summary",{text:"Index report"}),sfStudioReadable(p.report)),h("button",{class:"primary",text:"Confirm and save source",onclick:()=>{
    if(!pending||!body.isConnected)return;const current=pending;pending=null;
    try{const r=current.commit();status.textContent=r.applied?"Source saved. Story revision unchanged.":r.reason||"No changes applied";preview.replaceChildren();refresh()}catch(e){status.textContent=String(e.message||e)}
   }})));
  }catch(e){if(ticket===epoch)status.textContent=String(e.message||e)}finally{if(ticket===epoch)run.disabled=false}
 }});
 function refresh(){const rows=ffListUniverses(),old=target.value;target.replaceChildren(h("option",{value:"",text:"New universe"}),...rows.map(u=>h("option",{value:u.id,text:u.name})));target.value=rows.some(u=>u.id===old)?old:"";list.replaceChildren(...rows.map(u=>h("details",{class:"ff-panel"},h("summary",{text:u.name+" · revision "+u.rev}),h("p",{text:u.sources+" sources · "+u.chapters+" chapters · "+u.chars+" characters · "+u.events+" events"}),...(ffUniverse(u.id)?.sources||[]).map(s=>h("p",{text:s.title+" · "+s.kind+" · "+(s.chapters||[]).length+" chapters"})))));if(!rows.length)list.append(h("p",{class:"sub",text:"No imported universes yet."}))}
 refresh();if(se?.canon?.universe)target.value=se.canon.universe;
 body.append(h("p",{class:"sub",text:"Sources are indexed locally. Imports do not change a playthrough's pinned revision."}),list,h("h3",{text:"Import source"}),fld("Universe",target),fld("Source file",file),fld("Title",title),fld("Source type",kind),h("div",{class:"row"},run,h("button",{text:"Cancel import",onclick:()=>{epoch++;controller?.abort();pending=null;run.disabled=false;preview.replaceChildren();status.textContent="Import cancelled. No pending changes saved."}})),status,preview);
 sheet("Source Library",body);
}
window.SFFanUI=Object.assign(window.SFFanUI||{},{library});
})();

(function(){
"use strict";
const options=(xs)=>xs.map(x=>[x,x]), label=x=>String(x).replace(/([a-z])([A-Z])/g,"$1 $2");
const panel=(...kids)=>h("div",{class:"ff-panel"},...kids);
const dump=x=>sfStudioReadable(x);
const button=(text,onclick)=>h("button",{text,onclick});
function screen(se,title,build){
 const body=h("div",{class:"ff-ui"}),status=h("p",{role:"status","aria-live":"polite",class:"sub"}),content=h("div",{class:"ff-ui"});
 const refresh=()=>{content.replaceChildren();const state=ffState(se);if(!state){content.append(h("p",{text:"No attached universe."}));return}build(content,state,apply,refresh)};
 const apply=fn=>{try{const r=fn();status.textContent=r.applied?"Saved":r.reason||"No change applied";if(r.applied)refresh()}catch(e){status.textContent=String(e.message||e)}};
 body.append(status,content);refresh();sheet(title,body);
}
const universe=se=>ffU(se);
const chars=se=>Object.entries(universe(se)?.chars||{}).map(([id,c])=>[id,c.name||id]);
function studio(se){screen(se,"Fanfiction Studio",(b,s,apply)=>{
 b.append(panel(h("b",{text:s.universe.name}),h("p",{text:"Pinned revision "+s.universe.pinned+" · Source revision "+s.universe.rev}),button("Source Library",()=>window.SFFanUI.library(se))));
 const types=["oc","self","takeover","transmigration","reincarnation","regression","fixit","whatif","divergence","au","crossover","rolereversal","parallel","nextgen","prequel","sequel","missing","slice","ensemble","altending"];
 const selected=new Set(s.mode.types||[]), name=h("input",{value:s.mode.player?.name||""}),desc=h("textarea",{value:s.mode.player?.desc||"",rows:3}),take=sel(s.mode.takeover||"",[["","None"],...chars(se)],()=>{});
 b.append(panel(h("b",{text:"Insertion modes"}),...types.map(t=>chk(t,selected.has(t),v=>v?selected.add(t):selected.delete(t))),fld("Original character name",name),fld("Description",desc),fld("Takeover character (mode selection only)",take),button("Save insertion settings",()=>apply(()=>ffSetMode(se,{types:[...selected],player:{...s.mode.player,name:name.value,desc:desc.value},takeover:take.value||null})))));
 const pov=sel(s.pov.mode||"second",options(["first","second","thirdLimited","omniscient","multi"]),()=>{}),ch=h("input",{type:"number",min:0,value:s.position.ch||0}),order=h("input",{type:"number",min:0,value:s.position.order||0});
 b.append(panel(fld("Perspective",pov),button("Save perspective",()=>apply(()=>ffSetPOV(se,{mode:pov.value}))),fld("Source chapter",ch),fld("Event order",order),button("Save position",()=>{if(!Number.isInteger(+ch.value)||+ch.value<0||!Number.isInteger(+order.value)||+order.value<0)return;apply(()=>ffSetPosition(se,{ch:+ch.value,order:+order.value}))})));
})}
function canon(se){screen(se,"Canon Manager",(b,s,apply)=>{
 for(const [k,v] of Object.entries(s.rules))b.append(fld(label(k),sel(v,options(["locked","adaptive","free"]),x=>apply(()=>ffSetRule(se,k,x)))));
 const target=sel("",[["","Select target"],...s.events.map(e=>[e.id,e.title]),...chars(se)],()=>{}),note=h("textarea",{rows:3,placeholder:"Approved change"});
 b.append(panel(fld("Exception target",target),fld("Exception",note),button("Approve exception",()=>{if(target.value&&note.value.trim())apply(()=>ffException(se,target.value,note.value.trim()))})),panel(h("b",{text:"Existing exceptions and locks"}),dump(se.canon.exceptions||[]),dump(se.canon.locks||[])),panel(h("b",{text:"Change history"}),button("Undo last canon change",()=>apply(()=>ffUndo(se))),dump(ffHistory(se).slice(-30).reverse())));
})}
function timeline(se){screen(se,"Timeline & Fates",(b,s,apply)=>{
 b.append(h("p",{text:"Source chapter "+(s.position.ch??"Unknown")}),h("b",{text:"Upcoming possible events"}),dump(s.upcoming||[]));
 const q=h("input",{placeholder:"Filter events"}),results=h("div",{class:"ff-ui"});let limit=50;
 function draw(){const matches=s.events.filter(e=>(e.title+" "+e.status).toLowerCase().includes(q.value.toLowerCase()));results.replaceChildren(...matches.slice(0,limit).map(e=>{
 const change=sel("prevented",options(["unchanged","altered","prevented","delayed","replaced","protected"]),()=>{}),why=h("input",{placeholder:"Reason"}),impact=h("div",{});
 return panel(h("b",{text:e.title}),h("p",{text:e.status||"unchanged"}),h("p",{text:e.why||""}),fld("Change",change),fld("Reason",why),button("Preview impact",()=>impact.replaceChildren(dump(ffImpact(se,e.id,change.value)))),impact,button("Apply event change",()=>{if(why.value.trim())apply(()=>ffEventStatus(se,e.id,change.value,why.value.trim()))}),button("Lock event",()=>apply(()=>ffLock(se,"event",e.id,true))),button("Unlock event",()=>apply(()=>ffLock(se,"event",e.id,false))));
 }));if(matches.length>limit)results.append(button("Show more",()=>{limit+=50;draw()}))}
 q.addEventListener("input",()=>{limit=50;draw()});draw();b.append(q,results,h("h3",{text:"Fates"}));
 for(const [id,f] of Object.entries(s.fates))b.append(panel(h("b",{text:chars(se).find(c=>c[0]===id)?.[1]||id}),h("p",{text:"Original: "+(f.original||"Unknown")+" · Current: "+(f.current||"Unknown")}),sel(f.target||"adapt",options(["preserve","adapt","protected","free"]),v=>apply(()=>ffSetFate(se,id,v)))));
})}
function inspector(se){screen(se,"Character Inspector",(b)=>{
 const ids=chars(se),pick=sel(ids[0]?.[0]||"",ids,()=>draw()),out=h("div",{class:"ff-ui"});
 function draw(){const id=pick.value;if(!id){out.replaceChildren(h("p",{text:"No indexed characters."}));return}out.replaceChildren(panel(h("b",{text:"Identity"}),dump(ffIdentity(se,id))),panel(h("b",{text:"Character knowledge"}),dump(ffKnows(se,id))),panel(h("b",{text:"Directional relationships (author view)"}),dump(ffRelationships(se,{involving:id,includePrivate:true}))))}
 b.append(fld("Character",pick),out);draw();
})}
function romance(se){screen(se,"Romance Preferences",(b,s,apply)=>{
 const r=se.canon.romance||{},pref=sel(r.pref||"none",options(["bl","gl","straight","any","none"]),()=>eligible()),focus=sel(r.focus||"optional",options(["background","optional","balanced","central"]),()=>{}),pace=sel(r.pacing||"natural",options(["slow","natural","fast"]),()=>{}),canon=sel(r.canonRelationships||"adaptive",options(["preserve","adaptive","au"]),()=>{}),interest=h("select",{});
 function eligible(){const old=interest.value||r.interest||"";const ids=pref.value==="none"?[]:chars(se).filter(([id])=>ffRomanceAllowed(se,"player",id).ok);interest.replaceChildren(h("option",{value:"",text:"No preferred interest"}),...ids.map(([id,n])=>h("option",{value:id,text:n})));interest.value=ids.some(([id])=>id===old)?old:""}
 eligible();b.append(h("p",{class:"sub",text:"Adult fictional characters only. Non-explicit, independent character choices."}),fld("Preference",pref),fld("Narrative focus",focus),fld("Pacing",pace),fld("Canon relationships",canon),fld("Eligible fictional interest",interest),button("Save preferences",()=>apply(()=>ffSetRomance(se,{pref:pref.value,focus:focus.value,pacing:pace.value,canonRelationships:canon.value,interest:interest.value||null}))),h("p",{class:"sub",text:"If romance is currently off, save an enabled preference first to populate eligible interests."}));
})}
function realworld(se){screen(se,"Real-World Story",(b,s)=>{
 const u=universe(se);b.append(h("b",{text:"Alternate-reality fiction"}),h("p",{text:"Universe type: "+(u?.type||"fictional")}),panel(h("b",{text:"Public figures — professional context only"}),...Object.values(u?.people||{}).map(p=>h("p",{text:p.name+" · "+(p.publicRole||"Public figure")}))),panel(h("b",{text:"Public source records"}),...((u?.records||[]).filter(r=>r.verified).slice(0,50).map(r=>h("p",{text:(r.verified||"uncertain")+" · "+(r.date||"Undated")+" · "+r.text})))),button("Source Library",()=>window.SFFanUI.library(se)));
})}
function competition(se){screen(se,"Competition Studio",(b,s,apply)=>{
 const id=h("input",{placeholder:"Competition ID"}),seed=h("input",{value:"round-1"}),factors=["performance","votes","skill","teamwork"],weights=[40,25,20,10].map(v=>h("input",{type:"number",min:0,max:100,value:v})),random=h("input",{type:"number",min:0,max:20,value:5}),entries=h("textarea",{rows:5,placeholder:'JSON entries: [{"id":"contestant","factors":{"performance":80,"votes":70,"skill":75,"teamwork":90}}]'}),out=h("div",{});let result=null,recordId="";
 const preview=()=>{result=null;out.replaceChildren();try{const rows=JSON.parse(entries.value),w=weights.map(x=>+x.value),rnd=+random.value;if(!id.value.trim()||!seed.value.trim()||!Array.isArray(rows)||!rows.length||new Set(rows.map(x=>x.id)).size!==rows.length||rows.some(x=>typeof x.id!=="string"||!x.id.trim()||factors.some(k=>!Number.isFinite(x.factors?.[k])||x.factors[k]<0||x.factors[k]>100))||w.some(x=>!Number.isFinite(x)||x<0||x>100)||!w.some(x=>x>0)||rnd<0||rnd>20||!Number.isFinite(rnd))throw Error("Enter valid unique contestants, factors, weights, seed and ID.");recordId=id.value.trim();result=ffRank(rows,{weights:Object.fromEntries(factors.map((k,i)=>[k,w[i]])),random:rnd},seed.value);out.append(dump(result),button("Record previewed result",()=>{if(result)apply(()=>ffRecordCompetition(se,recordId,result))}))}catch(e){out.append(h("p",{text:String(e.message||e)}))}};
 for(const el of [id,seed,...weights,random,entries])el.addEventListener("input",()=>{result=null;out.replaceChildren()});
 b.append(h("p",{class:"sub",text:"Simulated results only. Existing results cannot be overwritten here."}),fld("Competition ID",id),fld("Seed",seed),...factors.map((k,i)=>fld(k,weights[i])),fld("Random variation",random),fld("Contestant factors",entries),button("Preview rankings",preview),out,h("b",{text:"Recorded results"}),dump(se.canon.competitions||{}));
})}
function continuity(se){screen(se,"Continuity Center",(b,s)=>{
 b.append(panel(h("b",{text:"Event conflicts"}),dump(s.conflicts||[])),panel(h("b",{text:"Validation"}),dump(ffValidate(se))),panel(h("b",{text:"Reply warnings"}),...se.turns.flatMap((t,i)=>[...(t.ffc||[]),...(t.voice||[])].map(w=>h("p",{text:"Turn "+(i+1)+" · "+w.kind+(w.name?" · "+w.name:"")+": "+w.text}))).slice(-100)));
})}
Object.assign(window.SFFanUI,{studio,canon,timeline,inspector,romance,realworld,competition,continuity});
})();

(function(){
"use strict";
const read=k=>{try{return localStorage.getItem(k)||""}catch(e){return ""}};
const write=(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}};
window.SFFanUI.polishMenu=function(bg,se){
 const drawer=bg.querySelector(".drawer"),groups=[...drawer.querySelectorAll("details[name='sf-novel-menu']")];if(!groups.length)return;
 const key="sf-ui-menu-"+se.id,last=read(key),search=h("input",{type:"search",placeholder:"Search story tools","aria-label":"Search story tools"}),favorites=h("div",{class:"ff-menu-favorites"}),favKey="sf-ui-favorites";let fav=[];try{fav=JSON.parse(read(favKey)||"[]");if(!Array.isArray(fav))fav=[]}catch(e){}
 const groupName=g=>g.querySelector("summary").textContent,rows=groups.flatMap(g=>[...g.children].filter(x=>x.tagName!=="SUMMARY").map((el,i)=>({el,g,id:groupName(g)+":"+(el.classList.contains("drow")?el.firstChild?.textContent:el.textContent).trim(),name:el.textContent.trim()})));
 let searching=false;
 function drawFavorites(){favorites.replaceChildren();const chosen=rows.filter(r=>fav.includes(r.id));if(chosen.length)favorites.append(h("p",{class:"sub",text:"Favorites"}),...chosen.map(r=>h("button",{text:r.name,onclick:()=>{if(r.el.tagName==="BUTTON")r.el.click();else{r.g.open=true;r.el.scrollIntoView({block:"nearest"})}}})))}
 const manage=h("details",{class:"ff-menu-favorites"},h("summary",{text:"Manage favorites"}),...rows.map(r=>chk(r.name,fav.includes(r.id),v=>{fav=v?[...new Set([...fav,r.id])]:fav.filter(x=>x!==r.id);write(favKey,JSON.stringify(fav));drawFavorites()})));
 drawer.insertBefore(h("div",{class:"ff-menu-search"},search,favorites),groups[0]);(groups.find(g=>groupName(g)==="Advanced & Settings")||groups[groups.length-1]).append(manage);drawFavorites();
 for(const g of groups){if(groupName(g)===last)g.open=true;g.addEventListener("toggle",()=>{if(!searching&&g.open)write(key,groupName(g))})}
 search.addEventListener("input",()=>{const q=search.value.trim().toLowerCase();searching=!!q;for(const g of groups){const matches=rows.filter(r=>r.g===g);for(const r of matches)r.el.hidden=!!q&&!r.name.toLowerCase().includes(q)&&!groupName(g).toLowerCase().includes(q);g.hidden=!!q&&matches.every(r=>r.el.hidden);if(q)g.open=false}if(q){const first=groups.find(g=>!g.hidden);if(first)first.open=true}else{for(const g of groups)g.open=groupName(g)===read(key)}});
};
})();

(function(){
"use strict";
const btn=(text,onclick)=>h("button",{text,onclick}), panel=(...kids)=>h("div",{class:"ff-panel"},...kids), dump=x=>sfStudioReadable(x), opts=a=>a.map(x=>[x,x]);
function open(se,title,build){
 const body=h("div",{class:"ff-ui"}),status=h("p",{role:"status","aria-live":"polite"}),content=h("div",{class:"ff-ui"});
 const refresh=()=>{content.replaceChildren();build(content,apply,refresh)};
 const apply=fn=>{try{const r=fn();status.textContent=(r.applied??r.ok)?"Saved":r.reason||"No change applied";if(r.applied??r.ok)refresh()}catch(e){status.textContent=String(e.message||e)}};
 body.append(status,content);refresh();sheet(title,body);
}
const nameOf=(se,id)=>id==="player"?(se.char?.name||"Player"):se.canon?(ffIdentity(se,id)?.canon?.name||id):id;
function names(se){return [...new Set([...Object.keys(chNpcs(se)||{}),...chRelationships(se).flatMap(r=>[nameOf(se,r.a),nameOf(se,r.b)]),...memQuery(se,{layer:"character",limit:1000}).flatMap(r=>r.who||[])])].filter(Boolean).sort()}
function web(se){open(se,"Relationship Web",(b,apply)=>{
 let zoom=1;function editRel(r){const keys=["trust","affection","respect","familiarity","rivalry"],fields=keys.map(k=>[k,h("input",{type:"number",min:["familiarity","rivalry"].includes(k)?0:-100,max:100,value:r[k]??0})]);return h("details",{},h("summary",{text:"Edit relationship"}),...fields.map(([k,e])=>fld(k,e)),btn("Save relationship",()=>apply(()=>chSetRelationship(se,r.a,r.b,Object.fromEntries(fields.map(([k,e])=>[k,Number(e.value)]))))))}
 const all=chRelationships(se),ids=[...new Set(all.flatMap(r=>[r.a,r.b]))],pick=sel("",[["","All characters"],...ids.map(id=>[id,nameOf(se,id)])],()=>draw()),out=h("div",{class:"ff-ui"}),graph=h("div",{});
 function draw(){const rows=all.filter(r=>!pick.value||r.a===pick.value||r.b===pick.value);out.replaceChildren(...rows.slice(0,100).map(r=>panel(h("b",{text:nameOf(se,r.a)+" → "+nameOf(se,r.b)}),h("p",{text:chLabel(r)+(r.private?" · Private (author view)":"")}),...["trust","affection","respect","familiarity","rivalry"].map(k=>h("p",{text:k+": "+(r[k]??0)})),h("details",{},h("summary",{text:"Event history"}),dump(chHistory(se,r.a,r.b))),editRel(r))));if(!rows.length)out.append(h("p",{text:"No recorded relationships."}));
 graph.replaceChildren();const nodes=[...new Set(rows.flatMap(r=>[r.a,r.b]))].slice(0,20);if(!nodes.length)return;const ns="http://www.w3.org/2000/svg",svg=document.createElementNS(ns,"svg");const span=400/zoom;svg.setAttribute("viewBox",((400-span)/2)+" "+((400-span)/2)+" "+span+" "+span);svg.setAttribute("width","100%");svg.setAttribute("aria-label","Directional relationship graph");const pos=new Map(nodes.map((id,i)=>[id,[200+145*Math.cos(i*2*Math.PI/nodes.length),200+145*Math.sin(i*2*Math.PI/nodes.length)]]));
 function shape(tag,attrs){const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));svg.append(e);return e}
 for(const r of rows){if(!pos.has(r.a)||!pos.has(r.b)||r.a===r.b)continue;const [x,y]=pos.get(r.a),[u,v]=pos.get(r.b),d=Math.hypot(u-x,v-y),dx=(u-x)/d,dy=(v-y)/d;shape("line",{x1:x+dx*23,y1:y+dy*23,x2:u-dx*27,y2:v-dy*27,stroke:"currentColor","stroke-opacity":0.4});shape("polygon",{points:[ [u-dx*23,v-dy*23],[u-dx*34-dy*5,v-dy*34+dx*5],[u-dx*34+dy*5,v-dy*34-dx*5]].map(p=>p.join(",")).join(" "),fill:"currentColor"})}
 for(const id of nodes){const [x,y]=pos.get(id);shape("circle",{cx:x,cy:y,r:22,fill:"#526f99"});const name=nameOf(se,id),src=typeof cvArt==="function"?cvArt(se,"cast:"+name):null;if(src){shape("image",{x:x-17,y:y-17,width:34,height:34,href:src,preserveAspectRatio:"xMidYMid slice"})}shape("text",{x,y:y+(src?34:4),"text-anchor":"middle",fill:src?"currentColor":"white","font-size":10}).textContent=name.slice(0,12)}
 graph.append(svg,h("p",{class:"sub",text:"Graph shows up to 20 characters. Select a character to narrow the view."}));
 }b.append(h("p",{class:"sub",text:"Author view: private relationships may be visible."}),fld("Character",pick),h("div",{style:"display:flex;gap:8px;flex-wrap:wrap"},btn("Zoom in",()=>{zoom=Math.min(3,zoom+0.25);draw()}),btn("Zoom out",()=>{zoom=Math.max(0.75,zoom-0.25);draw()}),btn("Reset zoom",()=>{zoom=1;draw()}),btn("Undo relationship edit",()=>apply(()=>chUndo(se)))),graph,out);draw();
})}
function journal(se){open(se,"Character Journal",(b,apply)=>{
 const ns=names(se),pick=sel(ns[0]||"",ns.map(n=>[n,n]),()=>draw()),out=h("div",{class:"ff-ui"}),filter=sel("all",opts(["all","did","witnessed","learned","believes","rumor","feels","intends"]),()=>draw()),known=h("input",{type:"checkbox"});
 function draw(){const n=pick.value;out.replaceChildren();if(!n)return;const rows=chJournal(se,n).filter(r=>(filter.value==="all"||r.role===filter.value)&&(!known.checked||r.playerKnows));out.append(...rows.slice(-100).reverse().map(r=>panel(h("b",{text:r.role+" · turn "+r.t}),h("p",{text:r.text}),h("p",{class:"sub",text:(r.source||"Unknown source")+" · "+(r.playerKnows?"Player knows":"Author only")}))));if(!rows.length)out.append(h("p",{text:"No matching journal entries."}));const dev=chDevelopments(se,n),note=h("textarea",{rows:2});out.append(panel(h("b",{text:"Development notes (author view)"}),dump(dev),fld("New development note",note),btn("Add note",()=>{if(note.value.trim())apply(()=>chAddDevelopment(se,n,note.value.trim()))})))}
 known.addEventListener("change",draw);b.append(fld("Character",pick),fld("Entry type",filter),h("label",{},known," Player-known entries only"),out);draw();
})}
function agenda(se){open(se,"NPC Agenda",(b,apply)=>{
 const ns=names(se),pick=sel(ns[0]||"",ns.map(n=>[n,n]),()=>draw()),out=h("div",{class:"ff-ui"}),day=chStoryDay(se);
 function draw(){out.replaceChildren();if(!pick.value)return;const n=pick.value,a=chAgenda(se,n,day,day+7)||{},p=chNpcs(se)[n]||{goals:[],schedule:[]};
 const goals=h("div",{class:"ff-ui"}),schedule=h("div",{class:"ff-ui"}),gr=[],sr=[];
 function goal(g={}){if(typeof g==="string")g={text:g};const text=h("textarea",{rows:2,value:g.text||""}),priority=h("input",{type:"number",min:1,max:5,value:g.priority||3}),term=sel(g.term||"short",opts(["short","long"]),()=>{}),conflicts=h("input",{value:(g.conflictsWith||[]).join(", ")});const row={read:()=>({...g,text:text.value.trim(),priority:Number(priority.value),term:term.value,conflictsWith:conflicts.value.split(",").map(x=>x.trim()).filter(Boolean)})};const el=panel(fld("Goal",text),fld("Priority (1–5)",priority),fld("Duration",term),fld("Conflicting goal IDs",conflicts),btn("Remove from draft",()=>{gr.splice(gr.indexOf(row),1);el.remove()}));gr.push(row);goals.append(el)}
 function slot(v={}){const d=h("input",{type:"number",min:0,value:v.day??day}),where=h("input",{value:v.where||""}),doing=h("input",{value:v.doing||""});const row={read:()=>({...v,day:Number(d.value),where:where.value,doing:doing.value})};const el=panel(fld("Story day",d),fld("Location",where),fld("Activity",doing),btn("Remove from draft",()=>{sr.splice(sr.indexOf(row),1);el.remove()}));sr.push(row);schedule.append(el)}
 (p.goals||[]).forEach(goal);(p.schedule||[]).forEach(slot);
 out.append(panel(h("b",{text:"Current activity"}),h("p",{text:[a.where,a.doing].filter(Boolean).join(" · ")||"No scheduled activity"}),...(a.developments||[]).map(x=>h("p",{text:"Day "+x.day+" · "+x.text}))),panel(h("b",{text:"Recorded off-screen developments"}),...chAgendaLog(se).filter(x=>x.name===n).map(x=>h("p",{text:"Day "+x.day+" · "+x.text}))),h("h3",{text:"Goals"}),goals,btn("Add goal",()=>goal()),h("h3",{text:"Schedule"}),schedule,btn("Add commitment",()=>slot()),btn("Save plan",()=>apply(()=>chSetNpc(se,n,{goals:gr.map(x=>x.read()).filter(x=>x.text),schedule:sr.map(x=>x.read())}))));
 }
 b.append(h("p",{text:"Story day "+day+" · Viewing does not advance time. Draft edits are saved only when you select Save plan."}),fld("Character",pick),out);draw();
})}
function memory(se){open(se,"Memory Studio",(b,apply)=>{
 const layers=["permanent","working","episodic","semantic","character","relationship","temporal","world","universe"],q=h("input",{placeholder:"Search memories"}),layer=sel("",[["","All layers"],...opts(layers)],()=>draw()),deleted=sel("active",opts(["active","deleted","all"]),()=>draw()),out=h("div",{class:"ff-ui"});let limit=30;
 function draw(){const rows=memQuery(se,{text:q.value,layer:layer.value||undefined,deleted:deleted.value==="deleted"?"only":deleted.value==="all",limit:limit+1});out.replaceChildren(...rows.slice(0,limit).map(r=>{const edit=h("textarea",{rows:3});edit.value=r.text;return panel(h("b",{text:r.layer+" · "+r.kind}),h("p",{class:"sub",text:r.src+" · "+r.id+(r.pin?" · Pinned":"")+(r.lock?" · Locked":"")}),h("p",{text:r.text}),h("details",{},h("summary",{text:"Edit and history"}),edit,btn("Save text",()=>apply(()=>memEdit(se,r.id,{text:edit.value}))),btn(r.pin?"Unpin":"Pin",()=>apply(()=>memPin(se,r.id,!r.pin))),btn(r.lock?"Unlock":"Lock",()=>apply(()=>memLock(se,r.id,!r.lock))),btn(r.deleted?"Restore":"Soft delete",()=>apply(()=>r.deleted?memRestore(se,r.id):memDelete(se,r.id))),dump(memHistory(se,r.id))))}));if(rows.length>limit)out.append(btn("Show more",()=>{limit+=30;draw()}));if(!rows.length)out.append(h("p",{text:"No matching memories."}))}
 q.addEventListener("input",()=>{limit=30;draw()});const add=h("textarea",{rows:3}),addLayer=sel("permanent",opts(layers),()=>{});
 b.append(h("p",{text:memView(se).records.length+" records across nine layers"}),dump(memStatus(se)),btn("Undo last memory edit",()=>apply(()=>memUndo(se))),fld("Search",q),fld("Layer",layer),fld("Visibility",deleted),out,panel(h("b",{text:"Add memory"}),addLayer,add,btn("Save memory",()=>{if(add.value.trim())apply(()=>memAdd(se,{layer:addLayer.value,text:add.value.trim(),kind:"note"}))})),h("h3",{text:"Open conflicts"}),...memConflicts(se).map(c=>{const choice=sel("dismissed",opts(["keep-narrator","keep-step","dismissed"]),()=>{}),records=memView(se).records.filter(r=>!r.deleted),pick=sel("",[["","Select memory to correct"],...records.map(r=>[r.id,r.text.slice(0,100)])],()=>{edit.value=records.find(r=>r.id===pick.value)?.text||""}),edit=h("textarea",{rows:3});return panel(dump(c),choice,btn("Mark resolved (no memory edit)",()=>apply(()=>memResolve(se,c.id,choice.value))),h("details",{},h("summary",{text:"Resolve with corrected memory"}),pick,edit,btn("Save correction and resolve",()=>{if(pick.value&&edit.value.trim())apply(()=>memResolve(se,c.id,"edited",{edit:{id:pick.value,patch:{text:edit.value.trim()}}}))})))}),panel(h("b",{text:"Detected contradictions"}),dump(SFMem2.contradictions(memView(se)))));draw();
})}
function director(se){open(se,"Story Director",(b,apply)=>{
 const s=dirSettings(se),levels=["off","low","secondary","balanced","high"];b.append(chk("Enable Story Director",s.enabled,v=>apply(()=>dirEnable(se,v))),h("p",{class:"sub",text:"Guidance never overrides player choices."}),h("h3",{text:"Narrative focus"}),...Object.entries(s.focus).map(([k,v])=>fld(k,sel(v,opts(levels),x=>apply(()=>dirSet(se,{focus:{[k]:x}}))))));
 for(const [k,values] of Object.entries({pacing:["slow","natural","fast"],dialogue:levels,humor:levels,suspense:levels,description:levels,timeSkips:["ask","allowed","never"],subplots:["none","allowed","encouraged"],canonSpeed:["slow","natural","fast"]}))b.append(fld(k,sel(s[k],opts(values),v=>apply(()=>dirSet(se,{[k]:v})))));
 b.append(panel(h("b",{text:"Recent narrative analysis (heuristic)"}),dump(dirAnalyze(se))));
})}
Object.assign(window.SFFanUI,{web,journal,agenda,memory,director});
})();

(function(){
"use strict";
const button=(text,onclick)=>h("button",{text,onclick}), dump=x=>sfStudioReadable(x), panel=(...kids)=>h("div",{class:"ff-panel"},...kids);
function studio(se,title,build){
 const body=h("div",{class:"ff-ui"}),status=h("p",{role:"status","aria-live":"polite"}),content=h("div",{class:"ff-ui"});
 function refresh(){content.replaceChildren();build(content,apply)}
 function apply(fn){try{const r=fn();status.textContent=(r.applied??r.ok)?"Saved"+(r.fired?.length?" · Consequences: "+JSON.stringify(r.fired):""):r.reason||"No change";if(r.applied??r.ok)refresh()}catch(e){status.textContent=String(e.message||e)}}
 body.append(status,content);refresh();sheet(title,body);
}
function universe(se){studio(se,"Universe Studio",(b,apply)=>{
 const list=ffListUniverses(),u=ffU(se),p=ffUpgradePreview(se);
 b.append(h("p",{text:"Shared universe library · Playthroughs retain their own outcomes."}),...list.map(x=>panel(h("b",{text:x.name}),h("p",{text:"Revision "+x.rev+" · "+x.chapters+" chapters · "+x.events+" events"}))),button("Import sources",()=>window.SFFanUI.library(se)));
 if(!u)return;
 b.append(panel(h("b",{text:u.name+" · pinned revision "+se.canon.rev}),dump(p),button("Apply previewed revision upgrade",()=>{if(p&&p.to!==p.from&&confirm("Upgrade this playthrough to revision "+p.to+"?"))apply(()=>ffUpgrade(se))}),button("Undo canon change",()=>apply(()=>ffUndo(se)))));
 const records=memQuery(se,{limit:100}).filter(r=>!r.deleted),pick=sel("",[["","Choose a fact"],...records.map(r=>[r.id,r.text.slice(0,100)])],()=>{});
 b.append(panel(h("b",{text:"Share selected lore as fanon"}),h("p",{text:"Author action: do not share private character knowledge or secrets."}),pick,button("Promote selected fact",()=>{const r=records.find(x=>x.id===pick.value);if(r&&confirm("Share this fact across the universe?"))apply(()=>ffPromote(se,r,{canon:"fanon"}))})));
 const fanon=(u.records||[]).filter(r=>r.canon==="fanon");b.append(h("h3",{text:"Shared fanon"}),...fanon.slice(0,100).map(r=>panel(h("p",{text:r.text}),button("Remove shared fanon",()=>{if(confirm("Remove this shared fanon record?"))apply(()=>ffDemote(u.id,r.id))}))));
 const ids=(se.canon.universes||[]).map(x=>x.id);if(!ids.includes(u.id))ids.unshift(u.id);
 const combined=ffCrossover(ids);b.append(panel(h("b",{text:"Crossover inspection"}),h("p",{text:ids.join(" · ")}),...ids.flatMap(a=>ids.filter(c=>c!==a).map(c=>panel(h("b",{text:a+" → "+c}),dump(ffPowerRule(se,a,c))))),h("details",{},h("summary",{text:"Combined world rules"}),dump(combined?.rules||{}))));
 const chars=Object.entries(combined?.chars||u.chars||{}),cp=sel("",[["","Choose character"],...chars.map(([id,c])=>[id,c.name||id])],()=>{knowledge.replaceChildren(dump(cp.value?ffKnowsX(se,cp.value):[]))}),knowledge=h("div",{});
 b.append(panel(h("b",{text:"Character knowledge (author view)"}),cp,knowledge));
})}
Object.assign(window.SFFanUI,{universe,studioShell:studio});
})();

(function(){
"use strict";
const button=(text,onclick)=>h("button",{text,onclick}), dump=x=>sfStudioReadable(x), panel=(...kids)=>h("div",{class:"ff-panel"},...kids), field=(v="",type="text")=>{const e=h("input",{type});e.value=v;return e};
function gameplay(se){window.SFFanUI.studioShell(se,"Gameplay Studio",(b,apply)=>{
 const g=gmState(se),num=e=>Number(e.value),id=field(),name=field(),min=field(0,"number"),max=field(100,"number"),start=field(0,"number"),hidden=h("input",{type:"checkbox"});
 b.append(chk("Enable gameplay",g.enabled,v=>apply(()=>gmEnable(se,v))),h("p",{text:"Level "+g.level+" · XP "+g.xp+" · Day "+g.day}),button("Undo last gameplay change",()=>apply(()=>gmUndo(se))));
 const xp=field(10,"number"),base=field(g.curve?.base??100,"number"),growth=field(g.curve?.growth??1.5,"number"),cap=field(g.curve?.max??50,"number");
 b.append(panel(h("b",{text:"Progression"}),fld("XP change",xp),button("Apply XP",()=>apply(()=>gmXp(se,num(xp),"Player adjustment"))),fld("Base XP",base),fld("Growth",growth),fld("Maximum level",cap),button("Save curve",()=>apply(()=>gmSet(se,{curve:{base:num(base),growth:num(growth),max:num(cap)}})))));
 b.append(h("h3",{text:"Stats"}),...Object.entries(g.stats||{}).map(([key,s])=>{const delta=field(1,"number");return panel(h("b",{text:s.name||key}),dump(s),fld("Change",delta),button("Apply change",()=>apply(()=>gmChange(se,key,num(delta),"Player adjustment"))))}),panel(h("b",{text:"Define stat"}),fld("ID",id),fld("Name",name),fld("Minimum",min),fld("Maximum",max),fld("Starting value",start),h("label",{},hidden," Hidden from narrator"),button("Add stat",()=>apply(()=>gmDefineStat(se,{id:id.value.trim(),name:name.value.trim(),min:num(min),max:num(max),start:num(start),hidden:hidden.checked})))));
 const qi=field(),qt=field(),steps=h("textarea",{rows:3}),reward=field(0,"number");
 b.append(h("h3",{text:"Quests"}),...g.quests.map(q=>panel(h("b",{text:q.title}),dump(q),button("Advance",()=>apply(()=>gmAdvanceQuest(se,q.id))),button("Fail quest",()=>{if(confirm("Mark quest failed?"))apply(()=>gmFailQuest(se,q.id,"Player decision"))}))),panel(fld("Quest ID",qi),fld("Title",qt),fld("Objectives (one per line)",steps),fld("XP reward",reward),button("Add quest",()=>apply(()=>gmAddQuest(se,{id:qi.value.trim(),title:qt.value.trim(),steps:steps.value.split("\n").map(x=>x.trim()).filter(Boolean),reward:{xp:num(reward)}})))));
 const ri=field(),stat=sel("level",["level","day",...Object.keys(g.stats||{})].map(x=>[x,x]),()=>{}),op=sel(">=",["<","<=",">",">=","=="].map(x=>[x,x]),()=>{}),threshold=field(1,"number"),effect=h("textarea",{rows:3}),note=field(),repeat=h("input",{type:"checkbox"});effect.value="{}";
 b.append(h("h3",{text:"Consequence rules"}),dump(g.rules),panel(fld("Rule ID",ri),fld("Condition",stat),op,threshold,fld("Effect JSON (stats, fail, unlock)",effect),fld("Note",note),h("label",{},repeat," Repeat when re-armed"),button("Add rule",()=>apply(()=>gmAddRule(se,{id:ri.value.trim(),when:{stat:stat.value,op:op.value,value:num(threshold)},effect:JSON.parse(effect.value),note:note.value,repeat:repeat.checked})))));
 const careers=gmCareers(),custom=h("textarea",{rows:6});b.append(h("h3",{text:"Careers"}),dump(g.career));
 if(!g.career)b.append(...careers.map(c=>panel(h("b",{text:c.name}),button("Start career",()=>apply(()=>gmStartCareer(se,c.id,{}))))),panel(fld("Custom career module JSON",custom),button("Start custom career",()=>apply(()=>{const c=JSON.parse(custom.value);return gmStartCareer(se,c.id,{custom:c})}))));
 else {const c=careers.find(x=>x.id===g.career.id)||careers.find(x=>x.id===g.career.module?.id);const acts=c?.activities||Object.entries(g.career.module?.activities||{}).map(([id,a])=>({id,...a}));b.append(...acts.map(a=>button(a.name+(a.needRank?" · requires "+a.needRank:""),()=>{if(confirm("Advance one career week?"))apply(()=>gmActivity(se,a.id))})))}
 b.append(h("h3",{text:"Gameplay history"}),dump(gmLog(se,50)));
})}
Object.assign(window.SFFanUI,{gameplay});
})();

(function(){
"use strict";
const button=(text,onclick)=>h("button",{text,onclick}),dump=x=>sfStudioReadable(x),panel=(...kids)=>h("div",{class:"ff-panel"},...kids);
function creator(se){
 const st=getStory(se.storyId),body=h("div",{class:"ff-ui"}),status=h("p",{role:"status","aria-live":"polite"}),report=h("div",{}),importReport=h("div",{}),name=h("input",{}),note=h("textarea",{rows:3}),art=h("input",{type:"checkbox",disabled:!!st?.ooc}),templates=sfTemplates().map(t=>({name:t.name,box:h("input",{type:"checkbox"})}));
 let pending=null,epoch=0;
 function options(){return {sessionId:se.id,templates:templates.filter(t=>t.box.checked).map(t=>t.name),art:art.checked&&!st?.ooc,creator:{name:name.value,note:note.value}}}
 function run(download){try{const r=download?crDownload(se.storyId,options()):crBuild(se.storyId,options());status.textContent=r.ok?(download?"Package prepared for download":"Preview ready"):r.reason||"Export failed";report.replaceChildren(dump({size:r.size,artBlocked:r.artBlocked,removed:r.removed,preview:r.ok?crPreview(r.package):null}))}catch(e){status.textContent=String(e.message||e)}}
 const file=h("input",{type:"file",accept:".json,.sfcreator.json"}),openButton=button("Create new story from package",()=>{if(!pending||!confirm("Create a new story from this blueprint?"))return;try{const r=crOpen(pending);status.textContent=r.applied?"New story created: "+r.storyId:r.reason||"No change";if(r.applied){pending=null;openButton.disabled=true}importReport.append(dump(r))}catch(e){status.textContent=String(e.message||e)}});openButton.disabled=true;
 file.addEventListener("change",()=>{epoch++;pending=null;openButton.disabled=true;importReport.replaceChildren()});
 const preview=button("Preview import",async()=>{const ticket=++epoch;pending=null;openButton.disabled=true;importReport.replaceChildren();try{const f=file.files[0];if(!f)throw Error("Choose a package first");if(f.size>8*1024*1024)throw Error("Package exceeds 8 MB");const p=JSON.parse(await f.text());if(ticket!==epoch||!body.isConnected)return;const r=crPreview(p);importReport.append(dump(r));if(r.ok){pending=p;openButton.disabled=false}status.textContent=r.ok?"Validated. Nothing imported yet.":"Package validation failed"}catch(e){if(ticket===epoch)status.textContent=String(e.message||e)}});
 body.append(status,panel(h("h3",{text:"Export reusable blueprint"}),h("p",{text:"Excludes playthroughs, memories, credentials and gameplay progress."}),fld("Creator name",name),fld("Creator notes",note),h("label",{},art," Include images"),st?.ooc?h("p",{text:"Images cannot be exported from OOC-imported stories."}):null,h("b",{text:"Character templates"}),...templates.map(t=>h("label",{},t.box," "+t.name)),button("Preview export",()=>run(false)),button("Download package",()=>run(true)),report),panel(h("h3",{text:"Import creator package"}),file,preview,importReport,openButton));sheet("Creator Studio",body);
}
Object.assign(window.SFFanUI,{creator});
})();

(function(){
"use strict";
const btn=(text,onclick)=>h("button",{text,onclick}),panel=(...kids)=>h("div",{class:"ff-panel"},...kids);
function cinema(se){window.SFFanUI.studioShell(se,"Cinematic / Visual Novel",(b,apply)=>{
 const v=cvState(se),s=v.settings,scene=cvScene(se),cast=cvCast(se);
 const choose=(key,values)=>fld(key,sel(s[key],values.map(x=>typeof x==="string"?[x,x]:[x.id,x.name]),x=>apply(()=>cvSet(se,{[key]:x}))));
 const number=(key,min,max)=>fld(key,h("input",{type:"number",min,max,value:s[key],onchange:e=>apply(()=>cvSet(se,{[key]:Number(e.target.value)}))}));
 const toggle=k=>chk(k,!!s[k],x=>apply(()=>cvSet(se,{[k]:x})));
 b.append(panel(h("h3",{text:"Reader presentation"}),choose("layout",cvLayouts()),...["nameplate","autoAdvance","fullscreen","hideUI","reducedMotion"].map(toggle),choose("dialogueBox",["classic","minimal","parchment","glass","comic","terminal"]),choose("narration",["plain","italic","boxed","centered"]),choose("textReveal",["instant","typewriter","fade-in"]),number("revealSpeed",5,120),number("autoDelay",1,30)));
 b.append(panel(h("h3",{text:"Scene presets"}),...cvPresets().map(p=>btn(p.name,()=>apply(()=>cvApplyPreset(se,p.id))))));
 const lighting=["neutral","dawn","day","dusk","night","candle","storm","neon","underwater"],overlay=["none","rain","snow","fog","embers","petals","film-grain","vignette","scanlines"],transition=["none","fade","dissolve","slide","wipe","flash"];
 const bg=h("input",{value:scene.background||"",placeholder:"Artwork reference"}),caption=h("textarea",{value:scene.caption||"",rows:2});
 const url=cvArt(se,scene.background);
 b.append(panel(h("h3",{text:"Scene artwork"}),url?h("img",{src:url,alt:"Current scene",style:"width:100%;max-height:220px;object-fit:contain"}):null,fld("Background reference",bg),fld("Caption",caption),btn("Save scene artwork",()=>apply(()=>cvSetScene(se,{background:bg.value||null,caption:caption.value}))),...Object.entries({lighting,overlay,transition}).map(([k,values])=>fld(k,sel(scene[k]||s[k],values.map(x=>[x,x]),x=>apply(()=>cvSetScene(se,{[k]:x})))))));
 b.append(h("h3",{text:"Cast presentation"}),...Object.entries(cast||{}).map(([name,c])=>{
 const n=c.name||name,ref=c.portrait||"cast:"+n,src=cvArt(se,ref),portrait=h("input",{value:ref}),scale=h("input",{type:"number",min:0.5,max:1.5,step:0.1,value:c.scale??1});
 return panel(h("b",{text:n}),src?h("img",{src,alt:n,style:"width:96px;height:120px;object-fit:contain"}):null,chk("Visible",c.visible!==false,x=>apply(()=>cvSetCharacter(se,n,{visible:x}))),fld("Expression",sel(c.expression||"neutral",["neutral","happy","sad","angry","surprised","afraid","thoughtful","smug","tired","determined"].map(x=>[x,x]),x=>apply(()=>cvSetCharacter(se,n,{expression:x})))),fld("Position",sel(c.position||"center",["far-left","left","center","right","far-right","offscreen"].map(x=>[x,x]),x=>apply(()=>cvSetCharacter(se,n,{position:x})))),fld("Scale",scale),fld("Portrait reference",portrait),btn("Save portrait and scale",()=>apply(()=>cvSetCharacter(se,n,{portrait:portrait.value,scale:Number(scale.value)}))));
 }));
 b.append(btn("Reset presentation only",()=>{if(confirm("Reset cinematic presentation? Story content is unchanged."))apply(()=>cvReset(se))}));
})}
Object.assign(window.SFFanUI,{cinema});
})();

(function(){
"use strict";
const btn=(text,onclick)=>h("button",{text,onclick}),panel=(...kids)=>h("div",{class:"ff-panel"},...kids);
function appearance(se){
 let scope="story",device=matchMedia("(max-width: 700px)").matches?"mobile":"desktop";
 window.SFFanUI.studioShell(se,"Appearance & Customization",(b,apply)=>{
 const s=apState(se,device),set=(k,v)=>apply(()=>apSet(se,{[k]:v},scope));
 const opts=xs=>xs.map(x=>typeof x==="string"?[x,x]:Array.isArray(x)?x:[x.id,x.name]);
 const choose=(k,xs)=>fld(k,sel(s[k],opts(xs),v=>set(k,v)));
 const field=(k,type="text",min,max,step)=>fld(k,h("input",{type,min,max,step,value:s[k]??"",onchange:e=>set(k,type==="number"?Number(e.target.value):e.target.value||null)}));
 const scopePick=sel(scope,opts(["global","story","mobile","desktop"]),v=>{scope=v;device=v==="mobile"||v==="desktop"?v:device;render()});
 function render(){b.replaceChildren();build()}
 function build(){
 const current=apState(se,device);
 b.append(panel(h("b",{text:"Editing scope"}),scopePick,h("p",{text:"Effective preview: "+device+". Device overrides take precedence over story and global settings."}),btn("Reset selected scope",()=>{if(confirm("Reset appearance for "+scope+"?"))apply(()=>apReset(se,scope))})));
 b.append(panel(h("h3",{text:"Themes"}),...apThemes().map(t=>h("button",{onclick:()=>set("theme",t.id),style:"display:flex;align-items:center;gap:8px;flex-wrap:wrap"},t.name,...(t.palette||[]).map(c=>h("span",{style:"display:inline-block;width:20px;height:20px;border:1px solid currentColor;border-radius:4px;background:"+c}))))));
 b.append(panel(h("h3",{text:"Layout and typography"}),choose("layout",apLayouts()),choose("format",apFormats()),choose("nav",["bottom","top","side","floating"]),choose("panel",["right","left","bottom","overlay"]),field("font"),field("fontScale","number",0.8,1.4,0.05),choose("spacing",["compact","cozy","roomy"]),choose("borders",["none","thin","bold"]),field("radius","number",0,24,1),field("transparency","number",0,0.6,0.05),...["bg","card","accent","text"].map(k=>field(k)),field("background"),choose("motion",["none","subtle","full"]),choose("contrast",["normal","high"]),chk("Reduced motion",!!current.reducedMotion,v=>set("reducedMotion",v))));
 b.append(panel(h("h3",{text:"Icon design families"}),...apIcons().map(i=>btn(i.name,()=>set("icons",i.id)))));
 const name=h("input",{placeholder:"Preset name"}),file=h("input",{type:"file",accept:".json"}),report=h("pre",{}),confirmImport=btn("Save imported preset",()=>{if(pending){const p=pending;pending=null;apply(()=>apImport(p))}});let pending=null;confirmImport.disabled=true;
 file.addEventListener("change",()=>{pending=null;confirmImport.disabled=true;report.textContent=""});
 b.append(panel(h("h3",{text:"Custom presets"}),name,btn("Save effective appearance",()=>apply(()=>apSavePreset(name.value,apState(se,device)))),...apPresets().map(p=>panel(h("b",{text:p.name}),btn("Apply to "+scope,()=>apply(()=>apApplyPreset(se,p.id,scope))),btn("Export",()=>{const data=apExportPreset(p.id);if(!data)return;const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"}));const a=h("a",{href:url,download:"story-forge-appearance.json"});document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}),btn("Delete preset",()=>{if(confirm("Delete this appearance preset?"))apply(()=>apDeletePreset(p.id))}))),file,btn("Preview import",async()=>{pending=null;confirmImport.disabled=true;try{const f=file.files[0];if(!f||f.size>1024*1024)throw Error("Choose a JSON preset under 1 MB");const data=JSON.parse(await f.text());if(file.files[0]!==f||!b.isConnected)return;const r=apImportPreview(data);report.textContent=JSON.stringify(r,null,2);if(r.ok){pending=data;confirmImport.disabled=false}}catch(e){report.textContent=String(e.message||e)}}),report,confirmImport));
 }
 build();
 });
}
Object.assign(window.SFFanUI,{appearance});
})();

(function(){
"use strict";
const btn=(text,onclick)=>h("button",{text,onclick}),panel=(...kids)=>h("div",{class:"ff-panel"},...kids),opts=a=>a.map(x=>[x,x]);
const labels={oc:"Original character",self:"Self-insert",takeover:"Canon takeover",transmigration:"Transmigration",reincarnation:"Reincarnation",regression:"Regression",fixit:"Fix-it",whatif:"What if",divergence:"Canon divergence",au:"Alternate universe",crossover:"Crossover",rolereversal:"Role reversal",parallel:"Parallel story",nextgen:"Next generation",prequel:"Prequel",sequel:"Sequel",missing:"Missing scene",slice:"Slice of life",ensemble:"Ensemble",altending:"Alternate ending"};
function createFanfiction(root,initialUniverse="",initialDraft=""){
 let step=0,uid=initialUniverse,modes=["oc"],takeover="",name="",desc="",title="",setting="",ch=0,age="",pov="second",pref="any",pacing="natural",rules={},others=[],link="merged",powers={},pending=null,controller=null,epoch=0,created=false,locks=[],exceptions=[],fates={},foreknowledge=[],draftId=null,draftName="";
 const body=h("div",{class:"ff-ui ff-create"}),status=h("p",{role:"status","aria-live":"polite"}),content=h("div",{class:"ff-ui ff-create-content"}),steps=["Universe","Scenario","Character","Timeline & narration","Canon rules","Crossover","Review"];
 const config=()=>({modes:[...modes],start:{ch},takeover:takeover||undefined,player:{name,desc},startAge:age===""?null:Number(age),pov:{mode:pov},romance:{pref,pacing},rules:{...rules},crossover:{with:others,link,powers:others.flatMap(id=>[[uid,id],[id,uid]].map(([from,to])=>({from,to,rule:powers[from+"|"+to]||"separate"})))},title,setting,locks,exceptions,fates,foreknowledge});
 const input=(label,value,change,type="text")=>fld(label,h("input",{type,value,oninput:e=>change(e.target.value)}));
 const area=(label,value,change)=>fld(label,h("textarea",{rows:3,value,oninput:e=>change(e.target.value)}));
 const select=(label,value,options,change)=>fld(label,sel(value,options,change));
 function draw(){content.replaceChildren();status.textContent="";content.append(h("div",{class:"ff-step-head"},h("small",{text:"NEW FANFICTION · "+(step+1)+" / "+steps.length}),h("h2",{text:steps[step]}),h("div",{class:"ff-progress",role:"progressbar","aria-valuenow":step+1,"aria-valuemin":1,"aria-valuemax":steps.length},...steps.map((x,i)=>h("span",{class:i<=step?"done":"",title:x})))));
 const list=ffListUniverses(),u=uid?ffUniverse(uid):null;
 const summary=h("aside",{class:"ff-live-summary"},h("small",{text:"STORY CONFIGURATION"}),h("strong",{text:u?.name||"Choose a universe"}),h("p",{text:modes.map(m=>labels[m]||m).join(" · ")}),h("p",{text:(name||"Player character")+" · Chapter "+ch}),h("p",{text:locks.length+" locks · "+exceptions.length+" exceptions"}));content.append(summary);
 const chars=Object.entries(u?.chars||{}),events=u?.events||[],records=u?.records||[];
 const resetTargets=()=>{locks=[];exceptions=[];fates={};foreknowledge=[]};
 const drafts=ffDrafts(),dp=sel(initialDraft,[["","Choose saved draft"],...drafts.map(d=>[d.id,d.name])],()=>{});
 content.append(h("details",{},h("summary",{text:"Saved drafts and reusable setups"}),input("Draft name",draftName,v=>draftName=v),btn("Save draft",()=>{const r=ffSaveDraft({id:draftId||undefined,name:draftName||title||"Fanfiction draft",universe:uid,options:config()});if(r.applied){draftId=r.id;draw();status.textContent="Draft saved."}else status.textContent=r.reason}),dp,btn("Resume draft",()=>{const d=ffLoadDraft(dp.value);if(!d||!d.options)return;if(!confirm("Replace the current wizard setup with this draft?"))return;epoch++;controller?.abort();pending=null;const o=d.options;draftId=d.id||dp.value;draftName=d.name;uid=d.universe;modes=o.modes||["oc"];takeover=o.takeover||"";name=o.player?.name||"";desc=o.player?.desc||"";title=o.title||"";setting=o.setting||"";ch=o.start?.ch||0;age=o.startAge??"";pov=o.pov?.mode||"second";pref=o.romance?.pref||"any";pacing=o.romance?.pacing||"natural";rules=o.rules||{};others=o.crossover?.with||[];link=o.crossover?.link||"merged";powers=Object.fromEntries((o.crossover?.powers||[]).map(p=>[p.from+"|"+p.to,p.rule]));locks=o.locks||[];exceptions=o.exceptions||[];fates=o.fates||{};foreknowledge=o.foreknowledge||[];step=0;draw()}),btn("Delete saved draft",()=>{if(dp.value&&confirm("Delete this saved draft? Created stories are unaffected.")){const r=ffDeleteDraft(dp.value);if(r.applied){if(draftId===dp.value)draftId=null;draw()}else status.textContent=r.reason}})));
 if(step===0){
 content.append(select("Source universe",uid,[["","Choose a universe"],...list.map(x=>[x.id,x.name])],v=>{uid=v;takeover="";resetTargets();others=others.filter(x=>x!==v);pending=null;draw()}));
 const file=h("input",{type:"file",accept:".epub,.txt,.md"}),sourceTitle=h("input",{placeholder:"Optional source title"}),kind=sel("novel",opts(["novel","manga","anime","wiki","notes"]),()=>{}),report=h("div",{}),saveImport=btn("Confirm source import",()=>{if(!pending)return;try{const r=pending.commit();if(!(r.applied??r.ok)){status.textContent=r.reason||"Import refused";return}uid=pending.preview.universe;takeover="";resetTargets();pending=null;draw()}catch(e){status.textContent=e.message}});saveImport.disabled=true;
 const invalidate=()=>{epoch++;controller?.abort();pending=null;saveImport.disabled=true;report.replaceChildren()};for(const e of [file,sourceTitle,kind])e.addEventListener("change",invalidate);
 content.append(panel(h("h3",{text:"Import a source"}),h("p",{text:"Index a source you have permission to use. Review before saving it to your library."}),file,sourceTitle,kind,btn("Preview import",async()=>{invalidate();const token=epoch;controller=new AbortController();try{if(!file.files[0])throw Error("Choose a source file");const r=await ffImportPreview(file.files[0],{title:sourceTitle.value,kind:kind.value,signal:controller.signal,onProgress:p=>{if(token===epoch)status.textContent="Indexing source…"}});if(token!==epoch||!body.isConnected)return;if(!r.ok){status.textContent=r.reason;return}pending=r;report.append(h("p",{text:"Revision "+r.preview.rev+" · Added: "+JSON.stringify(r.preview.added)+" · Duplicates: "+JSON.stringify(r.preview.duplicate)}),h("p",{text:"Conflicts: "+(r.preview.conflicts||[]).length}),h("p",{text:"Characters: "+(r.preview.names||[]).join(", ")}));saveImport.disabled=false;status.textContent="Review ready; nothing imported yet."}catch(e){if(token===epoch)status.textContent=e.message}}),btn("Cancel import",invalidate),report,saveImport));
 }else if(step===1){content.append(h("p",{text:"Combine scenario types to define your story."}),h("div",{class:"ff-mode-grid"},...ffModes().map((m,i)=>h("button",{class:"ff-mode-card","aria-pressed":String(modes.includes(m)),onclick:()=>{modes=modes.includes(m)?modes.filter(x=>x!==m):[...modes,m];rules={};draw()}},h("span",{class:"ff-mode-symbol",text:["✧","◇","◈","↻","☾","✦"][i%6]}),h("strong",{text:labels[m]||m}),h("small",{text:modes.includes(m)?"Selected":"Select"})))));
 }else if(step===2){content.append(select("Canon character (if applicable)",takeover,[["","Original character"],...Object.entries(u?.chars||{}).map(([id,c])=>[id,c.name||id])],v=>{takeover=v}),input("Player character name",name,v=>name=v),area("Origin, identity and background",desc,v=>desc=v),input("Starting age (optional)",age,v=>age=v,"number"),h("p",{class:"sub",text:"Takeover, transmigration and regression require a canon character. Leave name blank to inherit that character’s name."}));
 }else if(step===3){content.append(input("Starting source chapter (0 = beginning)",ch,v=>ch=Number(v),"number"),h("details",{},h("summary",{text:"Browse canon timeline"}),...events.slice(0,150).map(e=>h("button",{class:"ff-timeline-event",text:"Chapter "+e.ch+" · "+e.title,onclick:()=>{ch=Number(e.ch)||0;draw()}}))),select("Point of view",pov,[["first","First person"],["second","Second person"],["thirdLimited","Third person limited"],["omniscient","Omniscient"],["multi","Multiple POVs"]],v=>pov=v),select("Romance preference (fictional characters only)",pref,[["any","Any"],["none","None"],["bl","BL"],["gl","GL"],["straight","Straight"]],v=>pref=v),select("Romance pacing",pacing,opts(["slow","natural","fast"]),v=>pacing=v));
 }else if(step===4){const defaults=ffDefaults(modes);content.append(h("p",{text:"Locked preserves canon; adaptive allows justified changes; free permits divergence."}),h("div",{class:"row"},...["locked","adaptive","free"].map(v=>btn("All "+v,()=>{rules=Object.fromEntries(Object.keys(defaults).map(k=>[k,v]));draw()})),btn("Mode defaults",()=>{rules={};draw()})),...Object.keys(defaults).map(k=>select(k.replace(/([A-Z])/g," $1"),rules[k]||defaults[k],opts(["locked","adaptive","free"]),v=>rules[k]=v)));
 const lockList=h("div",{}),lockKind=sel("event",opts(["event","char"]),()=>drawLock()),lockTarget=h("div",{});function drawLock(){const k=lockKind.value,choices=k==="event"?events.map(e=>[e.id,e.title]):chars.map(([id,c])=>[id,c.name||id]),p=sel("",[["","Choose target"],...choices],()=>{});lockTarget.replaceChildren(p,btn("Add lock",()=>{if(p.value&&!locks.some(l=>l.kind===k&&l.id===p.value)){locks.push({kind:k,id:p.value});showLocks()}}))}function showLocks(){lockList.replaceChildren(...locks.map(l=>panel(h("p",{text:l.kind+" · "+(l.kind==="event"?events.find(e=>e.id===l.id)?.title:u?.chars?.[l.id]?.name||l.id)}),btn("Remove lock",()=>{locks=locks.filter(x=>x!==l);showLocks()}))))}drawLock();showLocks();
 const ep=sel("",[["","Choose event"],...events.map(e=>[e.id,e.title])],()=>{}),et=h("textarea",{rows:3}),exList=h("div",{});function showEx(){exList.replaceChildren(...exceptions.map(e=>panel(h("p",{text:(events.find(x=>x.id===e.target)?.title||e.target)+": "+e.text}),btn("Remove exception",()=>{exceptions=exceptions.filter(x=>x!==e);showEx()}))))}showEx();
 const fp=sel("",[["","Choose character"],...chars.map(([id,c])=>[id,c.name||id])],()=>{}),fv=sel("protected",opts(["preserve","adapt","protected","free"]),()=>{}),fl=h("div",{});function showFates(){fl.replaceChildren(...Object.entries(fates).map(([id,v])=>panel(h("p",{text:(u?.chars?.[id]?.name||id)+": "+v}),btn("Remove fate rule",()=>{delete fates[id];showFates()}))))}showFates();
 const known=sel("",[["","Choose event or fact"],...events.map(e=>[e.id,e.title]),...records.map(r=>[r.id,String(r.text||r.id).slice(0,120)])],()=>{}),kl=h("div",{});function showKnown(){kl.replaceChildren(...foreknowledge.map(id=>panel(h("p",{text:events.find(e=>e.id===id)?.title||records.find(r=>r.id===id)?.text||id}),btn("Remove foreknowledge",()=>{foreknowledge=foreknowledge.filter(x=>x!==id);showKnown()}))))}showKnown();
 content.append(h("details",{},h("summary",{text:"Individual canon locks"}),lockKind,lockTarget,lockList),h("details",{},h("summary",{text:"Approved exceptions"}),ep,fld("Intentional change",et),btn("Approve exception",()=>{if(ep.value&&et.value.trim()){exceptions.push({target:ep.value,text:et.value.trim()});et.value="";showEx()}}),exList),h("details",{},h("summary",{text:"Character fate protections"}),fp,fv,btn("Set fate rule",()=>{if(fp.value){fates[fp.value]=fv.value;showFates()}}),fl),h("details",{},h("summary",{text:"Player foreknowledge"}),h("p",{text:"Author-selected knowledge may include future spoilers."}),known,btn("Grant selected knowledge",()=>{if(known.value&&!foreknowledge.includes(known.value)){foreknowledge.push(known.value);showKnown()}}),kl));
 }else if(step===5){content.append(h("p",{text:"Optional: connect additional source universes."}),...list.filter(x=>x.id!==uid).map(x=>chk(x.name,others.includes(x.id),v=>{others=v?[...new Set([...others,x.id])]:others.filter(id=>id!==x.id);draw()})),select("Universe connection",link,opts(["merged","portal","reincarnation","parallel"]),v=>link=v),...others.flatMap(id=>[[uid,id],[id,uid]].map(([from,to])=>select((ffUniverse(from)?.name||from)+" → "+(ffUniverse(to)?.name||to),powers[from+"|"+to]||"separate",opts(["separate","translated","hybrid","custom"]),v=>powers[from+"|"+to]=v))));
 }else{content.append(input("Story title",title,v=>title=v),area("Story setting and opening premise",setting,v=>setting=v));const r=ffNewCanonPreview(uid,config());if(!r.ok)content.append(h("p",{text:r.reason}));else{const x=r.summary;content.append(panel(h("b",{text:x.universe}),h("p",{text:"Modes: "+x.modes.map(m=>labels[m]||m).join(", ")}),h("p",{text:"Player: "+x.player+" · Chapter "+x.start+" · POV: "+x.pov}),h("p",{text:"Locked rules: "+x.locked.join(", ")}),h("p",{text:"Individual locks: "+locks.length+" · Exceptions: "+exceptions.length+" · Fate rules: "+Object.keys(fates).length+" · Foreknowledge: "+foreknowledge.length}),h("p",{text:"Each playthrough receives an independent canon copy."})),btn("Create fanfiction",()=>{if(created)return;const v=ffNewCanonPreview(uid,config());if(!v.ok){status.textContent=v.reason;return}if(!confirm("Create this story with the reviewed canon rules?"))return;const result=ffCreateStory(uid,config());if(!result.applied){status.textContent=result.reason||"Creation refused";return}created=true;go({n:"story",id:result.storyId})}))}}
 content.append(h("div",{class:"ff-wizard-nav"},step?btn("Back",()=>{step--;draw()}):null,step<6?btn("Next",()=>{if(step===0&&!uid){status.textContent="Choose or import a universe first.";return}if(step===1&&!modes.length){status.textContent="Choose at least one mode.";return}if(step===2&&(!name.trim()&&!takeover||modes.some(m=>["takeover","transmigration","regression"].includes(m))&&!takeover)){status.textContent="Complete the character identity first.";return}if(step===3&&(!Number.isFinite(ch)||ch<0||!Number.isInteger(ch))){status.textContent="Enter a nonnegative whole chapter number.";return}epoch++;controller?.abort();pending=null;step++;draw()}):null));
 }
 body.append(status,content);root.append(body);draw();
}
Object.assign(window.SFFanUI,{createFanfiction});
})();

(function(){
"use strict";
function fanfictionHome(root){
 const el=(tag,attrs,...kids)=>h(tag,attrs,...kids),button=(text,onclick)=>h("button",{text,onclick});
 let section="home";
 function wizard(uid="",draft=""){root.replaceChildren();root.append(h("button",{class:"ff-back",text:"‹ Fanfiction Studio",onclick:()=>{if(confirm("Return to Studio? Save your draft first to retain unfinished changes."))draw("home")}}));window.SFFanUI.createFanfiction(root,uid,draft)}
 function universePage(id){
 const u=ffUniverse(id);if(!u){draw("home");return}
 root.replaceChildren();const wrap=h("div",{class:"ff-dashboard"});root.append(wrap);
 const chars=Object.values(u.chars||{}),events=u.events||[],sources=u.sources||[],stories=DB.stories.filter(st=>st.fanfic?.universe===id);
 wrap.append(button("‹ Your universes",()=>draw("universes")),h("section",{class:"ff-hero"},h("small",{text:"UNIVERSE LIBRARY"}),h("h2",{text:u.name}),h("p",{text:sources.length+" sources · "+chars.length+" characters · "+events.length+" events"}),h("button",{class:"ff-primary",text:"Create fanfiction",onclick:()=>wizard(id)})));
 const results=h("div",{class:"ff-ui"}),search=h("input",{placeholder:"Search this section",type:"search","aria-label":"Search universe"});let selected=0;
 const sections=[["Sources",sources.map(x=>({title:x.title,detail:(x.kind||"Source")+" · "+(x.chapters||[]).length+" chapters"}))],["Characters",chars.map(x=>({title:x.name,detail:[x.appearance,x.personality].filter(v=>typeof v==="string").join(" · ")}))],["Timeline",events.map(x=>({title:x.title,detail:"Chapter "+x.ch+" · "+(x.summary||"")}))],["Canon records",(u.records||[]).map(x=>({title:x.kind||"Fact",detail:x.text||""}))],["Playthroughs",stories.map(x=>({title:x.title,detail:"Open story",action:()=>go({n:"story",id:x.id})}))]];
 function refresh(){const q=search.value.toLowerCase();const rows=sections[selected][1].filter(x=>(x.title+" "+x.detail).toLowerCase().includes(q));results.replaceChildren(h("h3",{text:sections[selected][0]+" · "+rows.length}),...rows.slice(0,100).map(x=>h(x.action?"button":"article",{class:"ff-panel",onclick:x.action||null},h("strong",{text:x.title}),h("p",{text:x.detail}))),rows.length>100?h("p",{text:"Showing first 100 results. Search to narrow the list."}):null)}
 const tiles=h("div",{class:"ff-dashboard-grid"},...sections.map(([label,rows],i)=>h("button",{class:"ff-dashboard-tile","aria-pressed":i===0,onclick:()=>{selected=i;for(const [n,b] of Array.from(tiles.children).entries())b.setAttribute("aria-pressed",String(n===i));refresh()}},h("strong",{text:label}),h("small",{text:String(rows.length)}))));
 search.addEventListener("input",refresh);wrap.append(tiles,search,results);refresh()
 }
 function draw(tab){section=tab;root.replaceChildren();const list=ffListUniverses(),drafts=ffDrafts(),stories=DB.stories.filter(s=>s.fanfic);
 const wrap=h("div",{class:"ff-dashboard"});root.append(wrap);
 const hero=h("section",{class:"ff-hero"},h("div",{class:"ff-hero-art","aria-hidden":"true"},h("span",{text:"✧"}),h("span",{text:"◇"}),h("span",{text:"✦"})),h("small",{text:"FANFICTION STUDIO"}),h("h2",{text:"Rewrite destiny."}),h("p",{text:"Enter familiar worlds. Create your own path."}),h("button",{class:"ff-primary",text:"+ Create fanfiction",onclick:()=>wizard()}));wrap.append(hero);
 const tiles=[["universes","◈","Universes",list.length],["stories","▤","My fanfiction",stories.length],["drafts","✎","Saved drafts",drafts.length],["templates","▱","Templates",drafts.length]];
 wrap.append(h("div",{class:"ff-dashboard-grid"},...tiles.map(([id,icon,label,count])=>h("button",{class:"ff-dashboard-tile","aria-pressed":String(tab===id),onclick:()=>draw(id)},h("span",{class:"ff-tile-icon",text:icon}),h("strong",{text:label}),h("small",{text:count+" saved"})))));
 const title=tab==="stories"?"My fanfiction":tab==="drafts"?"Saved drafts":tab==="templates"?"Reusable setups":"Your universes";
 wrap.append(h("div",{class:"ff-section-head"},h("h3",{text:title}),tab!=="home"?button("Overview",()=>draw("home")):null));
 if(tab==="stories"){wrap.append(...stories.map(st=>h("button",{class:"ff-universe-card",onclick:()=>go({n:"story",id:st.id})},h("span",{class:"ff-cover",text:"▤"}),h("div",{},h("strong",{text:st.title}),h("small",{text:ffUniverse(st.fanfic.universe)?.name||"Fanfiction"})),h("span",{text:"›"}))));if(!stories.length)wrap.append(h("p",{class:"sub",text:"No fanfiction stories yet."}))}
 else if(tab==="drafts"||tab==="templates"){wrap.append(h("p",{class:"sub",text:tab==="templates"?"Reuse a saved setup in the creation wizard.":"Continue a saved configuration."}),...drafts.map(d=>h("button",{class:"ff-universe-card",onclick:()=>wizard(d.universe||"",d.id)},h("span",{class:"ff-cover",text:"✎"}),h("div",{},h("strong",{text:d.name}),h("small",{text:"Select Resume draft in the wizard"})),h("span",{text:"›"}))));if(!drafts.length)wrap.append(h("p",{class:"sub",text:"No saved setups yet."}))}
 else{wrap.append(...list.map(u=>h("button",{class:"ff-universe-card",onclick:()=>universePage(u.id)},h("span",{class:"ff-cover",text:"✧"}),h("div",{},h("strong",{text:u.name}),h("small",{text:(u.chapters||0)+" chapters · "+(u.events||0)+" events"}),h("small",{text:"Explore universe and create stories"})),h("span",{text:"›"}))));wrap.append(button("+ Import a universe",()=>wizard()));if(!list.length)wrap.append(h("p",{class:"sub",text:"Import your first source to begin."}))}
 }
 draw("home");
}
Object.assign(window.SFFanUI,{fanfictionHome});
})();
