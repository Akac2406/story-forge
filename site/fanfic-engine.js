/* Story Forge fanfiction engine (contract v2, docs/FANFIC-CONTRACT.md). Pure functions, no network, no AI requests.
 * Part 1: universe store helpers, local indexing of source text, incremental imports with revisions, rule presets.
 * Part 2: canon event dependency evaluation (butterfly effect), impact preview, rule precedence, spoiler-filtered search.
 * The app adapter (index.html) handles files (EPUB via epubText), storage (DB.universes) and saving.
 */
(function(root){
'use strict';
const arr=x=>Array.isArray(x)?x:[];
const low=x=>String(x||'').toLowerCase();
const slug=x=>low(x).normalize('NFKD').replace(/[̀-ͯ]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,48)||'x';
function hash(s){let h=2166136261>>>0;s=String(s||'');for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)>>>0}return h.toString(36)}
const words=s=>(String(s||'').match(/\S+/g)||[]).length;
const ids={char:(u,n)=>'char:'+u+':'+slug(n),ev:(u,n)=>'ev:'+u+':'+n,src:t=>'src:'+slug(t),fact:(u,n)=>'fact:'+u+':'+slug(n)};

/* ---------- Part 1: indexing ---------- */
const HEAD=/^\s*(?:chapter|ch\.?|episode|ep\.?|part|volume|vol\.?|prologue|epilogue|side story)\b[^\n]{0,80}$/im;
/* splitChapters(text) -> [{n,title,text}]. Uses chapter headings; falls back to ~3,000-word blocks. */
function splitChapters(text){const T=String(text||'').replace(/\r\n?/g,'\n');const lines=T.split('\n'),out=[];let cur=null;
  lines.forEach(l=>{if(HEAD.test(l)&&l.trim().length<90){if(cur)out.push(cur);cur={title:l.trim(),lines:[]}}else{if(!cur)cur={title:'Opening',lines:[]};cur.lines.push(l)}});
  if(cur)out.push(cur);let ch=out.map(c=>({title:c.title,text:c.lines.join('\n').trim()})).filter(c=>c.text);
  if(ch.length<=1){const w=T.split(/\s+/),B=3000;ch=[];for(let i=0;i<w.length;i+=B)ch.push({title:'Part '+(ch.length+1),text:w.slice(i,i+B).join(' ')})}
  return ch.map((c,i)=>Object.assign({n:i+1},c))}
/* candidateNames(chapters) -> [{name, count, firstCh, aliases[]}]: capitalised word groups seen in several places (not at sentence start only). */
const COMMON=new Set('The A An And But Or If When Then He She They It His Her Their We I You My Your Our This That These Those What Who Where Why How Yes No Not Chapter Part Volume Episode Mr Mrs Ms Sir Lady Lord Young Old Master Miss However Although Because After Before While During Still Even Just Only Also Perhaps Maybe Suddenly Finally Meanwhile There Here Now Today Tomorrow Yesterday One Two Three'.split(' '));
function candidateNames(chapters,o){o=o||{};const min=o.min||3,cnt=new Map();
  chapters.forEach(c=>{const re=/\b[A-Z][a-z'’]+(?:[ \t]+[A-Z][a-z'’]+){0,2}/g;let m;while((m=re.exec(c.text))){const ws=m[0].split(/\s+/);while(ws.length&&COMMON.has(ws[0]))ws.shift();const nm=ws.filter(w=>!COMMON.has(w)).join(' ');if(!nm||nm.length<3)continue;
    const e=cnt.get(nm)||{name:nm,count:0,firstCh:c.n};e.count++;cnt.set(nm,e)}});
  const all=[...cnt.values()].sort((a,b)=>b.count-a.count||(a.name<b.name?-1:1));
  // fold single words into the most frequent full name that contains them (aliases), then apply the minimum count
  const full=all.filter(e=>e.name.includes(' ')),out=[];all.forEach(e=>{if(!e.name.includes(' ')){const p=full.find(f=>f.name.split(' ').includes(e.name));if(p){(p.aliases=p.aliases||[]).push(e.name);p.count+=e.count;return}}out.push(e)});
  return out.filter(e=>e.count>=min).sort((a,b)=>b.count-a.count||(a.name<b.name?-1:1)).map(e=>({name:e.name,count:e.count,firstCh:e.firstCh,aliases:arr(e.aliases)})).slice(0,o.max||200)}
/* indexSource(text|chapters, meta) -> {source, chapters, names, report}. Local only; candidates are 'uncertain'. */
function indexSource(input,meta){meta=meta||{};const chapters=Array.isArray(input)?input.map((c,i)=>({n:c.n||i+1,title:c.title||('Chapter '+(i+1)),text:String(c.text||'')})):splitChapters(input);
  const src={id:meta.id||ids.src(meta.title||'source'),title:meta.title||'Untitled source',kind:meta.kind||'novel',priority:meta.priority||1,lang:meta.lang||'en',
    chapters:chapters.map(c=>({n:c.n,title:c.title,hash:hash(c.text),words:words(c.text)})),coverage:{from:chapters.length?chapters[0].n:0,to:chapters.length?chapters[chapters.length-1].n:0},indexedAt:meta.now||Date.now()};
  const names=candidateNames(chapters,meta);
  return{source:src,chapters,names,report:{chapters:chapters.length,words:chapters.reduce((a,c)=>a+words(c.text),0),names:names.length}}}
/* emptyUniverse(name) */
function emptyUniverse(name,now){const id=slug(name);return{v:1,id,name:String(name||id),rev:0,created:now||Date.now(),updated:now||Date.now(),revisions:[],sources:[],aliases:{},chars:{},events:[],records:[],conflicts:[],rules:{powers:[],world:[]}}}
/* mergeImport(universe, indexed, o) -> {universe (new object), added, duplicate, conflicts, rev}. Never mutates the input.
 * Same chapter number + same hash = duplicate (skipped). Same number + different hash = conflict record (old kept). New chapters extend coverage. */
