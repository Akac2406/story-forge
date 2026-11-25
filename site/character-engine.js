/* Story Forge living characters engine (roadmap phase 6). Pure functions, no network, no AI requests.
 * - evolve: directional relationships change from recorded events, with evidence and per-event limits (idempotent by event id).
 * - journal: what one character experienced, witnessed, knows and feels, from the memory v2 view.
 * - agenda: NPC goals and schedules advanced by story days, producing off-screen developments deterministically.
 * - checkVoice: flags lines that clash with a character's established speech or temperament.
 * Relationship records follow FANFIC-CONTRACT section 6: {id:'rel:A>B', a, b, kinds[], trust, affection, respect, history[], private, knownBy[]}.
 */
(function(root){
'use strict';
const arr=x=>Array.isArray(x)?x:[];const low=x=>String(x||'').toLowerCase();const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
/* Event cues: [pattern, change for target's view of actor, change for actor's view of target, label] on trust/affection/respect */
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
 [/\b(beat|defeat\w*|outperform\w*|outscor\w*|won against)\b/,{respect:4,affection:-1},{},'rivalry']];
const KIND={bond:[{trust:5,affection:5},{trust:5,affection:5},'bond'],betrayal:[{trust:-15,affection:-10},{},'betrayal'],promise:[{trust:3},{},'promise'],injury:[{trust:-6,affection:-6},{},'harm']};
const LIMIT=15;
/* deltas(event) -> [{from, to, change, why}] directional. who[0] is the actor; every other participant is a target. */
function deltas(e){const who=arr(e.who);if(who.length<2)return[];const a=who[0],T=low(e.text),out=[];let tv={},av={},why=[];
  if(KIND[e.kind]){const k=KIND[e.kind];tv=Object.assign({},k[0]);av=Object.assign({},k[1]);why.push(k[2])}
  CUES.forEach(([re,t,s,l])=>{if(re.test(T)){Object.keys(t).forEach(k=>tv[k]=(tv[k]||0)+t[k]);Object.keys(s).forEach(k=>av[k]=(av[k]||0)+s[k]);why.push(l)}});
  const cap=o=>{const r={};Object.keys(o).forEach(k=>{if(o[k])r[k]=clamp(o[k],-LIMIT,LIMIT)});return r};tv=cap(tv);av=cap(av);
  if(!Object.keys(tv).length&&!Object.keys(av).length)return[];
  who.slice(1).forEach(b=>{if(Object.keys(tv).length)out.push({from:b,to:a,change:tv,why:why.join(', ')});if(Object.keys(av).length)out.push({from:a,to:b,change:av,why:why.join(', ')})});return out}
/* evolve(rels, events, o) -> {rels, applied:[...]} new array; each event applied at most once per direction (history holds event ids). */
function evolve(rels,events,o){o=o||{};const R=JSON.parse(JSON.stringify(arr(rels))),byId=new Map(R.map(r=>[r.id,r])),applied=[],idOf=o.idOf||(n=>n);
  arr(events).slice().sort((x,y)=>(x.t||0)-(y.t||0)||(x.id<y.id?-1:1)).forEach(e=>{const ev=Object.assign({},e,{who:arr(e.who).map(idOf).filter(Boolean)});
    deltas(ev).forEach(d=>{const id='rel:'+d.from+'>'+d.to;let r=byId.get(id);if(!r){r={id,a:d.from,b:d.to,kinds:[],trust:0,affection:0,respect:0,history:[],private:false,knownBy:[]};byId.set(id,r);R.push(r)}
      if(arr(r.history).some(h=>(h.event||h)===e.id))return;Object.keys(d.change).forEach(k=>r[k]=clamp((Number(r[k])||0)+d.change[k],-100,100));
      r.history=arr(r.history).concat([{event:e.id,t:e.t??null,change:d.change,why:d.why}]);applied.push({id,event:e.id,change:d.change})})});
  return{rels:R,applied}}
function history(rels,a,b){const r=arr(rels).find(x=>x.id==='rel:'+a+'>'+b);return r?arr(r.history).map(h=>typeof h==='string'?{event:h}:h):[]}
function label(r){if(!r)return'stranger';const t=r.trust||0,f=r.affection||0;if(t<=-40||f<=-40)return'hostile';if(t>=60&&f>=60)return'devoted';if(t>=35&&f>=35)return'close';if(f>=20||t>=20)return'friendly';if(t<=-15||f<=-15)return'wary';return'neutral'}

/* journal(view, name) -> [{t, kind, text, role}] from a memory v2 view (SFMem2.build/apply). role: did | witnessed | learned | feels */
function journal(view,name){const n=low(name),R=arr(view&&view.records).filter(r=>!r.deleted),out=[];const is=w=>low(w)===n||low(w).split(' ')[0]===n.split(' ')[0];
  R.filter(r=>r.layer==='episodic').forEach(e=>{if(arr(e.who).some(is))out.push({t:e.t,kind:e.kind,text:e.text,role:'did'});else if(arr(e.links).some(l=>l.startsWith('wit:')&&is(l.slice(4))))out.push({t:e.t,kind:e.kind,text:e.text,role:'witnessed'})});
  const c=R.find(r=>r.layer==='character'&&arr(r.who).some(is));if(c){const ids=new Set(arr(c.links).filter(l=>l.startsWith('knows:')).map(l=>l.slice(6)));R.filter(r=>r.layer==='semantic'&&ids.has(r.id)).forEach(f=>out.push({t:f.since??f.t??null,kind:'fact',text:f.text,role:'learned'}))}
  R.filter(r=>r.layer==='relationship'&&arr(r.who).some(is)).forEach(r=>out.push({t:r.t,kind:'bond',text:r.text,role:'feels'}));
  return out.sort((x,y)=>(x.t??-1)-(y.t??-1))}

/* agenda(npc, fromDay, toDay) -> {name, where, doing, goals, developments:[{day, text}]} — deterministic, no AI. npc = {name, goals[], schedule[{day, where, doing}]} */
function agenda(npc,fromDay,toDay){const S=arr(npc&&npc.schedule).slice().sort((a,b)=>a.day-b.day),f=Number(fromDay)||0,t=Number(toDay)||0;
  const cur=S.filter(x=>x.day<=t).pop()||null,devs=S.filter(x=>x.day>f&&x.day<=t).map(x=>({day:x.day,text:(npc.name||'Someone')+' '+(x.doing||'moves on')+(x.where?' at '+x.where:'')+'.'}));
  if(t>f&&arr(npc&&npc.goals).length&&!devs.length)devs.push({day:t,text:npc.name+' keeps working toward: '+npc.goals[0]+'.'});
  return{name:npc&&npc.name,where:cur?cur.where:'',doing:cur?cur.doing:'',goals:arr(npc&&npc.goals),developments:devs}}

/* checkVoice(id, reply) -> [{kind:'voice', name, text}] for lines spoken by the character that clash with their speech/temperament. id = {name, speech:{tone, vocabulary}, core:{personality, temperament}} */
const W=s=>(String(s).match(/\S+/g)||[]).length;
function linesOf(name,reply){const first=String(name||'').split(' ')[0];if(!first)return[];const out=[];const T=String(reply||'');
  const re1=new RegExp('(?:^|\\n)\\s*'+first+'(?:\\s+\\w+)?\\s*\\|\\s*"?([^\\n]+)','gi');let m;while((m=re1.exec(T)))out.push(m[1]);
  const re2=new RegExp('"([^"]{2,400})"\\s*,?\\s*'+first+'\\s+(?:said|says|shouted|whispered|replied|snapped|yelled|asked)','gi');while((m=re2.exec(T)))out.push(m[1]);
  const re3=new RegExp(first+'\\s+(?:said|says|shouted|whispered|replied|snapped|yelled|asked)[^"]{0,20}"([^"]{2,400})"','gi');while((m=re3.exec(T)))out.push(m[1]);return out}
function checkVoice(id,reply){if(!id||!id.name)return[];const sp=low((id.speech||{}).tone+' '+(id.speech||{}).vocabulary),core=low((id.core||{}).personality+' '+(id.core||{}).temperament),out=[];
  linesOf(id.name,reply).forEach(l=>{const why=[];const caps=(l.match(/\b[A-Z]{3,}\b/g)||[]).length,bang=(l.match(/!/g)||[]).length,slang=(l.match(/\b(gonna|wanna|lol|dude|bro|yeah|nah|ain't|kinda|sorta)\b/gi)||[]).length;
    if(/\b(formal|precise|courtly|polite)\b/.test(sp)&&slang>=1)why.push('casual slang from a formal speaker');
    if(/\b(clipped|terse|few words|quiet)\b/.test(sp)&&W(l)>45)why.push('very long speech from a terse speaker');
    if(/\b(shy|quiet|reserved|calm|patient)\b/.test(core)&&(caps>=2||bang>=3))why.push('shouting from a '+((core.match(/\b(shy|quiet|reserved|calm|patient)\b/)||[])[1])+' character');
    if(why.length)out.push({kind:'voice',name:id.name,text:why.join('; ')+': "'+l.slice(0,100)+'"'})});return out}

root.SFChar=Object.freeze({deltas,evolve,history,label,journal,agenda,checkVoice,linesOf,LIMIT});
})(typeof window!=='undefined'?window:globalThis);
