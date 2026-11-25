/* Story Forge memory engine — Phase 0 scaffolding + Phase 1 event ledger and reversible deltas (opt-in).
 * No automatic migration or writes; the existing narrator remains authoritative.
 */
(function(root){
'use strict';
const clone=x=>JSON.parse(JSON.stringify(x));
function init(){return {v:1,seq:0,events:[],facts:[],secrets:[],chars:{},scenes:[],checks:[],stats:{cacheHit:0,inTok:0,cachedTok:0}}}
function migrate(session,story){
 const se=session||{}, mem=init();
 const next=(prefix)=>prefix+(++mem.seq);
 (se.facts||[]).forEach(f=>{const text=typeof f==='string'?f:(f&&f.text)||'';if(text)mem.facts.push({id:next('f'),text,from:[],since:0,until:null,sticky:false,conf:null,legacy:true})});
 (se.mems||[]).forEach(m=>{const text=typeof m==='string'?m:(m&&m.x)||'';if(text)mem.events.push({id:next('e'),t:Math.max(0,Number(se.upto)||0),ch:0,when:'',where:'',who:[],wit:[],kind:'memory',imp:3,text,open:false,src:'import'})});
 (se.chaps||[]).forEach((c,i)=>{if(c&&c.sum)mem.events.push({id:next('e'),t:0,ch:i,when:'',where:'',who:[],wit:[],kind:'summary',imp:3,text:String(c.sum),open:false,src:'digest'});(c&&c.conf||[]).forEach(x=>mem.checks.push({id:next('k'),t:0,kind:'legacy',text:String(x),ok:null}))});
 Object.entries(se.cast||{}).forEach(([name,c])=>{mem.chars[name]={kernel:{core:Array.isArray(c.t)?c.t.join(', '):String(c.t||''),voice:'',values:'',lines:[]},state:{mood:'',where:'',status:(se.dead||[]).includes(name)?'dead':'alive',goal:''},knows:[],beliefs:[],mem:[]}});
 (se.quests||[]).forEach(q=>{const text=typeof q==='string'?q:(q&&q.text)||'';if(text)mem.events.push({id:next('e'),t:0,ch:0,when:'',where:'',who:[],wit:[],kind:'quest',imp:3,text,open:true,src:'import'})});
 mem.events.sort((a,b)=>a.t-b.t);
 return mem;
}
function relHistory(se,a,b,n=3){const names=[String(a).toLowerCase(),String(b).toLowerCase()];return ((se&&se.mem&&se.mem.events)||[]).filter(e=>e.kind==='bond'&&names.every(x=>(e.who||[]).some(y=>String(y).toLowerCase()===x))).sort((x,y)=>(y.imp||0)-(x.imp||0)||(y.t||0)-(x.t||0)).slice(0,n).map(({id,text,when,imp,kind})=>({id,text,when,imp,kind}));}
function timeline(se,filter){const events=((se&&se.mem&&se.mem.events)||[]);return events.filter(e=>!filter||(typeof filter==='string'?(e.kind===filter||(e.who||[]).includes(filter)):(!filter.kind||e.kind===filter.kind)&&(!filter.who||(e.who||[]).includes(filter.who)))).map(clone)}
function charView(se,name){const c=se&&se.mem&&se.mem.chars&&se.mem.chars[name];if(!c)return null;const m=se.mem;return {kernel:clone(c.kernel),state:clone(c.state),knows:(c.knows||[]).map(id=>(m.facts||[]).concat(m.secrets||[]).find(x=>x.id===id)?.text).filter(Boolean),beliefs:clone(c.beliefs||[]),recent:(c.mem||[]).map(id=>m.events.find(x=>x.id===id)).filter(Boolean).slice(-5).map(clone)}}
function checks(se){return clone((se&&se.mem&&se.mem.checks)||[]).filter(c=>c.ok!==true)}
function stats(se){const m=se&&se.mem;if(!m)return {events:0,facts:0,cacheHitPct:0,lastSnapshotAt:null};const s=m.stats||{};return {events:m.events.length,facts:m.facts.length,cacheHitPct:s.inTok?Math.round(100*(s.cachedTok||0)/s.inTok):0,lastSnapshotAt:s.lastSnapshotAt||null}}
function integrity(mem){if(!mem||mem.v!==1)return {ok:false,errors:['Unsupported memory schema']};const errors=[],ids=new Set((mem.events||[]).map(e=>e.id));if(ids.size!==(mem.events||[]).length)errors.push('Duplicate event IDs');for(let i=1;i<(mem.events||[]).length;i++)if(mem.events[i].t<mem.events[i-1].t)errors.push('Events out of turn order');(mem.facts||[]).forEach(f=>(f.from||[]).forEach(id=>{if(!ids.has(id))errors.push('Missing provenance '+id)}));return {ok:errors.length===0,errors}}

/* ---------- Phase 1: event ledger and reversible per-turn deltas ----------
 * parseMeta(raw)            -> {events, learned, scene}   (pure)
 * buildDelta(mem, p, ctx)   -> mx                          (pure, does not touch mem)
 * apply(mem, mx)            -> applies a delta (idempotent)
 * undo(mem, mx)             -> reverses a delta
 * record(mem, p, ctx)       -> buildDelta + apply, returns mx
 * shiftTurns(mem, after, d) -> moves turn anchors after a message is deleted
 * A delta stores full copies of everything it adds, so it can be re-applied
 * later (switching back to an older generated version) without the model.
 */
const KINDS=['action','reveal','promise','betrayal','injury','death','item','travel','bond','secret','decision','threat','mystery'];
const OPEN_KINDS={promise:1,secret:1,threat:1,mystery:1};
const IMPW={trivial:1,minor:1,low:2,small:2,medium:3,moderate:3,normal:3,high:4,major:4,important:4,critical:5,huge:5,pivotal:5,'very high':5};
const impOf=x=>{const n=parseInt(x,10);if(n>=1)return Math.min(5,n);const w=String(x||'').toLowerCase().replace(/[^a-z ]/g,'').trim();return IMPW[w]||0};
const NONE=/^\s*(none|n\/a|-+|nothing|unknown|unclear|…|\.\.\.)\.?\s*$/i;
const clean=x=>String(x==null?'':x).replace(/^[\s*_"“]+|[\s*_"”]+$/g,'').trim();
/* Bracketed notes ("Ilse (watching, hidden)") are dropped before splitting, so their words never become characters. */
const names=x=>String(x||'').replace(/\([^()]*\)/g,' ').replace(/\([^()]*$/,' ').split(/\s*,\s*|\s+and\s+/).map(clean).filter(n=>n&&!NONE.test(n)&&n.length<=48);
const norm=t=>String(t||'').toLowerCase().replace(/[^a-z0-9\s]/g,' ').split(/\s+/).filter(w=>w.length>2||/^\d+$/.test(w));
function overlap(a,b){const A=new Set(norm(a)),B=new Set(norm(b));if(!A.size||!B.size)return 0;let n=0;A.forEach(w=>{if(B.has(w))n++});return n/Math.min(A.size,B.size)}
const KEYLINE=/^[\s*_>#-]*[A-Z][A-Z ]{2,}[*_]*\s*:/;
/* Where the metadata starts: the [[META]] marker, a bare META heading, or (when the model forgot the marker)
   a trailing run of at least two known KEY: lines. Returns -1 when there is none. */
function metaStart(t){t=String(t||"");let i=t.indexOf("[[META");if(i>=0)return i;
  const hd=t.match(/(^|\n)[ \t]*(?:#+[ \t]*|\*\*|__)?\[?META(?:DATA)?\]?(?:\*\*|__)?[ \t]*:?[ \t]*(?=\n)/i);if(hd)return hd.index+hd[1].length;
  const L=t.split("\n"),K=/^[\s*_>#-]*([A-Z][A-Z ]{1,20}?)[*_]*\s*:/,C=/^\s*(?:[-•*]|\d+[.)])\s+\S/,CORE=/^(NEXT|EVENTS|LEARNED|SCENE|STATS|CAST|BONDS|GOAL|QUESTS|STATUS|TOPICS|COUNTERS|CHAPTER|INFO|DEAD|ENDING)$/;
  let start=-1,keys=0,core=0,pos=t.length;for(let j=L.length-1;j>=0;j--){const l=L[j];pos-=l.length+(j<L.length-1?1:0);if(!l.trim()||/^\s*(```|---+|\*\*\*+)\s*$/.test(l))continue;const m=l.match(K);
    if(m){keys++;if(CORE.test(m[1].trim()))core++;start=pos;continue}if(C.test(l))continue;break}
  return keys>=2&&core>=2?start:-1}
function metaBlock(raw){const s=String(raw||''),i=metaStart(s);return i<0?'':s.slice(i).replace(/```[a-z]*\n?/gi,'')}
/* Value of KEY: the rest of its line plus any following lines up to the next KEY: line.
   Bullets and numbering on continuation lines are removed and the lines are joined with ";". */
function metaLine(raw,key,info){const lines=metaBlock(raw).split('\n'),re=new RegExp('^[\\s*_>#-]*'+key+'[*_]*\\s*:\\s*(.*)$','i');let k=-1,first='';
  for(let j=0;j<lines.length;j++){const m=lines[j].match(re);if(m){k=j;first=m[1];break}}if(k<0)return'';
  const parts=[first.replace(/^[\s*_]+/,'').replace(/[*_]+$/,'').trim()];for(let j=k+1;j<lines.length;j++){const l=lines[j];if(KEYLINE.test(l)||/^\s*\[\[/.test(l))break;const t=l.replace(/^\s*(?:[-•*]|\d+[.)])\s*/,'').replace(/[*_]+$/,'').trim();if(t){parts.push(t);if(info)info.multi=true}}
  return parts.filter(Boolean).join('; ')}
/* EVENTS splitting (v88). Models often get the separators wrong: ";" before the witnesses, events chained
   with "|" instead of ";", a missing importance, or a ";" inside the description. Instead of splitting on ";",
   find where each event starts — an importance (1-5 or a word like "high") followed by a known kind, or a known
   kind right after a witness field — and read each event's fields from there. Returns
   {imp (raw text or null), kind, who, where, text, wit, n (fields found), fixed (1 when separators were repaired)}. */
const KALIAS={clue:'reveal',discovery:'reveal',revelation:'reveal',information:'reveal',info:'reveal',confession:'reveal',conflict:'threat',danger:'threat',warning:'threat',fight:'action',combat:'action',movement:'travel',journey:'travel',arrival:'travel',departure:'travel',relationship:'bond',romance:'bond',friendship:'bond',loss:'death',wound:'injury',choice:'decision',plan:'decision',agreement:'decision',vow:'promise',oath:'promise',deception:'secret',lie:'secret',object:'item'};
const kindOf=x=>{const k=clean(x).toLowerCase();return KINDS.includes(k)?k:(KALIAS[k]||'')};
const looksNames=x=>{const v=String(x||'').replace(/\([^()]*\)/g,'').trim();if(NONE.test(v))return true;const L=names(v);return L.length>0&&L.every(n=>/^[A-Z]/.test(n)&&n.split(/\s+/).length<=4)};
function splitEvents(ev){
  const tok=[];let cur='',sep='';for(const ch of String(ev)){if(ch==='|'||ch===';'){tok.push({x:cur.trim(),s:sep});cur='';sep=ch}else cur+=ch}tok.push({x:cur.trim(),s:sep});
  const starts=[];
  for(let i=0;i<tok.length;i++){
    if(starts.length&&starts[starts.length-1]>=i)continue;
    const k=kindOf(tok[i].x),strictImp=/^[1-5]$/.test(tok[i].x);
    if(strictImp&&i+2<tok.length&&/^[a-z]+$/i.test(tok[i+1].x)&&(i===0||tok[i].s===';'||kindOf(tok[i+1].x))){starts.push(i);continue}
    if(!k||i+1>=tok.length)continue;
    const p=i>0?tok[i-1]:null;
    if(!p){starts.push(i);continue}
    if(impOf(p.x)&&!(starts.length&&starts[starts.length-1]===i-1)){starts.push(i-1);continue}
    if(NONE.test(p.x)||p.s==='|'){if(i>=4)starts.push(i);continue}
    if(p.s===';'||i===1)starts.push(i-1)}
  if(!starts.length)tok.forEach((t,i)=>{if(i&&t.s===';')starts.push(i)});
  if(!starts.length||starts[0]>0)starts.unshift(0);
  const out=[];
  starts.forEach((s,si)=>{const seg=tok.slice(s,si+1<starts.length?starts[si+1]:tok.length);if(!seg.some(t=>t.x))return;
    let imp=null,kind,r,fixed=0;
    if(kindOf(seg[0].x)&&!impOf(seg[0].x)&&(seg.length<2||!kindOf(seg[1].x))){kind=seg[0].x;r=seg.slice(1)}else{imp=seg[0].x;kind=seg[1]?seg[1].x:'';r=seg.slice(2)}
    if(seg.some((t,i)=>i>0&&t.s===';'))fixed=1;
    let j=r.length;if(r.length>4){const pj=r.findIndex((p,i)=>i>2&&p.s==='|');if(pj>0)j=pj;else{while(j-1>2&&looksNames(r[j-1].x))j--;if(j===r.length)j=r.length-1}fixed=1}else if(r.length===4)j=3;
    const text=clean(r.slice(2,j).map((p,i)=>(i?(p.s===';'?'; ':' | '):'')+p.x).join(''));
    out.push({imp,kind,who:r[0]?r[0].x:'',where:r[1]?r[1].x:'',text,wit:r.slice(j).map(p=>p.x.replace(/\([^()]*\)/g,'').trim()).filter(Boolean).join(', '),n:(r.length?Math.min(r.length,4):0)+(seg.length-r.length)+(imp===null?1:0),fixed})});
  return out}
function parseMeta(raw){
  const out={events:[],learned:[],scene:null};
  const ev=metaLine(raw,'EVENTS');
  if(ev&&!NONE.test(ev))splitEvents(ev).forEach(e=>{if(e.n<5||!e.text)return;
    out.events.push({imp:impOf(e.imp)||3,kind:kindOf(e.kind)||'action',who:names(e.who),where:NONE.test(e.where)?'':clean(e.where).slice(0,80),text:e.text.slice(0,300),wit:names(e.wit)})});
  const ln=metaLine(raw,'LEARNED');
  if(ln&&!NONE.test(ln))ln.split(';').forEach(part=>{const k=part.indexOf(':');if(k<1)return;const who=clean(part.slice(0,k)),full=clean(part.slice(k+1)),m=full.match(/^(.*?)\s*\(([^()]*)\)\s*$/),text=(m?m[1]:full).trim().slice(0,300),how=m?m[2].trim().slice(0,120):'';if(who&&text&&who.length<=48&&!NONE.test(who))out.learned.push({who,text,how})});
  const sc=metaLine(raw,'SCENE');
  if(sc&&!NONE.test(sc)){const f=sc.split('|').map(x=>x.trim());out.scene={where:NONE.test(f[0]||'')?'':clean(f[0]).slice(0,80),who:names(String(f[1]||'').replace(/;/g,',')),when:NONE.test(f[2]||'')?'':clean(f[2]).slice(0,60)}}
  return out}
/* Diagnostics only: reports what was missing or malformed without changing what is stored. */
function validateMeta(raw){const d={block:!!metaBlock(raw),keys:{},events:{total:0,valid:0},learned:{total:0,valid:0},scene:{valid:false},issues:[],multi:false};
  ['EVENTS','LEARNED','SCENE'].forEach(k=>{const info={};const v=metaLine(raw,k,info);d.keys[k]=!!v;if(info.multi)d.multi=true;if(!v&&d.block)d.issues.push(k+' missing')});
  if(!d.block){d.issues.push('no [[META]] block');return d}
  if(String(raw||'').indexOf('[[META')<0)d.noMarker=true;
  const ev=metaLine(raw,'EVENTS');if(ev&&!NONE.test(ev))splitEvents(ev).forEach((e,n)=>{d.events.total++;
    const bad=[];let fixed=e.fixed;if(e.n<5)bad.push('has '+e.n+' of 6 fields');else{if(e.imp===null)fixed=1;else if(!/^[1-5]$/.test(e.imp)){if(impOf(e.imp))fixed=1;else bad.push('importance "'+e.imp.slice(0,12)+'"')}
      const k=clean(e.kind).toLowerCase();if(!KINDS.includes(k)){if(KALIAS[k])fixed=1;else bad.push('kind "'+clean(e.kind).slice(0,16)+'"')}if(!e.text)bad.push('empty description');if(!names(e.who).length)bad.push('no participants')}
    if(bad.length)d.issues.push('EVENTS #'+(n+1)+': '+bad.join(', '));else{d.events.valid++;if(fixed)d.recovered=(d.recovered||0)+1}});
  const ln=metaLine(raw,'LEARNED');if(ln&&!NONE.test(ln))ln.split(';').forEach((p,n)=>{if(!p.trim())return;d.learned.total++;const k=p.indexOf(':');if(k<1||!clean(p.slice(k+1)))d.issues.push('LEARNED #'+(n+1)+': not "Name: what"');else d.learned.valid++});
  const sc=metaLine(raw,'SCENE');if(sc&&!NONE.test(sc)){const f=sc.split('|');d.scene.valid=f.length>=3&&!!clean(f[0]);if(!d.scene.valid)d.issues.push('SCENE: has '+f.length+' of 3 fields')}
  return d}
function blankChar(){return {kernel:{core:'',voice:'',values:'',lines:[]},state:{mood:'',where:'',status:'alive',goal:''},knows:[],beliefs:[],mem:[]}}
function getP(o,p){for(const k of p){if(o==null)return undefined;o=o[k]}return o}
function setP(o,p,v){for(let i=0;i<p.length-1;i++){if(o[p[i]]==null||typeof o[p[i]]!=='object')o[p[i]]={};o=o[p[i]]}if(v===undefined)delete o[p[p.length-1]];else o[p[p.length-1]]=v}
const same=(a,b)=>JSON.stringify(a===undefined?null:a)===JSON.stringify(b===undefined?null:b);
/* Name resolution: "Corwin Hale (beyond the door)", "Corwin" and "Brother Aled" reuse an existing "Corwin Hale" / "Aled" when exactly one
   known capitalised name clearly matches (titles ignored). Descriptions ("a dock hand", "Vey Calder's man") are never merged. */
const TITLES=/^(brother|sister|father|mother|lady|lord|sir|dame|mr|mrs|ms|miss|mx|dr|doctor|master|mistress|captain|officer|madam|madame|king|queen|prince|princess|uncle|aunt|old|young)$/i;
const nameToks=n=>String(n).split(/\s+/).filter(w=>w&&!TITLES.test(w.replace(/\.$/,'')));
const properName=n=>{const w=String(n).split(/\s+/).filter(Boolean);return w.length>0&&w.length<=4&&w.every(x=>/^[A-Z][\w'\u2019.-]*$/.test(x))&&!/['\u2019]s$/.test(w[w.length-1])};
function resolveName(keys,raw){let n=clean(String(raw||'').replace(/\s*\([^)]*\)\s*$/,''));if(!n)return clean(raw);const ex=keys.find(k=>k.toLowerCase()===n.toLowerCase());if(ex)return ex;
  if(!properName(n))return n;const A=nameToks(n).map(w=>w.toLowerCase());if(!A.length)return n;
  const hits=keys.filter(k=>{if(!properName(k))return false;const B=nameToks(k).map(w=>w.toLowerCase());if(!B.length)return false;return A.every(w=>B.includes(w))||B.every(w=>A.includes(w))});
  return hits.length===1?hits[0]:n}
function buildDelta(mem,p,ctx){
  mem=mem||init();p=p||{events:[],learned:[],scene:null};ctx=ctx||{};
  const t=Number(ctx.t)||0,mx={v:1,t,tid:ctx.tid||'',ev:[],fa:[],nc:[],ml:[],kn:[],set:[],seq:[mem.seq,mem.seq]};let seq=mem.seq;const nid=x=>x+(++seq);
  const seen=Object.keys(mem.chars||{}),rn=n=>{const r=resolveName(seen,n);if(r&&!seen.includes(r))seen.push(r);return r};
  p={events:(p.events||[]).map(e=>Object.assign({},e,{who:(e.who||[]).map(rn).filter((x,i,A)=>A.indexOf(x)===i),wit:(e.wit||[]).map(rn).filter((x,i,A)=>A.indexOf(x)===i)})),learned:(p.learned||[]).map(l=>Object.assign({},l,{who:rn(l.who)})),scene:p.scene?Object.assign({},p.scene,{who:(p.scene.who||[]).map(rn).filter((x,i,A)=>A.indexOf(x)===i)}):p.scene};
  const has=n=>(mem.chars&&mem.chars[n])||mx.nc.some(c=>c.n===n);
  const ensure=n=>{if(n&&!has(n))mx.nc.push({n,o:blankChar()})};
  const sc=p.scene;
  (p.events||[]).forEach(e=>{
    const ppl=x=>(x||[]).map(n=>String(n).toLowerCase()).sort().join('|');const dup=(mem.events||[]).concat(mx.ev).some(x=>Math.abs((x.t||0)-t)<=6&&x.kind===e.kind&&ppl(x.who)===ppl(e.who)&&overlap(x.text,e.text)>=0.85);if(dup)return;
    const ev={id:nid('e'),t,ch:Number(ctx.ch)||0,tid:ctx.tid||'',when:(sc&&sc.when)||'',where:e.where||(sc&&sc.where)||'',who:e.who.slice(0,8),wit:e.wit.slice(0,8),kind:e.kind,imp:e.imp,text:e.text,open:!!OPEN_KINDS[e.kind],src:'meta'};
    mx.ev.push(ev);ev.who.concat(ev.wit).forEach(n=>{ensure(n);if(!mx.ml.some(l=>l[0]===n&&l[1]===ev.id))mx.ml.push([n,ev.id])})});
  (p.learned||[]).forEach(l=>{
    const pool=(mem.facts||[]).concat(mem.secrets||[],mx.fa);let f=pool.find(x=>overlap(x.text,l.text)>=0.9);
    if(!f){f={id:nid('f'),text:l.text,from:mx.ev.map(e=>e.id),since:t,until:null,sticky:false,conf:null,src:'learned',tid:ctx.tid||''};mx.fa.push(f)}
    ensure(l.who);const ch=mem.chars&&mem.chars[l.who];if(!(ch&&(ch.knows||[]).includes(f.id))&&!mx.kn.some(k=>k[0]===l.who&&k[1]===f.id))mx.kn.push([l.who,f.id,l.how||''])});
  if(sc){const pv=mem.scene||{},nv={where:sc.where||pv.where||'',who:sc.who.slice(0,10),when:sc.when||pv.when||''};mx.set.push([['scene'],mem.scene===undefined?null:clone(mem.scene),nv]);
    if(sc.where)sc.who.forEach(n=>{ensure(n);const old=mem.chars&&mem.chars[n]?getP(mem.chars[n],['state','where']):'';if(old!==sc.where)mx.set.push([['chars',n,'state','where'],old===undefined?'':old,sc.where])})}
  mx.seq=[mem.seq,seq];return mx}
function apply(mem,mx){
  if(!mem||!mx)return mem;mem.events=mem.events||[];mem.facts=mem.facts||[];mem.chars=mem.chars||{};
  mem.seq=Math.max(Number(mem.seq)||0,(mx.seq&&mx.seq[1])||0);
  (mx.nc||[]).forEach(c=>{if(!mem.chars[c.n])mem.chars[c.n]=clone(c.o)});
  (mx.ev||[]).forEach(e=>{if(!mem.events.some(x=>x.id===e.id))mem.events.push(clone(e))});
  mem.events.sort((a,b)=>(a.t||0)-(b.t||0));
  (mx.fa||[]).forEach(f=>{if(!mem.facts.some(x=>x.id===f.id))mem.facts.push(clone(f))});
  (mx.ml||[]).forEach(([n,id])=>{const c=mem.chars[n];if(c){c.mem=c.mem||[];if(!c.mem.includes(id))c.mem.push(id)}});
  (mx.kn||[]).forEach(([n,id])=>{const c=mem.chars[n];if(c){c.knows=c.knows||[];if(!c.knows.includes(id))c.knows.push(id)}});
  (mx.set||[]).forEach(([p,,nv])=>setP(mem,p,clone(nv===undefined?null:nv)));
  return mem}
function undo(mem,mx,later){
  if(!mem||!mx)return mem;const evIds=new Set((mx.ev||[]).map(e=>e.id)),faIds=new Set((mx.fa||[]).map(f=>f.id));
  mem.events=(mem.events||[]).filter(e=>!evIds.has(e.id));mem.facts=(mem.facts||[]).filter(f=>!faIds.has(f.id));
  (mx.ml||[]).forEach(([n,id])=>{const c=mem.chars&&mem.chars[n];if(c&&c.mem)c.mem=c.mem.filter(x=>x!==id)});
  (mx.kn||[]).forEach(([n,id])=>{const c=mem.chars&&mem.chars[n];if(c&&c.knows)c.knows=c.knows.filter(x=>x!==id)});
  (mx.set||[]).slice().reverse().forEach(([p,ov,nv])=>{if(same(getP(mem,p),nv))setP(mem,p,ov===null&&p.length===1?undefined:clone(ov));
    else (later||[]).forEach(L=>{const e=L&&(L.set||[]).find(x=>same(x[0],p)&&same(x[1],nv));if(e)e[1]=clone(ov)})});
  (mx.nc||[]).forEach(c=>{const x=mem.chars&&mem.chars[c.n];if(x&&same(x,c.o))delete mem.chars[c.n]});
  return mem}
function record(mem,p,ctx){const mx=buildDelta(mem,p,ctx);apply(mem,mx);return mx}
function shiftTurns(mem,after,d){if(!mem)return mem;(mem.events||[]).forEach(e=>{if(e.t>after)e.t+=d});(mem.facts||[]).forEach(f=>{if(f.since>after)f.since+=d});return mem}
function empty(mx){return !mx||!((mx.ev||[]).length||(mx.fa||[]).length||(mx.nc||[]).length||(mx.kn||[]).length||(mx.set||[]).length)}
root.SFMemory=Object.freeze({init,migrate,relHistory,timeline,charView,checks,stats,integrity,parseMeta,validateMeta,splitEvents,metaStart,buildDelta,apply,undo,record,shiftTurns,empty,resolveName});
})(typeof window!=='undefined'?window:globalThis);
