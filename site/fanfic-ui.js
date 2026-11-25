/* Fanfiction UI: source library. All writes go through adapters. */
(function(){
"use strict";
function library(se){
 const body=h("div",{class:"ff-ui"}), status=h("p",{class:"sub",role:"status","aria-live":"polite"}), preview=h("div",{}), list=h("div",{}); let pending=null, controller=null, epoch=0;
 const file=h("input",{type:"file",accept:".epub,.txt,.md,.json"}), title=h("input",{placeholder:"Optional source title"}), kind=sel("novel",["novel","manga","anime","wiki","notes"].map(x=>[x,x]),()=>{}), target=h("select",{});
 const run=h("button",{class:"primary",text:"Preview import",onclick:async()=>{
  if(!file.files[0]){status.textContent="Choose a source file first.";return}
  const ticket=++epoch;controller?.abort();controller=new AbortController();pending=null;preview.replaceChildren();run.disabled=true;status.textContent="Reading source…";
  try{
   const result=await ffImportPreview(file.files[0],{title:title.value.trim(),kind:kind.value,universeId:target.value||undefined,signal:controller.signal,onProgress:(i,n)=>{if(ticket===epoch)status.textContent="Indexing "+i+" / "+n}});
   if(ticket!==epoch||!body.isConnected)return;
   if(!result.ok){status.textContent=result.reason||"Import failed";return}
   pending=result;const p=result.preview;status.textContent="Preview ready. Nothing has been saved.";
   preview.append(h("div",{class:"ff-panel"},h("b",{text:"Revision "+p.rev}),h("p",{text:"Added: "+JSON.stringify(p.added)+" · Duplicates: "+JSON.stringify(p.duplicate)}),h("p",{text:"Conflicts: "+JSON.stringify(p.conflicts)}),h("p",{text:"Detected names: "+(p.names||[]).join(", ")}),h("details",{},h("summary",{text:"Index report"}),h("pre",{text:JSON.stringify(p.report,null,2)})),h("button",{class:"primary",text:"Confirm and save source",onclick:()=>{
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
const dump=x=>h("pre",{text:JSON.stringify(x,null,2)});
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
 b.append(panel(h("b",{text:"Event conflicts"}),dump(s.conflicts||[])),panel(h("b",{text:"Validation"}),dump(ffValidate(se))),panel(h("b",{text:"Reply warnings"}),...se.turns.flatMap((t,i)=>(t.ffc||[]).map(w=>h("p",{text:"Turn "+(i+1)+" · "+w.kind+": "+w.text}))).slice(-100)));
})}
Object.assign(window.SFFanUI,{studio,canon,timeline,inspector,romance,realworld,competition,continuity});
})();