function mergeImport(u,ix,o){o=o||{};const U=JSON.parse(JSON.stringify(u)),now=o.now||Date.now();let s=U.sources.find(x=>x.id===ix.source.id);const added=[],dup=[],conf=[];
  if(!s){s=Object.assign({},ix.source,{chapters:[]});U.sources.push(s)}
  ix.source.chapters.forEach(c=>{const old=s.chapters.find(x=>x.n===c.n);if(!old){s.chapters.push(c);added.push(c.n)}else if(old.hash===c.hash)dup.push(c.n);else{conf.push(c.n);U.conflicts.push({id:'sc:'+(U.conflicts.length+1),between:[s.id,s.id],ch:c.n,text:'Chapter '+c.n+' of '+s.title+' differs from the copy already imported',resolved:null,at:now})}});
  s.chapters.sort((a,b)=>a.n-b.n);s.coverage={from:s.chapters.length?s.chapters[0].n:0,to:s.chapters.length?s.chapters[s.chapters.length-1].n:0};s.indexedAt=now;
  arr(ix.names).forEach(nm=>{const id=ids.char(U.id,nm.name);if(!U.chars[id])U.chars[id]={id,name:nm.name,aliases:nm.aliases,canon:'uncertain',firstCh:nm.firstCh,core:{},speech:{},abilities:[],affiliations:[],ambitions:[],arcs:[]};
    U.aliases[id]=[...new Set(arr(U.aliases[id]).concat([nm.name],nm.aliases))]});
  if(added.length||conf.length){U.rev=(U.rev||0)+1;U.revisions.push({rev:U.rev,at:now,note:(o.note||('Imported '+ix.source.title))+(added.length?' · chapters '+added[0]+'–'+added[added.length-1]:'')+(conf.length?' · '+conf.length+' conflicting':'')})}
  U.updated=now;return{universe:U,added,duplicate:dup,conflicts:conf,rev:U.rev}}

/* ---------- Rule presets (engine-owned; UI only displays/edits) ---------- */
const RULE_KEYS=['history','personalities','appearances','powers','family','friendships','romance','fates','majorEvents','minorEvents','chronology','organizations','protagonistAchievements','ending'];
const BASE={history:'locked',personalities:'locked',appearances:'locked',powers:'locked',family:'locked',friendships:'adaptive',romance:'adaptive',fates:'adaptive',majorEvents:'adaptive',minorEvents:'free',chronology:'locked',organizations:'adaptive',protagonistAchievements:'adaptive',ending:'adaptive'};
const MODE_PRESETS={oc:{},self:{},takeover:{protagonistAchievements:'free',friendships:'free'},transmigration:{personalities:'adaptive',protagonistAchievements:'free'},reincarnation:{chronology:'adaptive'},regression:{majorEvents:'free',fates:'free'},
  fixit:{fates:'free',majorEvents:'free',ending:'free'},whatif:{majorEvents:'free'},divergence:{majorEvents:'free',minorEvents:'free',ending:'free'},au:{history:'free',organizations:'free',chronology:'adaptive'},crossover:{powers:'adaptive',organizations:'adaptive'},
  rolereversal:{personalities:'adaptive',family:'adaptive'},parallel:{},nextgen:{family:'adaptive',chronology:'free'},prequel:{chronology:'adaptive',ending:'locked'},sequel:{history:'locked',ending:'free'},missing:{},slice:{majorEvents:'locked'},ensemble:{},altending:{ending:'free',majorEvents:'free'}};
function defaults(types){const r=Object.assign({},BASE);arr(types).forEach(t=>Object.assign(r,MODE_PRESETS[t]||{}));return r}

/* ---------- Part 2: events, butterfly effect, precedence ---------- */
/* need(c, state) -> 'met'|'unmet'|'unknown'|'impossible'. state = {alive:{id:bool}, at:{id:place}, knows:{id:[factId]}, rel:{'a>b':{trust..}}, has:{id:[item]}} */
function need(c,st){st=st||{};const who=c.who;switch(c.kind){
  case'alive':{const v=st.alive&&who in st.alive?st.alive[who]:undefined;if(v===undefined)return'unknown';return v===!!c.value?'met':(c.value&&v===false?'impossible':'unmet')}
  case'at':{const v=st.at&&st.at[who];if(v==null)return'unknown';return low(v)===low(c.value)?'met':'unmet'}
  case'knows':{const k=st.knows&&st.knows[who];if(!k)return'unknown';return k.includes(c.value)?'met':'unmet'}
  case'has':{const k=st.has&&st.has[who];if(!k)return'unknown';return k.includes(c.value)?'met':'unmet'}
  case'rel':{const r=st.rel&&st.rel[who];if(!r)return'unknown';const m=String(c.value).match(/^(\w+)\s*(>=|<=|>|<|=)\s*(-?\d+)$/);if(!m)return'unknown';const v=Number(r[m[1]]),n=Number(m[3]);
    if(!isFinite(v))return'unknown';return({'>=':v>=n,'<=':v<=n,'>':v>n,'<':v<n,'=':v===n})[m[2]]?'met':'unmet'}
  default:return'unknown'}}
/* evaluate(universe, canon, state) -> {status:{evId:{status, why, conflict?}}, conflicts:[...], upcoming:[evId], next, last}
 * Manual statuses already in canon.events (prevented, altered, replaced, delayed, protected) are respected. Only 'impossible' prerequisites invalidate. */
