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
  arr(m.facts).forEach(f=>add({id:f.id,layer:'semantic',kind:'fact',text:f.text,since:f.since??null,until:f.until??null,src:f.legacy?'legacy':'narrator',conf:f.conf??null,pin:!!f.sticky}));
  arr(m.secrets).forEach(f=>add({id:f.id,layer:'semantic',kind:'secret',text:f.text,since:f.since??null,until:f.until??null,src:'narrator'}));
  // 5 character
  Object.entries(m.chars||{}).forEach(([n,c])=>{const k=c.kernel||{},s=c.state||{};add({id:'char:'+n,layer:'character',kind:'character',who:[n],where:s.where||'',
    text:[k.core,s.mood&&('mood: '+s.mood),s.status&&('status: '+s.status)].filter(Boolean).join(' · '),links:arr(c.knows).map(id=>'knows:'+id).concat(arr(c.believes).map(id=>'believes:'+id))})});
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
const add=(edits,record)=>op(edits,{op:'add',id:record.id,record:rec(Object.assign({src:'player'},record))});
function undo(edits){const e=edits&&edits.v===1?edits:emptyEdits();return {v:1,ops:e.ops.slice(0,-1)}}
const EDITABLE=['text','who','where','kind','since','until','conf','links'];
function apply(store,edits){const byId=new Map(store.records.map(r=>[r.id,Object.assign({},r)]));const hist={};
  arr(edits&&edits.ops).forEach(o=>{if(o.op==='add'){if(!byId.has(o.id))byId.set(o.id,rec(o.record));return}const r=byId.get(o.id);if(!r)return;(hist[o.id]=hist[o.id]||[]).push(o);
    if(o.op==='edit'){if(r.lock&&r.src!=='player'&&r.layer==='permanent')return;EDITABLE.forEach(k=>{if(k in o.patch)r[k]=o.patch[k]});r.src='player';r.edited=true}
    else if(o.op==='pin')r.pin=!!o.on;else if(o.op==='lock')r.lock=!!o.on;else if(o.op==='delete'){if(!(r.lock&&r.layer==='permanent'))r.deleted=true}else if(o.op==='restore')r.deleted=false});
  return {v:2,records:[...byId.values()].map(r=>hist[r.id]?Object.assign(r,{history:hist[r.id].length}):r)}}

/* query(view, q) — deterministic order: pinned first, then layer order, then turn, then id. */
function query(view,q){q=q||{};const words=low(q.text).split(/\s+/).filter(Boolean);
  return arr(view&&view.records).filter(r=>(q.deleted?true:!r.deleted)&&(!q.layer||(Array.isArray(q.layer)?q.layer.includes(r.layer):r.layer===q.layer))&&(!q.who||arr(r.who).some(w=>low(w)===low(q.who)||low(w).split(/\s+/)[0]===low(q.who)))
    &&(!q.src||r.src===q.src)&&(q.pinned==null||!!r.pin===!!q.pinned)&&(q.from==null||(r.t!=null&&r.t>=q.from))&&(q.to==null||(r.t!=null&&r.t<=q.to))&&words.every(w=>low(r.text+' '+arr(r.who).join(' ')+' '+r.where).includes(w)))
   .sort((a,b)=>(b.pin-a.pin)||(LAYERS.indexOf(a.layer)-LAYERS.indexOf(b.layer))||((a.t??-1)-(b.t??-1))||(a.id<b.id?-1:a.id>b.id?1:0))
   .slice(0,q.limit||500)}

/* knowledge boundary: what a character knows (facts linked from their character record) — universe records never count. */
function knows(view,name){const c=arr(view&&view.records).find(r=>r.layer==='character'&&low(r.who[0])===low(name));if(!c)return[];const ids=new Set(c.links.filter(l=>l.startsWith('knows:')).map(l=>l.slice(6)));
  return arr(view.records).filter(r=>r.layer==='semantic'&&ids.has(r.id)&&!r.deleted)}

function stats(view){const n={};LAYERS.forEach(l=>n[l]=0);arr(view&&view.records).forEach(r=>{if(!r.deleted)n[r.layer]=(n[r.layer]||0)+1});return n}
function integrity(view){const errors=[],ids=new Set();arr(view&&view.records).forEach(r=>{if(!r.id)errors.push('record without id');else if(ids.has(r.id))errors.push('duplicate id '+r.id);ids.add(r.id);if(!LAYERS.includes(r.layer))errors.push('bad layer '+r.layer+' on '+r.id)});return {ok:!errors.length,errors}}

root.SFMem2=Object.freeze({LAYERS,TRUST,build,emptyEdits,edit,pin,lock,remove,restore,add,undo,apply,query,knows,stats,integrity});
})(typeof window!=='undefined'?window:globalThis);
