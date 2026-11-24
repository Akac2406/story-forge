/* Story Forge canon & instruction engine (v87).
   Pure functions: no DOM, no network, no paid calls. index.html calls these while building the narrator prompt
   and when a reply's metadata is applied. All data it reads is additive and optional, so old saves work unchanged.

   Shared structures (agreed with the UI side):
   - Canon Bible = st.entries [{k, t, a, id?, kind?, lock?, pri?, after?, before?, src?, aliases?}]
       k: comma-separated keys (first one is the display name); t: text; a: always include (legacy);
       lock: always included verbatim, never trimmed; pri 1-3 (3 = most important).
   - Notes: DB.notes / se.notes [{id, text, pri:"must"|"should"|"style", scope:{type, value}, on, created}]
       scope.type: always | keyword | character | chapter | turns. Legacy DB.globalNote / se.note strings
       are read as one must/always note each and never rewritten.
   - Canon mode: se.canonMode ?? st.canonMode ?? derived from follow: strict | adaptive | au | creative.
   - Divergences: se.divergences [{id, turn, tid, kind:"player-choice"|"drift"|"au", entry, text, status}].
*/
(function(root){'use strict';
const MODES=["strict","adaptive","au","creative"];
const str=(v,n)=>typeof v==="string"?v.trim().slice(0,n||4000):"";
const lc=s=>String(s||"").toLowerCase();
const esc=s=>s.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");

/* ---------- canon mode ---------- */
function mode(se,st){
  const m=(se&&se.canonMode)||(st&&st.canonMode);
  if(MODES.includes(m))return m;
  const f=String((se&&se.follow)||(st&&st.follow)||"strict").trim();
  if(f==="strict"||!f)return "strict";
  return "adaptive"; // "loose" and custom follow text both read as adaptive; the follow text itself is still sent
}

/* ---------- word matching ---------- */
// Whole-word match that also accepts simple plural/possessive endings. "Ann" does not match "Anna".
function keyRe(k){
  k=String(k||"").trim();if(k.length<2)return null;
  const body=esc(k).replace(/\s+/g,"\\s+");
  return new RegExp("(^|[^\\p{L}\\p{N}])"+body+"(?:'s|’s|s|es)?(?=$|[^\\p{L}\\p{N}])","iu");
}
const RE_CACHE=new Map();
function hasKey(text,k){
  let re=RE_CACHE.get(k);if(re===undefined){re=keyRe(k);RE_CACHE.set(k,re);if(RE_CACHE.size>4000)RE_CACHE.clear()}
  return !!(re&&re.test(text));
}
function keysOf(e){
  const ks=String(e&&e.k||"").split(",").map(x=>x.trim()).filter(Boolean);
  const al=Array.isArray(e&&e.aliases)?e.aliases:String(e&&e.aliases||"").split(",");
  return [...new Set(ks.concat(al.map(x=>String(x).trim()).filter(Boolean)))];
}
const nameOf=e=>String(e&&e.k||"").split(",")[0].trim();
const idOf=(e,i)=>String((e&&e.id)||("entry-"+i));

/* ---------- canon retrieval ---------- */
/* Scores every Canon Bible entry and fills the budget by score instead of list order.
   Locked entries always go in (separate, untrimmed). Returns {locked, text, included, dropped}. */
function lore(st,se,hist,action,opts){
  opts=opts||{};const es=Array.isArray(st&&st.entries)?st.entries:[];
  const budget=opts.budget||7000,first=!hist||!hist.length;
  const present=(opts.present||[]).map(lc);
  const last=hist&&hist.length?String(hist[hist.length-1].text||""):"";
  const recent=(hist||[]).slice(-3).map(t=>t.text||"").join("\n");
  const act=String(action||"");
  const pinned=[],cand=[],dropped=[];
  es.forEach((e,i)=>{
    const t=str(e&&e.t,4000);if(!t)return;
    const id=idOf(e,i),name=nameOf(e),ks=keysOf(e);
    const when=[str(e.after,80)?"applies from: "+str(e.after,80):"",str(e.before,80)?"until: "+str(e.before,80):""].filter(Boolean).join("; ");
    const tt=when?t+" ["+when+"]":t;
    if(e.lock){pinned.push({id,name,t:(when?str(e.t,100000)+" ["+when+"]":str(e.t,100000))});return}
    let score=0,why=[];
    if(e.a){score+=50;why.push("always")}
    for(const k of ks){
      if(hasKey(act,k)){score+=12;why.push("action:"+k);break}
    }
    for(const k of ks){if(hasKey(last,k)){score+=8;why.push("last turn");break}}
    for(const k of ks){if(hasKey(recent,k)){score+=4;why.push("recent");break}}
    if(present.length&&ks.some(k=>present.includes(lc(k)))){score+=10;why.push("in scene")}
    if(first&&opts.setting&&ks.some(k=>hasKey(opts.setting,k))){score+=3;why.push("setting")}
    if(score>0)score+=(Number(e.pri)||0)*2;
    if(score>0)cand.push({id,name,t:tt,score,why});else dropped.push({id,reason:"not relevant to this scene"});
  });
  cand.sort((a,b)=>b.score-a.score);
  const out=[],included=[];let used=0;
  for(const c of cand){
    if(used+c.t.length>budget){dropped.push({id:c.id,reason:"over budget",score:c.score});continue}
    used+=c.t.length;out.push("- "+(c.name?c.name+": ":"")+c.t);included.push({id:c.id,why:c.why.join(", ")});
  }
  return {locked:pinned.map(p=>"- "+(p.name?p.name+": ":"")+p.t).join("\n"),lockedIds:pinned.map(p=>p.id),
          text:out.join("\n"),included,dropped};
}

/* ---------- canon extraction (suggestions only; the player approves them in the Canon Bible) ---------- */
/* chunks: array of source-text passages. Finds names and terms that recur and are not yet in the Bible,
   and returns draft entries {k, t, kind:"term", src:"source", count} with the clearest sentence as text. */
const STOP=new Set("The A An And But Or If When Then There This That These Those He She It They We You I His Her Its Their Our Your My Mr Mrs Ms Dr Chapter Part Book One Two Three Yes No Oh What Who Why How Where After Before Even Still Just Now Then".split(" "));
function suggestEntries(chunks,entries,opts){
  opts=opts||{};const have=new Set();(entries||[]).forEach(e=>keysOf(e).forEach(k=>have.add(lc(k))));
  const count=new Map(),best=new Map();
  for(const c of chunks||[]){
    const text=String(c||"");const sents=text.split(/(?<=[.!?])\s+/);
    for(const sen of sents){
      const re=/\b([A-Z][\p{L}'’-]{1,}(?:\s+(?:of\s+the\s+|of\s+|the\s+)?[A-Z][\p{L}'’-]{1,}){0,3})/gu;let m;
      while((m=re.exec(sen))){
        let name=m[1].replace(/['’]s$/,"").trim();
        const first=name.split(/\s+/)[0];if(STOP.has(first)){name=name.split(/\s+/).slice(1).join(" ");if(!name)continue}
        if(name.length<3||STOP.has(name)||have.has(lc(name)))continue;
        count.set(name,(count.get(name)||0)+1);
        const b=best.get(name);if(!b||(sen.length>=60&&sen.length<b.length)||b.length<60)best.set(name,sen.trim().slice(0,300));
      }
    }
  }
  const min=opts.min||3;
  return [...count].filter(([n,c])=>c>=min).sort((a,b)=>b[1]-a[1]).slice(0,opts.limit||25)
    .map(([n,c])=>({k:n,t:best.get(n)||"",kind:"term",src:"source",count:c}));
}

/* ---------- style samples ---------- */
/* st.styleSamples = [{id, text, src?}] chosen by the player (up to 3). Sent every turn as voice examples. */
function styleBlock(st,opts){
  opts=opts||{};const max=opts.max||3,each=opts.each||1500;
  const xs=(Array.isArray(st&&st.styleSamples)?st.styleSamples:[]).map(x=>str(x&&x.text,each)).filter(Boolean).slice(0,max);
  if(!xs.length)return "";
  return "\n\nSTYLE SAMPLES from the source the player chose. Write your narration and dialogue in this same voice: point of view, tense, sentence rhythm and length, vocabulary, tone, how much is described versus said, and how characters speak. They are examples of HOW to write, not WHAT happens: never copy their sentences, names or events, and never quote them.\n"+xs.map((x,i)=>"--- sample "+(i+1)+" ---\n"+x).join("\n");
}
/* Suggests passages that show the author's voice well: medium length, a mix of narration and dialogue,
   spread across the book. chunks: array of passages (e.g. a reference text's chunks). Returns [{i, text, score}]. */
function suggestStyleSamples(chunks,opts){
  opts=opts||{};const n=opts.n||3,arr=(chunks||[]).map((c,i)=>({i,text:String(c||"").trim()})).filter(x=>x.text.length>=400);
  const scored=arr.map(x=>{const t=x.text,len=t.length,q=(t.match(/["“”]/g)||[]).length,sent=t.split(/(?<=[.!?])\s+/).length;
    let sc=0;sc+=len>=600&&len<=1600?3:len<=2200?1:-2;sc+=q>=2&&q<=14?2:q===0?0:-1;sc+=sent>=5?1:0;
    if(/^(chapter|contents|copyright|acknowledg|table of)/i.test(t)||/isbn|all rights reserved/i.test(t))sc-=10;
    return {i:x.i,text:t.slice(0,1500),score:sc}}).filter(x=>x.score>0);
  if(!scored.length)return [];
  const N=arr.length?arr[arr.length-1].i+1:1,out=[];
  for(let k=0;k<n;k++){const lo=Math.floor(k*N/n),hi=Math.floor((k+1)*N/n);const part=scored.filter(x=>x.i>=lo&&x.i<hi).sort((a,b)=>b.score-a.score);if(part[0])out.push(part[0])}
  return out;
}

/* ---------- notes ---------- */
function allNotes(DB,se){
  const n=[];
  if(str(DB&&DB.globalNote,100000))n.push({id:"legacy-global",text:str(DB.globalNote,100000),pri:"must",scope:{type:"always"},src:"global"});
  (Array.isArray(DB&&DB.notes)?DB.notes:[]).forEach(x=>n.push(Object.assign({src:"global"},x)));
  if(str(se&&se.note,100000))n.push({id:"legacy-story",text:str(se.note,100000),pri:"must",scope:{type:"always"},src:"story"});
  (Array.isArray(se&&se.notes)?se.notes:[]).forEach(x=>n.push(Object.assign({src:"story"},x)));
  return n.filter(x=>x&&str(x.text,100000));
}
/* Resolves scope for every note. Returns {active:[...], inactive:[{id,reason}]}. */
function notes(DB,se,st,hist,action,ctx){
  ctx=ctx||{};const act=[],inactive=[];
  const hay=String(action||"")+"\n"+(hist||[]).slice(-2).map(t=>t.text||"").join("\n");
  const present=(ctx.present||[]).map(lc);
  for(const n of allNotes(DB,se)){
    const id=String(n.id||"note"),pri=["must","should","style"].includes(n.pri)?n.pri:"must";
    if(n.on===false){inactive.push({id,reason:"turned off"});continue}
    const sc=n.scope||{type:"always"},type=sc.type||"always",val=String(sc.value==null?"":sc.value).trim();
    let ok=true,reason="";
    if(type==="keyword"){const ks=val.split(",").map(x=>x.trim()).filter(Boolean);ok=ks.some(k=>hasKey(hay,k));reason="keyword not in this scene"}
    else if(type==="character"){const ks=val.split(",").map(x=>x.trim()).filter(Boolean);ok=ks.some(k=>present.includes(lc(k))||hasKey(hay,k));reason="character not in this scene"}
    else if(type==="chapter"){const c=Number(ctx.chapter)||0,m=val.match(/^(\d+)(?:\s*-\s*(\d+))?$/);ok=!m||(c>=+m[1]&&c<=+(m[2]||m[1]));reason="outside its chapters"}
    else if(type==="turns"){const t=(hist||[]).filter(x=>x.role==="user").length+1,m=val.match(/^(\d+)(?:\s*-\s*(\d+))?$/);ok=!m||(t>=+m[1]&&(m[2]==null||t<=+m[2]));reason="outside its turns"}
    if(ok)act.push({id,text:str(n.text,100000),pri,src:n.src,scope:type}); /* never shortened: too-long notes are reported, not cut */else inactive.push({id,reason});
  }
  const rank={must:0,should:1,style:2};act.sort((a,b)=>rank[a.pri]-rank[b.pri]);
  return {active:act,inactive};
}

/* ---------- standing OOC directions ---------- */
const OOC_RE=/\(\s*OOC\s*:\s*([^)]*)\)/gi;
const STANDING=/\b(from now on|for the rest|always|never|don'?t ever|do not ever|stop (?:having|making|letting|writing)|keep (?:it|him|her|them|the)|until I say|until further notice|going forward|remember that|make sure)\b/i;
function detectStandingOoc(text){
  const out=[];let m;OOC_RE.lastIndex=0;
  while((m=OOC_RE.exec(String(text||""))))if(STANDING.test(m[1]))out.push(m[1].trim().slice(0,400));
  return out;
}
/* OOC directions with lasting wording from turns that are no longer in the history sent to the model. */
function standingOoc(hist,from,limit){
  const out=[];for(let j=0;j<Math.min(from,(hist||[]).length);j++){const t=hist[j];if(t&&t.role==="user")detectStandingOoc(t.text).forEach(x=>out.push(x))}
  return [...new Set(out)].slice(-(limit||6));
}

/* ---------- precedence and mandatory block ---------- */
function precedence(m){
  const canon=m==="au"||m==="creative"
    ?"4) the story record of this playthrough (what has already happened here); 5) canon notes, source passages and wiki notes, where they don't conflict with this playthrough; 6) your own knowledge of the base story"
    :"4) locked canon and the story record of this playthrough; 5) canon notes, source passages and wiki notes; 6) your own knowledge of the base story";
  return "\n\nPRIORITY when instructions or facts conflict (highest first): 1) an OOC direction in the player's latest message; 2) the player's MUST-follow notes; 3) locked canon and player-confirmed canon; "+canon+". Lower items never override higher ones.";
}
function mandatoryBlock(n,lockedText,confirmed,ooc){
  const must=n.active.filter(x=>x.pri==="must"),should=n.active.filter(x=>x.pri==="should"),style=n.active.filter(x=>x.pri==="style");
  const parts=[];
  if(must.length)parts.push("MUST follow, every reply:\n"+must.map(x=>"- "+x.text).join("\n"));
  if(ooc&&ooc.length)parts.push("Earlier standing directions from the player (still in effect unless a later note or OOC replaces them):\n"+ooc.map(x=>"- "+x).join("\n"));
  if(lockedText)parts.push("Locked canon (never contradict, never change):\n"+lockedText);
  if(confirmed)parts.push("Player-confirmed canon:\n"+confirmed);
  if(should.length)parts.push("Should follow unless the scene clearly makes it impossible:\n"+should.map(x=>"- "+x.text).join("\n"));
  if(style.length)parts.push("Style preferences:\n"+style.map(x=>"- "+x.text).join("\n"));
  return parts.length?"\n\n=== PLAYER INSTRUCTIONS AND LOCKED CANON ===\n"+parts.join("\n\n")+"\n=== END ===":"";
}
/* Short echo placed in the final user message, right before the model writes. */
function echo(n,lockedIds){
  const must=n.active.filter(x=>x.pri==="must").map(x=>x.text.split("\n")[0].slice(0,160));
  if(!must.length&&!(lockedIds&&lockedIds.length))return "";
  return "\n\n(Before writing, re-check the PLAYER INSTRUCTIONS"+(lockedIds&&lockedIds.length?" and LOCKED CANON":"")+" block"+(must.length?": "+must.map(x=>"• "+x).join(" "):"")+")";
}

/* ---------- character knowledge and timeline (Memory Phase 2, opt-in) ---------- */
function knowledge(se,M,opts){
  opts=opts||{};const mem=se&&se.mem;if(!mem||!M||typeof M.charView!=="function")return "";
  const sc=mem.scene||{},lastEv=(mem.events||[]).slice(-1)[0];
  let who=(sc.who||[]).slice(0,8);if(!who.length&&lastEv)who=(lastEv.who||[]).concat(lastEv.wit||[]).slice(0,8);
  const live=f=>f&&f.until==null;
  const all=(mem.facts||[]).concat(mem.secrets||[]).filter(live),lines=[];
  if(sc.where||sc.when||who.length)lines.push("Current scene: "+([sc.where,sc.when].filter(Boolean).join(", ")||"unknown place")+(who.length?"; present: "+who.join(", "):""));
  const knownBy=id=>Object.values(mem.chars||{}).some(c=>(c.knows||[]).includes(id));
  for(const n of who){
    const v=M.charView(se,n);if(!v)continue;
    const mine=new Set(((mem.chars[n]||{}).knows)||[]);
    const knows=all.filter(f=>mine.has(f.id)).slice(-6).map(f=>f.text);
    const notKnow=all.filter(f=>!mine.has(f.id)&&knownBy(f.id)).slice(-4).map(f=>f.text);
    const believes=(v.beliefs||[]).slice(-3).map(b=>typeof b==="string"?b:(b&&b.text)||"").filter(Boolean);
    const bits=[];if(knows.length)bits.push("knows: "+knows.join("; "));if(notKnow.length)bits.push("does NOT know: "+notKnow.join("; "));if(believes.length)bits.push("believes (may be wrong): "+believes.join("; "));
    if(bits.length)lines.push("- "+n+" "+bits.join(". "));
  }
  const ev=(mem.events||[]).filter(e=>(e.imp||0)>=3).slice(-(opts.events||6));
  if(ev.length)lines.push("Recent key events, oldest first:\n"+ev.map(e=>"- "+e.text).join("\n"));
  let out=lines.join("\n");const cap=opts.cap||3000;if(out.length>cap)out=out.slice(0,cap).replace(/\n[^\n]*$/,"");
  return out?"\n\nWho knows what, and where the story stands (from the story memory). Characters act and speak only on what they know; someone who does NOT know a fact must not mention it or react to it, unless they learn it in this reply:\n"+out:"";
}

/* ---------- divergence tracking ---------- */
function metaLine(se,st){
  const m=mode(se,st);if(m==="creative")return "";
  if(!Array.isArray(st&&st.entries)||!st.entries.length)return "";
  return "\nCANON: none, or for each canon note this reply departs from: entry name | player-choice (the player's action caused it) or drift (you changed it without a reason) | one short line on what changed, separated by ;";
}
function parseDivergence(line){
  const s=String(line||"").trim();if(!s||/^(none|n\/a|no|-)\.?$/i.test(s))return [];
  return s.split(";").map(p=>p.split("|").map(x=>x.trim())).filter(f=>f[0]&&!/^none$/i.test(f[0])).slice(0,5)
    .map(f=>({entry:f[0].slice(0,80),kind:/player/i.test(f[1]||"")?"player-choice":"drift",text:(f[2]||f[1]||"").slice(0,240)}));
}
/* Cheap local checks that need no model call. */
function localChecks(se,text){
  const out=[],t=String(text||"");
  for(const d of (se&&se.dead)||[]){
    const name=String(d).trim();if(!name)continue;
    const re=new RegExp("(^|\\n)\\s*"+esc(name)+"\\s*\\||\""+"[^\"]{0,200}\"\\s*,?\\s*"+esc(name)+"\\s+(?:says|said|asks|asked|replies|replied|shouts|whispers)","i");
    if(re.test(t))out.push({entry:name,kind:"drift",text:name+" is recorded as dead or removed but speaks in this reply."});
  }
  return out;
}
let seq=0;const nid=()=>"dv"+Date.now().toString(36)+(++seq);
function record(se,st,turn,tid,list){
  if(!list||!list.length)return [];
  const m=mode(se,st);se.divergences=Array.isArray(se.divergences)?se.divergences:[];
  const added=[];
  for(const d of list){
    const kind=m==="au"&&d.kind==="drift"?"au":d.kind;
    if(se.divergences.some(x=>x.turn===turn&&x.entry===d.entry&&x.text===d.text))continue;
    const x={id:nid(),turn,tid:tid||"",kind,entry:d.entry,text:d.text,status:kind==="drift"?"open":"accepted"};
    se.divergences.push(x);added.push(x);
  }
  if(se.divergences.length>200)se.divergences=se.divergences.slice(-200);
  return added;
}
function trimForBranch(n,cut){if(Array.isArray(n.divergences))n.divergences=n.divergences.filter(d=>d&&d.turn<cut)}
function dropTurn(se,turn){if(Array.isArray(se.divergences))se.divergences=se.divergences.filter(d=>d.turn!==turn)}

/* ---------- prompt size control ---------- */
/* sections: [{name, text, keep:true|false, drop:number (higher dropped first)}]. Returns {text, report}. */
function assemble(sections,cap){
  const total=()=>sections.reduce((a,s)=>a+(s.off?0:s.text.length),0);
  const order=sections.filter(s=>!s.keep&&s.text).sort((a,b)=>(b.drop||0)-(a.drop||0));
  const trimmed=[];
  for(const s of order){if(total()<=cap)break;s.off=true;trimmed.push(s.name)}
  return {text:sections.filter(s=>!s.off).map(s=>s.text).join(""),
          report:{sections:sections.filter(s=>s.text).map(s=>({name:s.name,chars:s.text.length,sent:!s.off,keep:!!s.keep})),trimmed,total:total(),cap}};
}

const API=Object.freeze({MODES,mode,hasKey,keysOf,lore,allNotes,notes,detectStandingOoc,standingOoc,precedence,mandatoryBlock,echo,
  knowledge,metaLine,parseDivergence,localChecks,record,trimForBranch,dropTurn,assemble,suggestEntries,styleBlock,suggestStyleSamples});
root.SFCanon=API;if(typeof globalThis!=='undefined'&&globalThis!==root)globalThis.SFCanon=API;
})(typeof window!=='undefined'?window:globalThis);