const DONE=new Set(['unchanged','altered','replaced']);const DEAD=new Set(['prevented','impossible']);
function evaluate(u,canon,st){const E=arr(u&&u.events).slice().sort((a,b)=>a.order-b.order),byId=new Map(E.map(e=>[e.id,e])),cur=Object.assign({},canon&&canon.events||{}),out={},conflicts=[];
  const pos=canon&&canon.position&&canon.position.order||0,locks=new Set(arr(canon&&canon.locks).filter(l=>l.kind==='event').map(l=>l.id));
  for(const e of E){const m=cur[e.id];const prot=locks.has(e.id)||(m&&m.status==='protected');
    if(m&&m.status&&m.status!=='protected'&&m.status!=='approaching'&&m.status!=='impossible'){out[e.id]=Object.assign({},m);continue}
    const deadReq=e.requires.filter(r=>out[r]&&DEAD.has(out[r].status)),needs=arr(e.needs).map(c=>({c,r:need(c,st)})),badNeed=needs.filter(x=>x.r==='impossible');
    if(deadReq.length||badNeed.length){const why=(deadReq.length?'requires '+deadReq.map(r=>byId.get(r).title).join(', ')+' ('+deadReq.map(r=>out[r].status).join(', ')+')':'')+(badNeed.length?(deadReq.length?'; ':'')+badNeed.map(x=>x.c.kind+' '+x.c.who+' failed').join(', '):'');
      if(prot){const id='pc:'+e.id;conflicts.push({id,event:e.id,text:e.title+' is protected, but it can no longer happen: '+why,options:['find another reason','unprotect','replace the event']});out[e.id]={status:'protected',why,conflict:id}}
      else out[e.id]={status:'impossible',why};continue}
    if(prot){out[e.id]={status:'protected'};continue}
    if(e.order<=pos){out[e.id]=m&&m.status?Object.assign({},m):{status:'unchanged'};continue}
    const unmet=needs.filter(x=>x.r==='unmet').map(x=>x.c.kind+' '+x.c.who);
    out[e.id]={status:e.order<=pos+2?'approaching':'unchanged',why:unmet.length?'waiting: '+unmet.join(', '):undefined}}
  const upcoming=E.filter(e=>e.order>pos&&!DEAD.has(out[e.id].status)).map(e=>e.id),done=E.filter(e=>e.order<=pos&&DONE.has(out[e.id].status));
  return{status:out,conflicts,upcoming,next:upcoming[0]||null,last:done.length?done[done.length-1].id:null}}
/* impact(universe, canon, state, evId, change) -> [{id,title,from,to}] events whose status would change. Preview only. */
function impact(u,canon,st,evId,change){const a=evaluate(u,canon,st).status,c2=JSON.parse(JSON.stringify(canon||{}));c2.events=Object.assign({},c2.events,{[evId]:{status:change||'prevented'}});
  const b=evaluate(u,c2,st).status;return arr(u.events).filter(e=>(a[e.id]||{}).status!==(b[e.id]||{}).status).map(e=>({id:e.id,title:e.title,from:(a[e.id]||{}).status,to:(b[e.id]||{}).status}))}
/* cycles(universe) -> [[evId...]] dependency cycles (should be empty). */
function cycles(u){const E=new Map(arr(u&&u.events).map(e=>[e.id,e])),seen=new Set(),stack=[],onS=new Set(),out=[];
  const go=id=>{if(onS.has(id)){out.push(stack.slice(stack.indexOf(id)).concat([id]));return}if(seen.has(id))return;seen.add(id);onS.add(id);stack.push(id);arr((E.get(id)||{}).leadsTo).forEach(go);stack.pop();onS.delete(id)};
  E.forEach((_,id)=>go(id));return out}
/* ruleFor(canon, target) -> {rule, source} following precedence: established > exception > lock > category > defaults. */
function ruleFor(canon,target){canon=canon||{};const t=target||{};
  if(t.established)return{rule:'locked',source:'established'};
  const ex=arr(canon.exceptions).find(x=>x.approved&&x.target===t.id);if(ex)return{rule:'free',source:'exception',exception:ex.id};
  if(arr(canon.locks).some(l=>l.id===t.id))return{rule:'locked',source:'lock'};
  const r=canon.rules&&canon.rules[t.category];if(r)return{rule:r,source:'category'};
  return{rule:defaults(canon.mode&&canon.mode.types)[t.category]||'adaptive',source:'default'}}
/* search(universe, canon, query, o) -> universe records + characters visible at the playthrough position (spoiler-filtered).
 * o.forChar: also include that character's explicit foreknowledge. Revision isolation: records with rev > canon.rev are hidden. */
function search(u,canon,query,o){o=o||{};const pos=canon&&canon.position&&canon.position.ch||0,rev=canon&&canon.rev||Infinity,q=low(query).split(/\s+/).filter(Boolean);
  const fk=new Set(o.forChar&&canon&&canon.identity&&canon.identity.canon===o.forChar?arr(canon.identity.foreknowledge):[]);
  const hit=r=>!q.length||q.some(w=>low(r.text+' '+arr(r.who).join(' ')).includes(w));
  const recs=arr(u&&u.records).filter(r=>(r.rev==null||r.rev<=rev)&&(!r.spoilerAt||r.spoilerAt.ch<=pos||fk.has(r.id))&&hit(r)).map(r=>Object.assign({},r,{label:r.canon==='source'?null:r.canon}));
  return recs}

/* ---------- Part 3: characters, knowledge, relationships, fates ---------- */
const nameOf=(u,id)=>((u&&u.chars||{})[id]||{}).name||String(id).split(':').pop();
/* knows(u, canon, charId) -> universe records this character knows at the current position.
 * Characters in record.knownBy (or, for non-secrets without knownBy, record.who) know it regardless of reader spoilers; others know only common facts
 * (no who, not secret) already revealed by the position; the takeover character adds explicit foreknowledge. Never 'everyone knows'. */
function knows(u,canon,charId){const pos=canon&&canon.position&&canon.position.ch||0,rev=canon&&canon.rev||Infinity,fk=new Set(canon&&canon.identity&&canon.identity.canon===charId?arr(canon.identity.foreknowledge):[]);
  return arr(u&&u.records).filter(r=>(r.rev==null||r.rev<=rev)&&r.canon!=='fanon'&&(fk.has(r.id)||(r.knownBy?arr(r.knownBy):(r.kind==='secret'?[]:arr(r.who))).includes(charId)||(!arr(r.who).length&&r.kind!=='secret'&&(!r.spoilerAt||r.spoilerAt.ch<=pos))))}
