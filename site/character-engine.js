/* Story Forge living characters engine (roadmap phase 6, contract: docs/CHARACTERS-API.md). Pure functions, no network, no AI requests.
 * Relationships: directional records 'rel:A>B' with trust, affection, respect, familiarity, rivalry (-100..100; familiarity and rivalry 0..100).
 *   value = base (player-set, default 0) + sum of changes from events that still exist. rebuild() recomputes from scratch, so a regenerated,
 *   deleted or branched-away reply leaves no trace (regeneration and branch safe). At most LIMIT per event per dimension.
 * Journals separate did / witnessed / learned / believes / rumor / feels / intends, with provenance and whether the player character knows it.
 * Personality: warnings are advisory; recorded development or a current mood turns a warning into 'growth' or 'mood' instead of 'voice'.
 * NPC agendas: prioritised goals (short/long term, competing), schedules and commitments, advanced by story days only.
 */
(function(root){
'use strict';
const arr=x=>Array.isArray(x)?x:[];const low=x=>String(x||'').toLowerCase();const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const DIMS=['trust','affection','respect','familiarity','rivalry'],RANGE={trust:[-100,100],affection:[-100,100],respect:[-100,100],familiarity:[0,100],rivalry:[0,100]},LIMIT=15;
/* cues: [pattern, change to target's view of actor, change to actor's view of target, label] */
const CUES=[
 [/\b(sav(e|es|ed|ing)|rescu\w*|protect\w*|shield\w*)\b/,{trust:8,affection:6,respect:4},{affection:2},'protected or saved'],
 [/\b(help\w*|support\w*|comfort\w*|heal\w*|tend\w*)\b/,{trust:4,affection:4},{affection:1},'helped'],
 [/\b(thank\w*|prais\w*|compliment\w*|apologi\w*)\b/,{affection:3,respect:2},{},'kind words'],
 [/\b(confid\w*|shar\w* (a |the |his |her |their )?secret|trust\w* (him|her|them))\b/,{trust:5,affection:3},{trust:3},'shared a confidence'],
 [/\b(train\w*|teach\w*|taught|mentor\w*)\b/,{respect:4,trust:2},{respect:1},'taught or trained'],
 [/\b(betray\w*|sold out|double[- ]cross\w*)\b/,{trust:-15,affection:-10},{},'betrayal'],
 [/\b(li(e|es|ed)|lying|deceiv\w*|trick\w*)\b/,{trust:-6},{},'deception'],
 [/\b(attack\w*|hit|hits|struck|stab\w*|wound\w*|hurt\w*|injur\w*)\b/,{trust:-8,affection:-8},{},'harm'],
 [/\b(insult\w*|mock\w*|humiliat\w*|threat\w*|yell\w* at|shout\w* at)\b/,{affection:-5,respect:-2},{},'hostile words'],
 [/\b(argu\w*|quarrel\w*|clash\w*|disagree\w*)\b/,{affection:-2},{affection:-2},'argument'],
 [/\b(beat|defeat\w*|outperform\w*|outscor\w*|won against|compet\w*|rival\w*)\b/,{respect:4,rivalry:6},{rivalry:4},'rivalry']];
const KIND={bond:[{trust:5,affection:5},{trust:5,affection:5},'bond'],betrayal:[{trust:-15,affection:-10},{},'betrayal'],promise:[{trust:3},{},'promise'],injury:[{trust:-6,affection:-6},{},'harm']};
const cap=o=>{const r={};Object.keys(o).forEach(k=>{if(o[k])r[k]=clamp(o[k],-LIMIT,LIMIT)});return r};
/* deltas(event) -> [{from, to, change, why}]. who[0] = actor, other participants = targets. Every shared event adds familiarity both ways. */
function deltas(e){const who=arr(e.who);if(who.length<2)return[];const a=who[0],T=low(e.text),out=[];let tv={},av={},why=[];
  if(KIND[e.kind]){const k=KIND[e.kind];tv=Object.assign({},k[0]);av=Object.assign({},k[1]);why.push(k[2])}
  CUES.forEach(([re,t,s,l])=>{if(re.test(T)){Object.keys(t).forEach(k=>tv[k]=(tv[k]||0)+t[k]);Object.keys(s).forEach(k=>av[k]=(av[k]||0)+s[k]);why.push(l)}});
  tv.familiarity=(tv.familiarity||0)+2;av.familiarity=(av.familiarity||0)+2;if(!why.length)why.push('time together');tv=cap(tv);av=cap(av);
  who.slice(1).forEach(b=>{out.push({from:b,to:a,change:tv,why:why.join(', ')});out.push({from:a,to:b,change:av,why:why.join(', ')})});return out}
const blank=(id,a,b)=>({id,a,b,kinds:[],base:{},trust:0,affection:0,respect:0,familiarity:0,rivalry:0,history:[],private:false,knownBy:[]});
function recompute(r){DIMS.forEach(k=>{let v=Number((r.base||{})[k])||0;arr(r.history).forEach(h=>{v+=Number((h.change||{})[k])||0});r[k]=clamp(v,RANGE[k][0],RANGE[k][1])});return r}
/* rebuild(rels, events, o) -> {rels, applied, removed}. Keeps player base values, kinds, privacy; drops changes from events that no longer exist; applies new ones. */
function rebuild(rels,events,o){o=o||{};const idOf=o.idOf||(n=>n),R=JSON.parse(JSON.stringify(arr(rels))).map(r=>Object.assign(blank(r.id,r.a,r.b),r,{base:r.base||{}})),byId=new Map(R.map(r=>[r.id,r]));
  const E=arr(events).map(e=>Object.assign({},e,{who:arr(e.who).map(idOf).filter(Boolean)})),live=new Set(E.map(e=>e.id));let removed=0;
  R.forEach(r=>{const keep=arr(r.history).filter(h=>live.has(h.event));removed+=arr(r.history).length-keep.length;r.history=keep});
  const applied=[];E.slice().sort((x,y)=>(x.t||0)-(y.t||0)||(x.id<y.id?-1:1)).forEach(e=>deltas(e).forEach(d=>{const id='rel:'+d.from+'>'+d.to;let r=byId.get(id);if(!r){r=blank(id,d.from,d.to);byId.set(id,r);R.push(r)}
    if(r.history.some(h=>h.event===e.id))return;r.history.push({event:e.id,t:e.t??null,change:d.change,why:d.why});applied.push({id,event:e.id,change:d.change})}));
  R.forEach(recompute);return{rels:R,applied,removed}}
const evolve=rebuild;
/* setBase(rels, a, b, patch) -> {ok, applied, reason, rels, prev}. Player-approved values/kinds/privacy; event history is kept. */
function setBase(rels,a,b,patch){if(!a||!b||a===b)return{ok:false,applied:false,reason:'needs two different characters',rels};const p=patch||{},bad=Object.keys(p).filter(k=>!DIMS.includes(k)&&!['kinds','private','knownBy'].includes(k));
  if(bad.length)return{ok:false,applied:false,reason:'unknown field '+bad[0],rels};const R=JSON.parse(JSON.stringify(arr(rels))),id='rel:'+a+'>'+b;let r=R.find(x=>x.id===id);const prev=r?JSON.parse(JSON.stringify(r)):null;
  if(!r){r=blank(id,a,b);R.push(r)}r.base=Object.assign({},r.base);DIMS.forEach(k=>{if(k in p){const cur=r[k]-(Number(r.base[k])||0);r.base[k]=clamp(Number(p[k])||0,RANGE[k][0],RANGE[k][1])-cur}});
  ['kinds','private','knownBy'].forEach(k=>{if(k in p)r[k]=p[k]});recompute(r);if(prev&&JSON.stringify(prev)===JSON.stringify(r))return{ok:false,applied:false,reason:'unchanged',rels};return{ok:true,applied:true,reason:null,rels:R,prev:{id,record:prev}}}
function history(rels,a,b){const r=arr(rels).find(x=>x.id==='rel:'+a+'>'+b);return r?arr(r.history).slice():[]}
function label(r){if(!r)return'stranger';const t=r.trust||0,f=r.affection||0;if(t<=-40||f<=-40)return'hostile';if((r.rivalry||0)>=40&&t>-15)return'rival';if(t>=60&&f>=60)return'devoted';if(t>=35&&f>=35)return'close';if(f>=20||t>=20)return'friendly';if(t<=-15||f<=-15)return'wary';if((r.familiarity||0)<4)return'stranger';return'neutral'}

/* journal(view, name, o) -> [{t, kind, text, role, source, playerKnows}] from a memory v2 view.
 * o = {player: name, rels: directional records, npc: {goals}} — feels and intends come from these. */
function journal(view,name,o){o=o||{};const n=low(name),R=arr(view&&view.records).filter(r=>!r.deleted),out=[];const is=x=>low(x)===n||low(x).split(' ')[0]===n.split(' ')[0];
  const P=low(o.player),pIs=x=>P&&(low(x)===P||low(x).split(' ')[0]===P.split(' ')[0]);const pChar=R.find(r=>r.layer==='character'&&arr(r.who).some(pIs)),pKnows=new Set(pChar?arr(pChar.links).filter(l=>l.startsWith('knows:')).map(l=>l.slice(6)):[]);
  const pSaw=e=>arr(e.who).some(pIs)||arr(e.links).some(l=>l.startsWith('wit:')&&pIs(l.slice(4)));
  R.filter(r=>r.layer==='episodic').forEach(e=>{if(arr(e.who).some(is))out.push({t:e.t,kind:e.kind,text:e.text,role:'did',source:e.id,playerKnows:pSaw(e)});else if(arr(e.links).some(l=>l.startsWith('wit:')&&is(l.slice(4))))out.push({t:e.t,kind:e.kind,text:e.text,role:'witnessed',source:e.id,playerKnows:pSaw(e)})});
  const c=R.find(r=>r.layer==='character'&&arr(r.who).some(is));if(c){const L=arr(c.links),kn=new Set(L.filter(l=>l.startsWith('knows:')).map(l=>l.slice(6))),bl=new Set(L.filter(l=>l.startsWith('believes:')).map(l=>l.slice(9)));
    R.filter(r=>r.layer==='semantic'&&(kn.has(r.id)||bl.has(r.id))).forEach(f=>{const rumor=f.kind==='rumor'||(f.conf!=null&&f.conf<0.5);out.push({t:f.since??f.t??null,kind:f.kind,text:f.text,role:bl.has(f.id)?'believes':rumor?'rumor':'learned',source:f.id,playerKnows:pKnows.has(f.id)})})}
  arr(o.rels).filter(r=>is(r.a)).forEach(r=>out.push({t:r.history&&r.history.length?r.history[r.history.length-1].t:null,kind:'feeling',text:'toward '+r.b+': '+label(r)+' (trust '+r.trust+', affection '+r.affection+')',role:'feels',source:r.id,playerKnows:false}));
  arr(o.npc&&o.npc.goals).forEach(g=>out.push({t:null,kind:'goal',text:typeof g==='string'?g:g.text,role:'intends',source:'agenda',playerKnows:false}));
  return out.sort((x,y)=>(x.t??-1)-(y.t??-1))}

/* agenda(npc, fromDay, toDay) -> {name, where, doing, goals (by priority), tensions, commitments, developments[{day, text}]}. Deterministic, no AI. */
const goalOf=g=>typeof g==='string'?{text:g,priority:3,term:'long'}:Object.assign({priority:3,term:'long'},g);
function agenda(npc,fromDay,toDay){const S=arr(npc&&npc.schedule).slice().sort((a,b)=>a.day-b.day),f=Number(fromDay)||0,t=Number(toDay)||0,G=arr(npc&&npc.goals).map(goalOf).sort((a,b)=>b.priority-a.priority);
  const cur=S.filter(x=>x.day<=t).pop()||null,devs=S.filter(x=>x.day>f&&x.day<=t).map(x=>({day:x.day,text:(npc.name||'Someone')+' '+(x.doing||'moves on')+(x.where?' at '+x.where:'')+'.'}));
  if(t>f&&G.length&&!devs.length)devs.push({day:t,text:npc.name+' keeps working toward: '+G[0].text+'.'});
  const tensions=[];G.forEach((g,i)=>arr(g.conflictsWith).forEach(x=>{const o=G.find(h=>h.text===x||h.id===x);if(o&&G.indexOf(o)>i)tensions.push({a:g.text,b:o.text,leaning:g.text})}));
  return{name:npc&&npc.name,where:cur?cur.where:'',doing:cur?cur.doing:'',goals:G,tensions,commitments:S.filter(x=>x.day>t).slice(0,3),developments:devs}}

/* checkVoice(identity, reply, o) -> [{kind:'voice'|'growth'|'mood', name, text}] advisory only. o = {developments:[text], mood:text} */
const W=s=>(String(s).match(/\S+/g)||[]).length;
function linesOf(name,reply){const first=String(name||'').split(' ')[0];if(!first)return[];const out=[];const T=String(reply||'');let m;
  const re1=new RegExp('(?:^|\\n)\\s*'+first+'(?:\\s+\\w+)?\\s*\\|\\s*"?([^\\n]+)','gi');while((m=re1.exec(T)))out.push(m[1]);
  const re2=new RegExp('"([^"]{2,400})"\\s*,?\\s*'+first+'\\s+(?:said|says|shouted|whispered|replied|snapped|yelled|asked)','gi');while((m=re2.exec(T)))out.push(m[1]);
  const re3=new RegExp(first+'\\s+(?:said|says|shouted|whispered|replied|snapped|yelled|asked)[^"]{0,20}"([^"]{2,400})"','gi');while((m=re3.exec(T)))out.push(m[1]);return out}
const GROWTH={slang:/\b(casual|relax\w*|loosen\w*|slang|less formal)\b/,long:/\b(talkative|opens? up|opened up|more open|chatty)\b/,shout:/\b(angr\w*|temper|loud\w*|snaps?|furious|fierce)\b/};
function checkVoice(id,reply,o){o=o||{};if(!id||!id.name)return[];const sp=low((id.speech||{}).tone+' '+(id.speech||{}).vocabulary),core=low((id.core||{}).personality+' '+(id.core||{}).temperament),dev=low(arr(o.developments).join(' ')),mood=low(o.mood),out=[];
  linesOf(id.name,reply).forEach(l=>{const hits=[];const caps=(l.match(/\b[A-Z]{3,}\b/g)||[]).length,bang=(l.match(/!/g)||[]).length,slang=(l.match(/\b(gonna|wanna|lol|dude|bro|yeah|nah|ain't|kinda|sorta)\b/gi)||[]).length;
    if(/\b(formal|precise|courtly|polite)\b/.test(sp)&&slang>=1)hits.push(['slang','casual slang from a formal speaker']);
    if(/\b(clipped|terse|few words|quiet)\b/.test(sp)&&W(l)>45)hits.push(['long','very long speech from a terse speaker']);
    if(/\b(shy|quiet|reserved|calm|patient)\b/.test(core)&&(caps>=2||bang>=3))hits.push(['shout','shouting from a '+((core.match(/\b(shy|quiet|reserved|calm|patient)\b/)||[])[1])+' character']);
    hits.forEach(([k,why])=>{const kind=GROWTH[k].test(dev)?'growth':(k==='shout'&&GROWTH.shout.test(mood))?'mood':'voice';out.push({kind,name:id.name,text:(kind==='growth'?'consistent with recorded development: ':kind==='mood'?'explained by current mood: ':'')+why+': "'+l.slice(0,100)+'"'})})});return out}

root.SFChar=Object.freeze({DIMS,LIMIT,deltas,rebuild,evolve,setBase,recompute,history,label,journal,agenda,checkVoice,linesOf});
})(typeof window!=='undefined'?window:globalThis);
