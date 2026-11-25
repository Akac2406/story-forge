/* Story Forge memory v2 — unified nine-layer view, player overlays and Studio queries (memory overhaul, contract 2).
 * Pure functions. Nothing here writes to stories: the app passes a plain "source" snapshot (see docs/MEMORY-API.md)
 * and stores the returned overlay ops in se.memEdits. The v1 store (se.mem, per-reply deltas) stays authoritative for
 * what the narrator recorded; v2 adds layers, provenance, and player edits that survive regeneration.
 */
(function(root){
'use strict';
const LAYERS=['permanent','working','episodic','semantic','character','relationship','temporal','world','universe'];
const TRUST={player:5,canon:4,narrator:3,step:2,digest:2,import:1,legacy:1};
const low=x=>String(x||'').toLowerCase();
const arr=x=>Array.isArray(x)?x:[];
function rec(o){return Object.assign({id:'',layer:'',kind:'',text:'',who:[],where:'',t:null,ch:null,tid:null,branch:null,src:'narrator',conf:null,pin:false,lock:false,since:null,until:null,supersedes:[],links:[],deleted:false},o)}
const pairKey=(a,b)=>[a,b].map(x=>String(x).trim()).sort((x,y)=>low(x)<low(y)?-1:1).join(' | ');

/* build(src) -> {v:2, records[]}. src = {sessionId, mem, canon[], notes[], player, setup, era, days, schedule[], progression{}, dead[], quests[], universe[]} */
function build(src){src=src||{};const m=src.mem||{},out=[],B=src.sessionId||null,add=o=>out.push(rec(Object.assign({branch:B},o)));
  // 1 permanent: locked canon, notes, setup, player
  arr(src.canon).forEach((e,i)=>add({id:e.id||('entry-'+i),layer:'permanent',kind:'canon',text:(e.k?e.k+': ':'')+String(e.t||''),src:'canon',lock:!!e.lock,pin:!!e.lock,links:arr(e.aliases)}));
  arr(src.notes).filter(n=>n&&n.on!==false).forEach(n=>add({id:n.id,layer:'permanent',kind:'note:'+(n.pri||'must'),text:String(n.text||''),src:'player',lock:true}));
  if(src.setup)add({id:'setup',layer:'permanent',kind:'setup',text:String(src.setup),src:'canon',lock:true});
  if(src.player&&src.player.name)add({id:'player',layer:'permanent',kind:'player',text:src.player.name+(src.player.desc?': '+src.player.desc:''),who:[src.player.name],src:'player',lock:true});
  // 2 working
  if(m.scene&&(m.scene.where||arr(m.scene.who).length))add({id:'working-scene',layer:'working',kind:'scene',text:[m.scene.where,arr(m.scene.who).join(', '),m.scene.when].filter(Boolean).join(' · '),where:m.scene.where||'',who:arr(m.scene.who).slice()});
  // 3 episodic + 6 relationship (from bond events)
  const rel={};
  arr(m.events).forEach(e=>{add({id:e.id,layer:'episodic',kind:e.kind||'action',text:e.text,who:arr(e.who).slice(),where:e.where||'',t:e.t??null,ch:e.ch??null,tid:e.tid||null,src:e.src==='meta'?(e.via||'narrator'):(e.src||'narrator'),conf:e.imp?e.imp/5:null,links:arr(e.wit).map(w=>'wit:'+w)});
    if(e.kind==='bond'&&arr(e.who).length>=2){const k=pairKey(e.who[0],e.who[1]);(rel[k]=rel[k]||[]).push(e)}});
  Object.keys(rel).forEach(k=>{const ev=rel[k],last=ev[ev.length-1];add({id:'rel:'+k,layer:'relationship',kind:'bond',text:last.text,who:k.split(' | '),t:last.t??null,links:ev.map(x=>x.id),src:'narrator'})});
  // 4 semantic
  arr(m.facts).forEach(f=>add({id:f.id,layer:'semantic',kind:'fact',text:f.text,since:f.since??null,until:f.until??null,storyFrom:f.since??null,storyTo:f.until??null,seenAt:f.since??null,expiredAt:null,src:f.legacy?'legacy':'narrator',conf:f.conf??null,pin:!!f.sticky,links:arr(f.from).map(x=>'from:'+x)}));
  arr(m.secrets).forEach(f=>add({id:f.id,layer:'semantic',kind:'secret',text:f.text,since:f.since??null,until:f.until??null,src:'narrator'}));
  // 5 character
  Object.entries(m.chars||{}).forEach(([n,c])=>{const k=c.kernel||{},s=c.state||{};add({id:'char:'+n,layer:'character',kind:'character',who:[n],where:s.where||'',
    text:[k.core,s.mood&&('mood: '+s.mood),s.status&&('status: '+s.status)].filter(Boolean).join(' · '),links:arr(c.knows).map(id=>'knows:'+id).concat(arr(c.believes).map(id=>'believes:'+id))})});
  // NPC goals and schedules (AI Town idea, advanced by story time only)
  Object.entries(src.npcs||{}).forEach(([n,p])=>{const c=out.find(r=>r.id==='char:'+n);const goals=arr(p.goals).map(String),sched=arr(p.schedule).map(x=>({day:Number(x.day)||0,where:String(x.where||''),doing:String(x.doing||'')}));
    if(c){c.goals=goals;c.schedule=sched}else add({id:'char:'+n,layer:'character',kind:'character',who:[n],text:'',goals,schedule:sched})});
  // 7 temporal
  if(src.era)add({id:'era',layer:'temporal',kind:'era',text:String(src.era),src:'canon',lock:true});
  if(src.days!=null)add({id:'clock',layer:'temporal',kind:'clock',text:'Day '+(1+Number(src.days||0)),t:null});
  arr(src.schedule).forEach((x,i)=>add({id:x.id||('sched-'+i),layer:'temporal',kind:low(x.kind||'deadline').replace(/\s+/g,'-'),text:String(x.text||''),who:x.actor?[x.actor]:[],until:x.day??x.at??null,src:'player'}));
  // 8 world
  const P=src.progression||{};Object.keys(P).forEach(type=>arr(P[type]).forEach(it=>add({id:'prog:'+type+':'+it.name,layer:'world',kind:type,text:it.name+': '+it.value,who:it.owner?[it.owner]:[]})));
  arr(src.dead).forEach(n=>add({id:'dead:'+n,layer:'world',kind:'death',text:n+' is dead',who:[n],lock:true}));
  arr(src.quests).forEach((q,i)=>{const t=typeof q==='string'?q:(q&&q.text)||'';if(t)add({id:(q&&q.id)||('quest-'+i),layer:'world',kind:'quest',text:t})});
  // 9 universe (shared; never becomes character knowledge by itself)
  arr(src.universe).forEach(u=>out.push(rec(Object.assign({},u,{layer:'universe',branch:null,src:u.src||'canon'}))));
  return {v:2,records:out}}

/* Overlays: player edits that live outside per-reply deltas, so regeneration cannot erase them. */
function emptyEdits(){return {v:1,ops:[]}}
function op(edits,o){const e=edits&&edits.v===1?edits:emptyEdits();return {v:1,ops:e.ops.concat([Object.assign({at:Date.now()},o)])}}
const edit=(edits,id,patch)=>op(edits,{op:'edit',id,patch:Object.assign({},patch)});
const pin=(edits,id,on)=>op(edits,{op:'pin',id,on:on!==false});
const lock=(edits,id,on)=>op(edits,{op:'lock',id,on:on!==false});
const remove=(edits,id)=>op(edits,{op:'delete',id});
const restore=(edits,id)=>op(edits,{op:'restore',id});
/* supersede: newer fact replaces an older one from turn t. The old record stays (history), closed at t (Graphiti-style invalidation). */
const supersede=(edits,oldId,newId,t)=>op(edits,{op:'supersede',id:oldId,by:newId,t:Number(t)||0});
const add=(edits,record)=>op(edits,{op:'add',id:record.id,record:rec(Object.assign({src:'player'},record))});
function undo(edits){const e=edits&&edits.v===1?edits:emptyEdits();return {v:1,ops:e.ops.slice(0,-1)}}
const EDITABLE=['text','who','where','kind','since','until','conf','links'];
function apply(store,edits){const byId=new Map(store.records.map(r=>[r.id,Object.assign({},r)]));const hist={};
  arr(edits&&edits.ops).forEach(o=>{if(o.op==='add'){if(!byId.has(o.id))byId.set(o.id,rec(o.record));return}const r=byId.get(o.id);if(!r)return;(hist[o.id]=hist[o.id]||[]).push(o);
    if(o.op==='edit'){if(r.lock&&r.src!=='player'&&r.layer==='permanent')return;EDITABLE.forEach(k=>{if(k in o.patch)r[k]=o.patch[k]});r.src='player';r.edited=true}
    else if(o.op==='pin')r.pin=!!o.on;else if(o.op==='lock')r.lock=!!o.on;else if(o.op==='delete'){if(!(r.lock&&r.layer==='permanent'))r.deleted=true}else if(o.op==='restore')r.deleted=false;else if(o.op==='supersede'){r.until=o.t;r.storyTo=o.t;r.expiredAt=o.t;r.expiredBy=o.by;const n=byId.get(o.by);if(n&&!n.supersedes.includes(r.id))n.supersedes=n.supersedes.concat([r.id])}});
  return {v:2,records:[...byId.values()].map(r=>hist[r.id]?Object.assign(r,{history:hist[r.id].length}):r)}}

/* query(view, q) — deterministic order: pinned first, then layer order, then turn, then id. */
function query(view,q){q=q||{};const words=low(q.text).split(/\s+/).filter(Boolean);
  const asOf=q.asOf==null?null:Number(q.asOf);
  return arr(view&&view.records).filter(r=>(q.deleted==='only'?r.deleted:q.deleted?true:!r.deleted)&&(asOf==null||((r.t==null||r.t<=asOf)&&(r.since==null||r.since<=asOf)&&(r.until==null||r.until>asOf)))&&(!q.layer||(Array.isArray(q.layer)?q.layer.includes(r.layer):r.layer===q.layer))&&(!q.who||arr(r.who).some(w=>low(w)===low(q.who)||low(w).split(/\s+/)[0]===low(q.who)))
    &&(!q.src||r.src===q.src)&&(q.pinned==null||!!r.pin===!!q.pinned)&&(!q.current||r.until==null)&&(q.from==null||(r.t!=null&&r.t>=q.from))&&(q.to==null||(r.t!=null&&r.t<=q.to))&&words.every(w=>low(r.text+' '+arr(r.who).join(' ')+' '+r.where).includes(w)))
   .sort((a,b)=>(b.pin-a.pin)||(LAYERS.indexOf(a.layer)-LAYERS.indexOf(b.layer))||((a.t??-1)-(b.t??-1))||(a.id<b.id?-1:a.id>b.id?1:0))
   .slice(0,q.limit||500)}

/* knowledge boundary: what a character knows (facts linked from their character record) — universe records never count. */
function knows(view,name){const c=arr(view&&view.records).find(r=>r.layer==='character'&&low(r.who[0])===low(name));if(!c)return[];const ids=new Set(c.links.filter(l=>l.startsWith('knows:')).map(l=>l.slice(6)));
  return arr(view.records).filter(r=>r.layer==='semantic'&&ids.has(r.id)&&!r.deleted)}

/* history(edits, id) -> the player operations on one record, oldest first. check(view, id) -> the record as it now stands (for confirming a change applied). */
function history(edits,id){return arr(edits&&edits.ops).filter(o=>o.id===id).map(o=>({op:o.op,at:o.at,patch:o.patch||null,on:o.on??null}))}
function check(view,id){return arr(view&&view.records).find(r=>r.id===id)||null}
/* ---------- Retrieval (Mem0 idea: fused keyword + entity + temporal + importance + pin; no embeddings) ----------
 * retrieve(view, ctx) -> [{record, score, why}] best first. ctx = {text, present[], where, t, layers[], limit, max (chars)}.
 * Deterministic. Facts no longer true at ctx.t are skipped; deleted records never returned; universe records are world truth only. */
const STOP=new Set('the a an and or of to in on at for with from by is are was were be been it its this that he she they them his her their you your i we our as but not no so if then than into out up down over under again'.split(' '));
const toks=x=>low(x).replace(/[^a-z0-9'\s]/g,' ').split(/\s+/).filter(w=>w.length>2&&!STOP.has(w)).map(w=>w.replace(/'s$/,'').replace(/(ies)$/,'y').replace(/s$/,''));
function retrieve(view,ctx){ctx=ctx||{};const pool=arr(view&&view.records).filter(r=>!r.deleted&&(ctx.layers?ctx.layers.includes(r.layer):['episodic','semantic','relationship','world','temporal','universe','character'].includes(r.layer)));
  const t=ctx.t==null?null:Number(ctx.t);const live=pool.filter(r=>t==null||((r.since==null||r.since<=t)&&(r.until==null||r.until>t)&&(r.t==null||r.t<=t)));
  const docs=live.map(r=>toks(r.text+' '+arr(r.who).join(' ')+' '+(r.where||''))),N=docs.length||1,avg=docs.reduce((a,d)=>a+d.length,0)/N||1,df={};docs.forEach(d=>new Set(d).forEach(w=>df[w]=(df[w]||0)+1));
  const q=[...new Set(toks(ctx.text))],present=arr(ctx.present).map(low),where=low(ctx.where),maxT=Math.max(1,...live.map(r=>r.t||0),t||0);
  const out=live.map((r,i)=>{const d=docs[i],tf={};d.forEach(w=>tf[w]=(tf[w]||0)+1);let kw=0;q.forEach(w=>{if(!tf[w])return;const idf=Math.log(1+(N-df[w]+.5)/(df[w]+.5));kw+=idf*(tf[w]*2.2)/(tf[w]+1.2*(1-.75+.75*d.length/avg))});
    const who=arr(r.who).map(low),ent=present.length?who.filter(w=>present.some(p=>p===w||p.split(' ')[0]===w.split(' ')[0])).length/Math.max(1,Math.min(who.length,present.length)):0;
    const plc=where&&low(r.where)&&(low(r.where).includes(where)||where.includes(low(r.where)))?1:0,rec=r.t==null?0.3:Math.exp(-((t??maxT)-r.t)/Math.max(10,maxT/4));
    const imp=r.conf==null?0.5:Number(r.conf),score=kw*1.0+ent*1.5+plc*0.6+rec*0.8+imp*0.7+(r.pin?2:0)+(r.lock?0.5:0);
    return{record:r,score:Math.round(score*1000)/1000,why:{kw:Math.round(kw*100)/100,ent,plc,rec:Math.round(rec*100)/100,imp}}});
  out.sort((a,b)=>b.score-a.score||(a.record.id<b.record.id?-1:1));let n=0,used=0;const lim=ctx.limit||40,max=ctx.max||6000,res=[];
  for(const x of out){const len=String(x.record.text).length+20;if(n>=lim||used+len>max)continue;res.push(x);n++;used+=len}return res}
function render(hits){const by={};hits.forEach(h=>{(by[h.record.layer]=by[h.record.layer]||[]).push(h.record)});const name={episodic:'Past events',semantic:'Known facts',relationship:'Relationships',world:'World state',temporal:'Time',universe:'Shared world',character:'Characters'};
  return Object.keys(by).sort((a,b)=>LAYERS.indexOf(a)-LAYERS.indexOf(b)).map(l=>name[l]+':\n'+by[l].map(r=>'- '+(r.t!=null?'[turn '+r.t+'] ':'')+r.text).join('\n')).join('\n\n')}

/* ---------- Contradictions (rule-based, no AI request) ----------
 * dead character acting after death record; two current facts that say opposite things; a fact that contradicts locked canon. */
const NEG=/\b(not|never|no longer|isn't|wasn't|doesn't|didn't|cannot|can't|won't|dead|gone|lost)\b/;
function overlapT(a,b){const A=new Set(toks(a)),B=new Set(toks(b));if(!A.size||!B.size)return 0;let n=0;A.forEach(w=>{if(B.has(w))n++});return n/Math.min(A.size,B.size)}
function contradictions(view){const R=arr(view&&view.records).filter(r=>!r.deleted),out=[];
  const dead=R.filter(r=>r.layer==='world'&&r.kind==='death').map(r=>({n:low(r.who[0]),t:r.t}));
  R.filter(r=>r.layer==='episodic').forEach(e=>arr(e.who).forEach(w=>{const d=dead.find(x=>x.n===low(w)||x.n.split(' ')[0]===low(w).split(' ')[0]);if(d&&(d.t==null||e.t>d.t)&&!/memory|flashback|ghost|corpse|body|funeral|grave/i.test(e.text))out.push({kind:'dead-acts',ids:[e.id,'dead:'+w],text:w+' is recorded as dead but acts in: '+e.text})}));
  const facts=R.filter(r=>(r.layer==='semantic'||(r.layer==='permanent'&&r.kind==='canon'))&&r.until==null);
  for(let i=0;i<facts.length;i++)for(let j=i+1;j<facts.length;j++){const a=facts[i],b=facts[j];if(a.layer==='permanent'&&b.layer==='permanent')continue;
    if(NEG.test(low(a.text))!==NEG.test(low(b.text))&&overlapT(a.text.replace(NEG,''),b.text.replace(NEG,''))>=0.7)out.push({kind:a.layer==='permanent'||b.layer==='permanent'?'canon':'fact',ids:[a.id,b.id],text:a.text+'  vs  '+b.text})}
  return out}

/* ---------- NPC state for a story day (deterministic; no AI requests) ---------- */
function npcState(view,day){const d=Number(day)||0;return arr(view&&view.records).filter(r=>r.layer==='character'&&!r.deleted&&(arr(r.schedule).length||arr(r.goals).length)).map(r=>{const s=arr(r.schedule).filter(x=>x.day<=d).sort((a,b)=>b.day-a.day)[0]||null;return{name:r.who[0],goals:arr(r.goals),where:s?s.where:'',doing:s?s.doing:'',since:s?s.day:null}})}

function stats(view){const n={};LAYERS.forEach(l=>n[l]=0);arr(view&&view.records).forEach(r=>{if(!r.deleted)n[r.layer]=(n[r.layer]||0)+1});return n}
function integrity(view){const errors=[],ids=new Set();arr(view&&view.records).forEach(r=>{if(!r.id)errors.push('record without id');else if(ids.has(r.id))errors.push('duplicate id '+r.id);ids.add(r.id);if(!LAYERS.includes(r.layer))errors.push('bad layer '+r.layer+' on '+r.id)});return {ok:!errors.length,errors}}

root.SFMem2=Object.freeze({LAYERS,TRUST,build,emptyEdits,edit,pin,lock,remove,restore,add,undo,apply,query,knows,history,check,supersede,retrieve,render,contradictions,npcState,stats,integrity});
})(typeof window!=='undefined'?window:globalThis);