/* identity(u, canon, charId) -> {canon, player?, inherited?, foreknowledge[], age} — separate records, canon is never modified. */
function identity(u,canon,charId){const c=(u&&u.chars||{})[charId]||null,id=canon&&canon.identity||{},tk=id.canon===charId,age=canon&&canon.position&&canon.position.ages?canon.position.ages[charId]:undefined;
  return{canon:c,player:tk?Object.assign({},id.player||{}):null,inherited:tk?id.inherited||null:null,foreknowledge:tk?arr(id.foreknowledge).slice():[],age:age??null,controlled:tk}}
/* relationships(canon, q) -> directional records filtered by {from, to, involving, kind, includePrivate} */
function relationships(canon,q){q=q||{};return arr(canon&&canon.relationships).filter(r=>(!q.from||r.a===q.from)&&(!q.to||r.b===q.to)&&(!q.involving||r.a===q.involving||r.b===q.involving)&&(!q.kind||arr(r.kinds).includes(q.kind))&&(q.includePrivate!==false||!r.private))}
/* view of a relationship as seen by an observer: private ones only if the observer is in knownBy or is a or b */
function relVisibleTo(r,obs){return!r.private||r.a===obs||r.b===obs||arr(r.knownBy).includes(obs)}

/* ---------- Part 4: mutations with history and undo (return {ok, applied, reason, canon}) ---------- */
const clone=x=>JSON.parse(JSON.stringify(x==null?null:x));
function mutate(canon,op,key,fn,now){const C=clone(canon||{});const prev=clone(C[key]);const r=fn(C);if(r&&r.refuse)return{ok:false,applied:false,reason:r.refuse,canon};
  if(JSON.stringify(C[key])===JSON.stringify(prev))return{ok:false,applied:false,reason:'unchanged',canon};
  C.history=arr(C.history).concat([Object.assign({at:now||Date.now(),op,field:key,prev},r&&r.note||{})]);return{ok:true,applied:true,reason:null,canon:C}}
function setRule(canon,k,v,now){if(!RULE_KEYS.includes(k))return{ok:false,applied:false,reason:'unknown rule',canon};if(!['locked','adaptive','free'].includes(v))return{ok:false,applied:false,reason:'bad value',canon};
  return mutate(canon,'setRule','rules',C=>{C.rules=Object.assign({},C.rules);C.rules[k]=v;return{note:{rule:k,to:v}}},now)}
function lock(canon,kind,id,on,now){return mutate(canon,'lock','locks',C=>{const L=arr(C.locks).filter(l=>!(l.kind===kind&&l.id===id));if(on!==false)L.push({kind,id});C.locks=L;return{note:{kind,id,on:on!==false}}},now)}
function exception(canon,target,text,now){if(!String(text||'').trim())return{ok:false,applied:false,reason:'empty',canon};return mutate(canon,'exception','exceptions',C=>{C.exceptions=arr(C.exceptions).concat([{id:'x'+(arr(C.exceptions).length+1),target,text:String(text).trim(),approved:true,t:now||Date.now()}])},now)}
function setFate(canon,charId,target,now){if(!['preserve','adapt','protected','free'].includes(target))return{ok:false,applied:false,reason:'bad value',canon};return mutate(canon,'setFate','fates',C=>{C.fates=Object.assign({},C.fates);C.fates[charId]=Object.assign({},C.fates[charId],{target})},now)}
function eventStatus(canon,id,status,why,now){if(!['unchanged','altered','prevented','delayed','replaced','protected'].includes(status))return{ok:false,applied:false,reason:'bad value',canon};
  return mutate(canon,'eventStatus','events',C=>{const cur=(C.events||{})[id];if(cur&&cur.status&&['altered','prevented','replaced'].includes(cur.status)&&cur.established)return{refuse:'established'};C.events=Object.assign({},C.events);C.events[id]={status,why:why||'set by the player',t:now||Date.now(),by:['player']}},now)}
function setMode(canon,patch,now){return mutate(canon,'setMode','mode',C=>{C.mode=Object.assign({},C.mode,patch)},now)}
function setPosition(canon,pos,now){return mutate(canon,'setPosition','position',C=>{C.position=Object.assign({},C.position,pos)},now)}
function setPOV(canon,pov,now){if(pov&&pov.mode&&!['first','second','thirdLimited','omniscient','multi'].includes(pov.mode))return{ok:false,applied:false,reason:'bad value',canon};return mutate(canon,'setPOV','pov',C=>{C.pov=Object.assign({},C.pov,pov)},now)}
function setRelationship(canon,rel,now){if(!rel||!rel.a||!rel.b)return{ok:false,applied:false,reason:'needs a and b',canon};const id='rel:'+rel.a+'>'+rel.b;
  return mutate(canon,'setRelationship','relationships',C=>{const L=arr(C.relationships).filter(r=>r.id!==id);L.push(Object.assign({kinds:[],history:[],private:false,knownBy:[]},L.find(r=>r.id===id)||arr(canon&&canon.relationships).find(r=>r.id===id)||{},rel,{id}));C.relationships=L},now)}
function undo(canon){const C=clone(canon||{}),h=arr(C.history);if(!h.length)return{ok:false,applied:false,reason:'nothing to undo',canon};const last=h[h.length-1],fld=last.field||last.key;C[fld]=last.prev;C.history=h.slice(0,-1);return{ok:true,applied:true,reason:null,canon:C,undone:last.op}}

