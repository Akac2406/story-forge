/* Story Forge creator packages (roadmap: Advanced Creator Studio). Pure functions, no storage, no model calls.
 * A creator package is a reusable blueprint: story setup, character templates, gameplay setup (rules, quests, career, stats at their starting values)
 * and Story Director settings. It never carries playthroughs, progress, memories, credentials or keys.
 * Images are dropped unless the creator explicitly allows them, and never for stories imported from OOC (story.ooc). */
(function(root){
'use strict';
const clone=x=>JSON.parse(JSON.stringify(x)),arr=x=>Array.isArray(x)?x:[];
const FORMAT='story-forge-creator',VERSION=1,MAX=8*1024*1024;
const CRED_KEYS=/^(ockey|apikey|orkey|key|password|passwd|token|secret|ocproxy|authorization|bearer)$/i;
const CRED_VAL=/\b(sk-[A-Za-z0-9_-]{12,}|sk-or-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._-]{12,})/;
const IMG=/^data:image\//i;

/* Walk any value: drop credential-looking keys and values; drop images unless allowed. Returns {value, removed:[paths]}. */
function scrub(v,o){o=o||{};const removed=[];
  const walk=(x,p)=>{if(typeof x==='string'){if(CRED_VAL.test(x)){removed.push({path:p,why:'credential'});return undefined}if(IMG.test(x)&&!o.art){removed.push({path:p,why:'image'});return undefined}return x}
    if(Array.isArray(x))return x.map((y,i)=>walk(y,p+'['+i+']')).filter(y=>y!==undefined);
    if(x&&typeof x==='object'){const out={};for(const [k,y] of Object.entries(x)){if(['__proto__','constructor','prototype'].includes(k))continue;if(CRED_KEYS.test(k)){removed.push({path:p+'.'+k,why:'credential'});continue}const w=walk(y,p+'.'+k);if(w!==undefined)out[k]=w}return out}
    return x};
  return{value:walk(v,'$'),removed}}

/* Gameplay setup only: stats back to their starting values (or min), quests not started, nothing fired, no log/history, career at its first rank. */
function gameSetup(g){if(!g)return null;const G=clone(g);for(const s of Object.values(G.stats||{})){s.value=s.start!=null?s.start:s.min}
  G.quests=arr(G.quests).map(q=>({id:q.id,title:q.title,steps:q.steps,reward:q.reward||{},status:'active',done:[]}));G.fired=[];G.log=[];G.hist=[];G.xp=0;G.level=1;G.day=0;
  if(G.career){G.career.rank=(arr(G.career.ranks)[0]||{}).id||G.career.rank;G.career.week=0;G.career.history=[]}return G}

/* build(parts, o) -> {ok, package, removed, reason}. parts: {story (portable), templates[], game, director, universe:{id,name,rev}, creator:{name, note}} */
function build(parts,o){o=o||{};if(!parts||!parts.story||!parts.story.title)return{ok:false,reason:'needs a story with a title'};
  const art=!!o.art&&!parts.story.ooc,pkg={format:FORMAT,version:VERSION,created:o.now||Date.now(),creator:parts.creator?{name:String(parts.creator.name||'').slice(0,80),note:String(parts.creator.note||'').slice(0,2000)}:null,
    art,story:parts.story,templates:arr(parts.templates),gameplay:gameSetup(parts.game),director:parts.director||null,universe:parts.universe?{id:parts.universe.id,name:parts.universe.name,rev:parts.universe.rev||0}:null};
  const s=scrub(pkg,{art});const size=JSON.stringify(s.value).length;if(size>MAX)return{ok:false,reason:'package is larger than 8 MB',removed:s.removed};
  return{ok:true,package:s.value,removed:s.removed,size,artBlocked:!!o.art&&!!parts.story.ooc}}

/* validate(pkg) -> {ok, issues[]} for incoming files; preview(pkg) -> short summary for an import screen. */
function validate(pkg){const issues=[];if(!pkg||pkg.format!==FORMAT)issues.push('not a Story Forge creator package');else{if(pkg.version!==VERSION)issues.push('unsupported version '+pkg.version);if(!pkg.story||!pkg.story.title)issues.push('missing story');
  const s=scrub(pkg,{art:!!pkg.art});if(s.removed.some(r=>r.why==='credential'))issues.push('contains credentials; they will be removed');if(JSON.stringify(pkg).length>MAX)issues.push('larger than 8 MB')}
  return{ok:!issues.some(i=>/not a|unsupported|missing|larger/.test(i)),issues}}
function preview(pkg){const v=validate(pkg);if(!v.ok)return{ok:false,issues:v.issues};const g=pkg.gameplay;
  return{ok:true,issues:v.issues,title:pkg.story.title,creator:pkg.creator&&pkg.creator.name||'',characters:arr(pkg.story.cast0).length+arr(pkg.templates).length,templates:arr(pkg.templates).map(t=>t.name),
    gameplay:g?{career:g.career?g.career.name:null,stats:Object.keys(g.stats||{}).length,quests:arr(g.quests).length,rules:arr(g.rules).length}:null,director:!!pkg.director,universe:pkg.universe,art:!!pkg.art}}
/* open(pkg) -> clean copies ready to store: {story, templates, game, director, universe} (scrubbed again; images only if the package allowed them). */
function open(pkg){const v=validate(pkg);if(!v.ok)return{ok:false,reason:v.issues.join('; ')};const s=scrub(pkg,{art:!!pkg.art}).value;
  return{ok:true,story:s.story,templates:arr(s.templates),game:s.gameplay?Object.assign(gameSetup(s.gameplay),{enabled:!!s.gameplay.enabled}):null,director:s.director||null,universe:s.universe||null}}

root.SFCreator=Object.freeze({FORMAT,VERSION,scrub,gameSetup,build,validate,preview,open});
})(typeof window!=='undefined'?window:globalThis);
