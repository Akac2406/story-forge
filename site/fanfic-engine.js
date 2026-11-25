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

root.SFFan=Object.freeze({slug,hash,ids,splitChapters,candidateNames,indexSource,emptyUniverse,mergeImport,RULE_KEYS,defaults,need,evaluate,impact,cycles,ruleFor,search});
})(typeof window!=='undefined'?window:globalThis);