/* ---------- Part 5: prompt canon block and reply check ---------- */
const toks=x=>low(x).replace(/[^a-z0-9'\s]/g,' ').split(/\s+/).filter(w=>w.length>3);
function overlap(a,b){const A=new Set(toks(a)),B=new Set(toks(b));if(!A.size)return 0;let n=0;A.forEach(w=>{if(B.has(w))n++});return n/A.size}
/* canonFor(u, canon, ctx) -> text for the prompt. ctx = {text (recent story), present:[charId], state, max}. Spoiler-safe, budgeted. */
function canonFor(u,canon,ctx){ctx=ctx||{};if(!u||!canon)return'';const max=ctx.max||5000,P=canon.position||{},ev=evaluate(u,canon,ctx.state),L=[];
  L.push('FANFICTION CANON ('+u.name+')');
  realWorldLines(u,canon,ctx.present).forEach(x=>L.push(x));romanceLines(u,canon,ctx.present).forEach(x=>L.push(x));
  L.push('Story position: source chapter '+(P.ch??'?')+(P.date?', '+P.date:'')+(P.ages?', ages: '+Object.entries(P.ages).map(([k,v])=>nameOf(u,k)+' '+v).join(', '):'')+'.');
  const tk=canon.identity&&canon.identity.canon;if(tk)L.push('The player controls '+nameOf(u,tk)+'. Never decide their actions, words or feelings. Their canon personality is a starting point; the player\'s choices take precedence.'+(arr(canon.identity.foreknowledge).length?' They know some future events (foreknowledge); other characters do not.':''));
  const R=canon.rules||{},lk=RULE_KEYS.filter(k=>R[k]==='locked'),fr=RULE_KEYS.filter(k=>R[k]==='free');
  if(lk.length)L.push('Keep exactly as in canon: '+lk.join(', ')+'.');if(fr.length)L.push('Free to change through the story: '+fr.join(', ')+'.');
  arr(canon.exceptions).filter(x=>x.approved).forEach(x=>L.push('Approved change: '+x.text));
  const up=ev.upcoming.slice(0,3).map(id=>arr(u.events).find(e=>e.id===id));if(up.length)L.push('Upcoming canon events that can still happen (let them arise naturally; do not rush or force them):\n'+up.map(e=>'- '+e.title+(ev.status[e.id].status==='approaching'?' (approaching)':'')).join('\n'));
  const gone=arr(u.events).filter(e=>['impossible','prevented'].includes((ev.status[e.id]||{}).status));if(gone.length)L.push('These canon events will NOT happen in this story; do not bring them back:\n'+gone.map(e=>'- '+e.title).join('\n'));
  arr(ctx.present).forEach(cid=>{const c=(u.chars||{})[cid];if(!c||cid===tk)return;const k=knows(u,canon,cid).map(r=>r.text),rel=relationships(canon,{from:cid}).filter(r=>arr(ctx.present).includes(r.b));
    L.push(c.name+': '+[c.core&&c.core.personality,c.speech&&c.speech.tone&&('speaks '+c.speech.tone),c.speech&&c.speech.mannerisms].filter(Boolean).join('; ')+'.'+(k.length?' Knows: '+k.join('; ')+'.':'')+(rel.length?' Feels toward '+rel.map(r=>nameOf(u,r.b)+': '+arr(r.kinds).join('/')+(r.trust!=null?' (trust '+r.trust+')':'')).join(', ')+'.':'')+' Does not know anything not listed here.')});
  const hits=search(u,canon,ctx.text||'',{}).slice(0,8);if(hits.length)L.push('Relevant canon facts (revealed so far):\n'+hits.map(r=>'- '+r.text+(r.label?' ['+r.label+']':'')).join('\n'));
  L.push('Write original scenes. Never copy passages from the source.');
  let out=L.join('\n');if(out.length>max)out=out.slice(0,max-1)+'…';return out}
/* check(u, canon, reply, ctx) -> [{kind, text}] rule and continuity issues. No AI request. */
function check(u,canon,reply,ctx){ctx=ctx||{};const out=[],T=String(reply||''),ev=evaluate(u,canon,ctx.state);
  arr(u&&u.events).filter(e=>['impossible','prevented'].includes((ev.status[e.id]||{}).status)).forEach(e=>{if(overlap(e.summary||e.title,T)>=0.6)out.push({kind:'forced-event',text:'Reply seems to bring back an event that can no longer happen: '+e.title})});
  const pos=canon&&canon.position&&canon.position.ch||0,fk=new Set(arr(canon&&canon.identity&&canon.identity.foreknowledge));
  arr(u&&u.records).filter(r=>r.spoilerAt&&r.spoilerAt.ch>pos&&!fk.has(r.id)).forEach(r=>{if(overlap(r.text,T)>=0.7)out.push({kind:'spoiler',text:'Reply may reveal something not known yet: '+r.text})});
  const st=ctx.state||{};Object.entries(st.alive||{}).filter(([,v])=>v===false).forEach(([id])=>{const n=nameOf(u,id).split(' ')[0];if(new RegExp('(^|\\n)\\s*'+n+'\\s*\\|','i').test(T)||new RegExp('\\b'+n+'\\s+(said|says|replied|shouted|whispered)\\b','i').test(T))out.push({kind:'dead-speaks',text:nameOf(u,id)+' is dead but speaks in the reply'})});
  const tk=canon&&canon.identity&&canon.identity.canon;if(tk){const n=nameOf(u,tk).split(' ')[0];if(new RegExp('\\b'+n+'\\s+(decides|decided|agrees|agreed|says|said)\\b','i').test(T)&&ctx.pov!=='omniscient')out.push({kind:'player-agency',text:'Reply may decide what the player character ('+nameOf(u,tk)+') does or says'})}
  realWorldCheck(u,canon,T,out);
  return out}

/* ---------- Part 6: validation, export, restore preview ---------- */
function validate(u,canon){const issues=[];if(!u)return{ok:false,issues:['universe missing']};if(!canon)return{ok:true,issues:[]};
  if(canon.rev!=null&&canon.rev>(u.rev||0))issues.push('playthrough pinned to a revision the universe does not have');
  Object.keys(canon.rules||{}).forEach(k=>{if(!RULE_KEYS.includes(k))issues.push('unknown rule '+k)});
  const E=new Set(arr(u.events).map(e=>e.id));Object.keys(canon.events||{}).forEach(id=>{if(!E.has(id))issues.push('status for unknown event '+id)});
  arr(canon.locks).forEach(l=>{if(l.kind==='event'&&!E.has(l.id))issues.push('lock on unknown event '+l.id);if(l.kind==='char'&&!(u.chars||{})[l.id])issues.push('lock on unknown character '+l.id)});
  arr(canon.relationships).forEach(r=>{if(r.id!=='rel:'+r.a+'>'+r.b)issues.push('relationship id mismatch '+r.id)});
  if(canon.identity&&canon.identity.canon&&!(u.chars||{})[canon.identity.canon])issues.push('takeover character not in universe');
  cycles(u).forEach(c=>issues.push('dependency cycle '+c.join(' > ')));return{ok:!issues.length,issues}}
function exportStory(se,u,o){o=o||{};const pinned=se&&se.canon&&se.canon.rev;return{kind:'story-forge-fanfic',v:1,at:o.now||Date.now(),session:clone(Object.assign({},se,{key:undefined,ocKey:undefined})),
  universe:u?Object.assign(clone(u),{records:arr(u.records).filter(r=>r.rev==null||pinned==null||r.rev<=pinned)}):null,credentials:false}}
function restorePreview(data){const issues=[];if(!data||data.kind!=='story-forge-fanfic')return{ok:false,issues:['not a Story Forge fanfiction backup']};if(data.v!==1)issues.push('unknown backup version '+data.v);
  if(!data.session||!Array.isArray(data.session.turns))issues.push('backup has no story turns');const s=JSON.stringify(data);if(/"(?:ocKey|apiKey|orKey|password|token|secret)"\s*:\s*"[^"]{8,}/i.test(s)||/\bsk-[A-Za-z0-9_-]{12,}/.test(s))issues.push('backup contains something that looks like a credential');
  const v=data.universe&&data.session&&data.session.canon?validate(data.universe,data.session.canon):{ok:true,issues:[]};
  return{ok:!issues.length&&v.ok,issues:issues.concat(v.issues),summary:{turns:data.session&&arr(data.session.turns).length,universe:data.universe&&data.universe.name,rev:data.session&&data.session.canon&&data.session.canon.rev}}}

/* ---------- Part 7 (contract section 14): real-world universes, romance eligibility, competitions ---------- */
const isReal=(u,id)=>String(id||'').startsWith('person:')||!!((u&&u.people||{})[id]);
const personOf=(u,id)=>(u&&u.people||{})[id]||null;
const nameAny=(u,id)=>id==='player'?'the player character':((personOf(u,id)||{}).name||nameOf(u,id));
const yearOf=x=>{const m=String(x||'').match(/(\d{3,4})/);return m?Number(m[1]):null};
/* ageAt(u, canon, id) -> number|null. Uses established ages first, then birth year vs story date. Conflicting sources -> null. */
function ageAt(u,canon,id){const P=canon&&canon.position||{},set=P.ages&&P.ages[id],c=(u&&u.chars||{})[id]||personOf(u,id)||{},by=yearOf(c.born),dy=yearOf(P.date);
  const calc=by!=null&&dy!=null?dy-by:null;if(set!=null&&calc!=null&&Math.abs(set-calc)>1)return null;return set!=null?Number(set):calc}
/* romanceAllowed(u, canon, a, b) -> {ok, reason}. Safety gate only (preference guides, never forces). */
function romanceAllowed(u,canon,a,b){const R=canon&&canon.romance||{};if(R.pref==='none')return{ok:false,reason:'romance off'};
  for(const id of [a,b]){if(isReal(u,id))return{ok:false,reason:'real person'};const age=ageAt(u,canon,id);if(age==null)return{ok:false,reason:'age unknown'};if(age<18)return{ok:false,reason:'minor'}}
  return{ok:true,reason:null}}
/* seeded PRNG (mulberry32) */
function rng(seed){let t=parseInt(hash(seed),36)>>>0;return()=>{t=(t+0x6D2B79F5)>>>0;let r=Math.imul(t^(t>>>15),1|t);r=(r+Math.imul(r^(r>>>7),61|r))^r;return((r^(r>>>14))>>>0)/4294967296}}
/* rank(entries, config, seed) -> {config, seed, results:[{id, score, rank, parts}]}. Reproducible; random part bounded by config.random (percent of 100). */
function rank(entries,config,seed){const W=(config&&config.weights)||{performance:40,votes:25,skill:20,teamwork:10},rnd=Math.max(0,Math.min(20,Number(config&&config.random)||0)),tot=Object.values(W).reduce((a,b)=>a+Number(b||0),0)||1,R=rng(seed);
  const res=arr(entries).slice().sort((x,y)=>x.id<y.id?-1:1).map(e=>{const parts={};let sc=0;Object.keys(W).forEach(k=>{const v=Math.max(0,Math.min(100,Number((e.factors||{})[k])||0))*W[k]/tot;parts[k]=Math.round(v*100)/100;sc+=v});
    const r=(R()*2-1)*rnd;parts.random=Math.round(r*100)/100;sc=Math.max(0,sc*(100-rnd)/100+r+rnd/2);return{id:e.id,score:Math.round(sc*100)/100,parts}});
  res.sort((x,y)=>y.score-x.score||(x.id<y.id?-1:1)).forEach((x,i)=>x.rank=i+1);return{config:{weights:W,random:rnd},seed:String(seed),results:res}}
/* recordCompetition(canon, id, result, o) — established outcomes are never re-rolled unless o.replace is explicitly set by the player. */
function recordCompetition(canon,id,result,o){if((canon&&canon.competitions||{})[id]&&!(o&&o.replace))return{ok:false,applied:false,reason:'established',canon};
  return mutate(canon,'competition','competitions',C=>{C.competitions=Object.assign({},C.competitions);C.competitions[id]=Object.assign({at:(o&&o.now)||Date.now()},result)},o&&o.now)}
function setRomance(canon,patch,now){const p=patch||{};if(p.pref&&!['bl','gl','straight','any','none'].includes(p.pref))return{ok:false,applied:false,reason:'bad value',canon};
  if(p.focus&&!['background','optional','balanced','central'].includes(p.focus))return{ok:false,applied:false,reason:'bad value',canon};
  return mutate(canon,'setRomance','romance',C=>{C.romance=Object.assign({},C.romance,p)},now)}
const ROMANCE_WORDS=/\b(kiss(?:es|ed|ing)?|dat(?:e|es|ed|ing)\b(?! of)|in love|confess(?:es|ed|ion)?|romantic|boyfriend|girlfriend|lover|cuddl\w*|blush\w* .{0,20}heart|holds? (?:his|her|their) hand)\b/i;
function realWorldLines(u,canon,present){if(!u||!u.type||u.type==='fictional')return[];const ppl=arr(present).filter(id=>isReal(u,id)).map(id=>nameAny(u,id));
  return['This is ALTERNATE-REALITY FICTION based on public events ('+u.type+'). Invented events are fiction, not fact.',
    'Real public figures'+(ppl.length?' ('+ppl.join(', ')+')':'')+' appear only in professional and public settings: practice, performances, competitions, public appearances. Never give them romance, sexuality, health issues, scandals, crimes, family or private-life details, and never invent quotes presented as real.']}
function romanceLines(u,canon,present){const R=canon&&canon.romance;if(!R)return[];if(R.pref==='none')return['No romance in this story.'];
  const ids=['player'].concat(arr(present)),ok=[],no=[];ids.forEach((a,i)=>ids.slice(i+1).forEach(b=>{if(a!=='player'&&b!=='player')return;const r=romanceAllowed(u,canon,a,b);(r.ok?ok:no).push(nameAny(u,a==='player'?b:a)+(r.ok?'':' ('+r.reason+')'))}));
  return['Romance preference: '+({bl:'BL',gl:'GL',straight:'straight',any:'any'})[R.pref||'any']+', focus '+(R.focus||'optional')+', pacing '+(R.pacing||'natural')+'. Non-explicit. Characters choose freely; romance is never guaranteed.'+(ok.length?' Possible romantic interests here: '+ok.join(', ')+'.':'')+(no.length?' Never romantic with: '+no.join(', ')+'.':'')]}
function realWorldCheck(u,canon,T,out){const sent=String(T||'').split(/(?<=[.!?\n])\s+/);
  sent.filter(x=>ROMANCE_WORDS.test(x)).forEach(x=>{Object.keys(u&&u.people||{}).forEach(id=>{const n=nameAny(u,id).split(' ')[0];if(new RegExp('\\b'+n+'\\b','i').test(x))out.push({kind:'real-person-romance',text:'Romance involving a real person: '+x.slice(0,140)})});
    Object.keys(u&&u.chars||{}).forEach(id=>{const age=ageAt(u,canon,id),n=nameOf(u,id).split(' ')[0];if(age!=null&&age<18&&new RegExp('\\b'+n+'\\b','i').test(x))out.push({kind:'minor-romance',text:'Romance involving a minor ('+nameOf(u,id)+'): '+x.slice(0,140)})})});return out}

/* ---------- Part 8 (roadmap phase 8): persistent universes and crossovers ---------- */
const uOfId=id=>{const m=String(id||'').match(/^(?:char|ev|fact|fanon|person):([^:]+):/);return m?m[1]:null};
/* upgradePreview(u, canon, state) -> {from, to, newRecords, newEvents, statusChanges} — nothing is changed. */
function upgradePreview(u,canon,state){const from=canon&&canon.rev||0,to=u&&u.rev||0;if(to<=from)return{from,to,newRecords:[],newEvents:[],statusChanges:[]};
  const newRecords=arr(u.records).filter(r=>r.rev!=null&&r.rev>from&&r.rev<=to).map(r=>r.id),newEvents=arr(u.events).filter(e=>e.rev!=null&&e.rev>from).map(e=>e.id);
  const a=evaluate(u,canon,state).status,c2=Object.assign({},canon,{rev:to}),b=evaluate(u,c2,state).status;
  return{from,to,newRecords,newEvents,statusChanges:arr(u.events).filter(e=>(a[e.id]||{}).status!==(b[e.id]||{}).status).map(e=>({id:e.id,from:(a[e.id]||{}).status,to:(b[e.id]||{}).status}))}}
function upgrade(canon,u,now){if(!u||(canon&&canon.rev||0)>=(u.rev||0))return{ok:false,applied:false,reason:'already current',canon};return mutate(canon,'upgrade','rev',C=>{C.rev=u.rev;return{note:{to:u.rev}}},now)}
/* promote(u, record, o) -> {ok, applied, reason, universe}: a playthrough fact becomes shared universe material, marked fanon unless o.canon; never character knowledge. */
function promote(u,rec,o){o=o||{};if(!u||!rec||!String(rec.text||'').trim())return{ok:false,applied:false,reason:'nothing to promote',universe:u};const U=clone(u),id='fanon:'+U.id+':'+slug(rec.id||rec.text);
  if(arr(U.records).some(r=>r.id===id||low(r.text)===low(rec.text)))return{ok:false,applied:false,reason:'already in the universe',universe:u};
  U.records=arr(U.records).concat([{id,layer:'universe',kind:rec.kind||'fact',text:String(rec.text).trim(),who:arr(rec.who),canon:o.canon?'source':'fanon',from:{session:o.session||null,record:rec.id||null},rev:U.rev||0,spoilerAt:null}]);U.updated=o.now||Date.now();
  return{ok:true,applied:true,reason:null,universe:U}}
function demote(u,id){const U=clone(u),n=arr(U.records).length;U.records=arr(U.records).filter(r=>!(r.id===id&&String(id).startsWith('fanon:')));return U.records.length<n?{ok:true,applied:true,reason:null,universe:U}:{ok:false,applied:false,reason:'only promoted (fanon) records can be removed',universe:u}}
/* crossover(universes) -> combined read-only view; ids stay namespaced; powers from every universe. */
function crossover(list){const L=arr(list).filter(Boolean),C={v:1,id:L.map(u=>u.id).join('+'),name:L.map(u=>u.name).join(' × '),type:L.some(u=>u.type&&u.type!=='fictional')?'hybrid':'fictional',rev:0,chars:{},people:{},aliases:{},events:[],records:[],rules:{powers:[],world:[]},sources:[],conflicts:[]};
  L.forEach(u=>{Object.assign(C.chars,u.chars||{});Object.assign(C.people,u.people||{});Object.assign(C.aliases,u.aliases||{});C.events=C.events.concat(arr(u.events));C.records=C.records.concat(arr(u.records));C.rules.powers=C.rules.powers.concat(arr(u.rules&&u.rules.powers).map(p=>Object.assign({universe:u.id},p)));C.rules.world=C.rules.world.concat(arr(u.rules&&u.rules.world).map(w=>'['+u.name+'] '+w))});return C}
/* powerRule(canon, fromUniverse, toUniverse) -> {rule, scale, note} (default: separate systems, original scale). */
function powerRule(canon,from,to){const r=arr(canon&&canon.powers).find(p=>p.from===from&&p.to===to)||arr(canon&&canon.powers).find(p=>p.from===to&&p.to===from&&p.rule!=='translated');return r?{rule:r.rule,scale:r.scale||'original',note:r.note||''}:{rule:'separate',scale:'original',note:'Abilities follow the rules of their own universe.'}}
/* homeUniverse(charId) and crossover-aware knowledge: in a crossover, common facts are known only within their own universe. */
function knowsX(u,canon,charId){const multi=arr(canon&&canon.universes).length>1,home=uOfId(charId);const k=knows(u,canon,charId);return multi&&home?k.filter(r=>arr(r.knownBy).includes(charId)||arr(r.who).includes(charId)||uOfId(r.id)===home):k}

/* ---------- Story creation: newCanon(u, o) -> {ok, reason, canon, summary} (pure; nothing stored) ----------
   o: {modes:[...], start:{ch}, takeover?:charId, player?:{name, desc}, startAge?, pov?:{mode, who?}, romance?:{pref, pacing?},
       rules?:{key:'locked'|'adaptive'|'free'}, crossover?:{with:[universeIds], link?, powers?:[...]}} */
const RULE_VALUES=['locked','adaptive','free'],NEEDS_BODY=['takeover','transmigration','regression','reincarnation'];
function newCanon(u,o){o=o||{};if(!u||!u.id)return{ok:false,reason:'universe missing'};const modes=arr(o.modes).filter(Boolean);
  if(!modes.length)return{ok:false,reason:'choose at least one mode'};const bad=modes.find(m=>!Object.prototype.hasOwnProperty.call(MODE_PRESETS,m));if(bad)return{ok:false,reason:'unknown mode '+bad};
  const body=modes.find(m=>NEEDS_BODY.includes(m)&&m!=='reincarnation');if(body&&!o.takeover)return{ok:false,reason:body+' needs a canon character to become'};
  if(o.takeover&&!(u.chars||{})[o.takeover])return{ok:false,reason:'unknown character '+o.takeover};
  const chs=arr(u.sources).reduce((n,x)=>n+arr(x.chapters).length,0),ch=Math.max(0,Math.round(+((o.start||{}).ch)||0));if(chs&&ch>chs)return{ok:false,reason:'start chapter is past the end of the source ('+chs+' chapters)'};
  const pov=Object.assign({mode:'second'},o.pov||{});if(!['first','second','thirdLimited','omniscient','multi'].includes(pov.mode))return{ok:false,reason:'bad point of view'};
  const rom=o.romance||null;if(rom&&rom.pref&&!['bl','gl','straight','any','none'].includes(rom.pref))return{ok:false,reason:'bad romance preference'};
  const rules=defaults(modes);for(const [k,v] of Object.entries(o.rules||{})){if(!(k in rules))return{ok:false,reason:'unknown rule '+k};if(!RULE_VALUES.includes(v))return{ok:false,reason:'bad value for '+k};rules[k]=v}
  const who=o.takeover||null,pl=o.player||{};const player={name:String(pl.name||(who?((u.chars[who]||{}).name||''):'')||'').slice(0,60),desc:String(pl.desc||'').slice(0,1000),origin:modes.includes('takeover')?'takeover':modes.includes('transmigration')?'transmigration':modes.includes('self')?'self':'oc'};
  if(!player.name)return{ok:false,reason:'the player character needs a name'};
  const canon={universe:u.id,rev:u.rev||0,mode:{types:modes,start:{ch,order:0},takeover:who,player,startAge:o.startAge==null?null:+o.startAge},pov:who&&!pov.who?Object.assign(pov,{who}):pov,
    position:{ch,order:0},rules,locks:[],exceptions:[],events:{},fates:{},relationships:[],hist:[]};
  if(rom)canon.romance=Object.assign({pref:'any',pacing:'natural'},rom);
  const X=o.crossover;if(X&&arr(X.with).length){canon.universes=[{id:u.id,role:'primary'}].concat(arr(X.with).filter(id=>id&&id!==u.id).map(id=>({id,role:'secondary'})));canon.link=X.link||'merged';canon.powers=arr(X.powers);if(!modes.includes('crossover'))canon.mode.types=modes.concat(['crossover'])}
  return{ok:true,reason:null,canon,summary:{universe:u.name||u.id,modes:canon.mode.types,start:ch,player:player.name,takeover:who?((u.chars[who]||{}).name||who):null,pov:canon.pov.mode,crossover:canon.universes?canon.universes.map(x=>x.id):null,locked:Object.keys(rules).filter(k=>rules[k]==='locked')}}}

root.SFFan=Object.freeze({slug,hash,ids,splitChapters,candidateNames,indexSource,emptyUniverse,mergeImport,RULE_KEYS,defaults,need,evaluate,impact,cycles,ruleFor,search,
  knows,identity,relationships,relVisibleTo,isReal,ageAt,romanceAllowed,rank,recordCompetition,setRomance,upgradePreview,upgrade,promote,demote,crossover,powerRule,knowsX,uOfId,newCanon,MODES:Object.freeze(Object.keys(MODE_PRESETS)),setRule,lock,exception,setFate,eventStatus,setMode,setPosition,setPOV,setRelationship,undo,canonFor,check,validate,exportStory,restorePreview});
})(typeof window!=='undefined'?window:globalThis);
