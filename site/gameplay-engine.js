/* Story Forge gameplay engine (roadmap phase 9): stats, progression, quests, consequences and modular careers.
 * Pure functions on a plain "game" object stored per playthrough (se.game). Nothing here calls a model or touches storage.
 * Every mutation returns {ok, applied, reason, game} with a new object; the input is never changed. History supports undo.
 * Randomness is seeded and bounded (mulberry32), so the same seed and actions always give the same result. */
(function(root){
'use strict';
const clone=x=>JSON.parse(JSON.stringify(x)),arr=x=>Array.isArray(x)?x:[],num=(x,d)=>{const n=+x;return Number.isFinite(n)?n:d};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
function rng(seed){let a=seed>>>0;return()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296}}
const hash=s=>{let h=2166136261;for(const c of String(s))h=Math.imul(h^c.charCodeAt(0),16777619);return h>>>0};

function defaults(){return{v:1,enabled:false,seed:1,day:0,stats:{},xp:0,level:1,curve:{base:100,growth:1.5,max:50},quests:[],rules:[],fired:[],career:null,log:[],hist:[]}}
const levelFor=(xp,c)=>{c=c||{};let lv=1,need=num(c.base,100),left=xp;while(left>=need&&lv<num(c.max,50)){left-=need;lv++;need=Math.round(need*num(c.growth,1.5))}return lv};

/* Every change goes through here: copy, apply, record what it was, re-check consequences. */
function mutate(game,kind,fn,o){o=o||{};const G=clone(game||defaults()),before=clone(game||defaults());delete before.hist;
  let r;try{r=fn(G)||{}}catch(e){return{ok:false,applied:false,reason:String(e.message||e),game}}
  if(r.reason)return{ok:false,applied:false,reason:r.reason,game};
  G.level=levelFor(G.xp,G.curve);const fired=o.noRules?[]:checkRules(G,o.t);
  G.hist=arr(G.hist).concat([{kind,at:o.now||Date.now(),t:o.t==null?null:o.t,prev:before}]).slice(-40);
  if(r.log!==false)G.log=arr(G.log).concat([{kind,t:o.t==null?null:o.t,day:G.day,text:r.log||kind}]).slice(-200);
  return{ok:true,applied:true,reason:null,game:G,fired,result:r.result}}
function undo(game){const h=arr(game&&game.hist);if(!h.length)return{ok:false,applied:false,reason:'nothing to undo',game};const p=clone(h[h.length-1].prev);p.hist=h.slice(0,-1);return{ok:true,applied:true,reason:null,game:p}}

/* ---------- stats ---------- */
function defineStat(game,s){return mutate(game,'stat',G=>{if(!s||!s.id)return{reason:'needs an id'};const min=num(s.min,0),max=num(s.max,100);if(min>=max)return{reason:'min must be below max'};
  G.stats[s.id]={id:s.id,name:s.name||s.id,min,max,value:clamp(num(s.start,min),min,max),hidden:!!s.hidden};return{log:'Stat '+(s.name||s.id)+' added'}})}
function change(game,id,delta,why,o){return mutate(game,'change',G=>{const s=G.stats[id];if(!s)return{reason:'unknown stat '+id};const v=clamp(s.value+num(delta,0),s.min,s.max);if(v===s.value)return{reason:'no change'};
  const d=v-s.value;s.value=v;return{log:s.name+' '+(d>0?'+':'')+d+(why?' ('+why+')':''),result:{id,delta:d,value:v}}},o)}
function gainXp(game,n,why,o){return mutate(game,'xp',G=>{const x=Math.max(0,Math.round(num(n,0)));if(!x)return{reason:'no change'};const lv=G.level;G.xp+=x;const nl=levelFor(G.xp,G.curve);return{log:'+'+x+' XP'+(why?' ('+why+')':'')+(nl>lv?' · level '+nl:''),result:{level:nl,up:nl>lv}}},o)}

/* ---------- quests ---------- */
function addQuest(game,q){return mutate(game,'quest',G=>{if(!q||!q.id||!q.title)return{reason:'needs an id and title'};if(G.quests.some(x=>x.id===q.id))return{reason:'quest exists'};
  G.quests.push({id:q.id,title:q.title,steps:arr(q.steps).map(s=>typeof s==='string'?{text:s}:s),done:[],status:'active',reward:q.reward||{},failIf:q.failIf||null,due:q.due==null?null:num(q.due,null)});return{log:'Quest: '+q.title}})}
function applyReward(G,rw){for(const [k,v] of Object.entries(rw||{})){if(k==='xp'){G.xp+=Math.max(0,num(v,0))}else if(G.stats[k]){const s=G.stats[k];s.value=clamp(s.value+num(v,0),s.min,s.max)}}}
function advanceQuest(game,id,step,o){return mutate(game,'advance',G=>{const q=G.quests.find(x=>x.id===id);if(!q)return{reason:'unknown quest'};if(q.status!=='active')return{reason:'quest is '+q.status};
  const i=step==null?q.done.length:num(step,-1);if(i<0||i>=q.steps.length)return{reason:'no such step'};if(q.done.includes(i))return{reason:'step already done'};
  q.done.push(i);let msg='Quest step: '+q.steps[i].text;if(q.done.length===q.steps.length){q.status='complete';applyReward(G,q.reward);msg='Quest complete: '+q.title}return{log:msg,result:{status:q.status}}},o)}
function failQuest(game,id,why,o){return mutate(game,'fail',G=>{const q=G.quests.find(x=>x.id===id);if(!q)return{reason:'unknown quest'};if(q.status!=='active')return{reason:'quest is '+q.status};q.status='failed';q.why=why||'';return{log:'Quest failed: '+q.title+(why?' ('+why+')':'')}},o)}

/* ---------- consequences: "when stat op value, do effect" (once unless repeat) ---------- */
const OPS={'<':(a,b)=>a<b,'<=':(a,b)=>a<=b,'>':(a,b)=>a>b,'>=':(a,b)=>a>=b,'==':(a,b)=>a===b};
function addRule(game,r){return mutate(game,'rule',G=>{if(!r||!r.id||!r.when||!OPS[r.when.op])return{reason:'needs id and when {stat, op, value}'};if(!G.stats[r.when.stat]&&r.when.stat!=='level'&&r.when.stat!=='day')return{reason:'unknown stat '+r.when.stat};
  if(G.rules.some(x=>x.id===r.id))return{reason:'rule exists'};G.rules.push({id:r.id,when:r.when,effect:r.effect||{},note:r.note||'',repeat:!!r.repeat});return{log:'Rule added: '+(r.note||r.id)}},{noRules:true})}
function valueOf(G,k){return k==='level'?G.level:k==='day'?G.day:(G.stats[k]||{}).value}
function checkRules(G,t){const out=[];for(let pass=0;pass<3;pass++){let any=false;for(const r of G.rules){const on=OPS[r.when.op](valueOf(G,r.when.stat),num(r.when.value,0)),was=G.fired.includes(r.id);
    if(on&&!was){G.fired.push(r.id);const e=r.effect||{};if(e.stats)applyReward(G,e.stats);if(e.fail)G.quests.filter(q=>q.id===e.fail&&q.status==='active').forEach(q=>{q.status='failed';q.why=r.note||r.id});
      if(e.unlock)G.quests.filter(q=>q.id===e.unlock&&q.status==='locked').forEach(q=>q.status='active');G.level=levelFor(G.xp,G.curve);G.log.push({kind:'consequence',t:t==null?null:t,day:G.day,text:r.note||r.id});out.push(r.id);any=true}
    else if(!on&&was&&r.repeat){G.fired=G.fired.filter(x=>x!==r.id)}}if(!any)break}return out}

/* ---------- careers: modules with stats, ranks (milestones) and weekly activities ---------- */
const CAREERS={
  idol:{name:'Idol',stats:[['vocal','Vocal'],['dance','Dance'],['rap','Rap'],['visual','Visual'],['variety','Variety'],['stamina','Stamina',0,100,80],['fans','Fans',0,1000000,0],['stress','Stress',0,100,10]],
    ranks:[{id:'trainee',name:'Trainee'},{id:'predebut',name:'Pre-debut',need:{vocal:40,dance:40}},{id:'rookie',name:'Rookie',need:{vocal:55,dance:55,fans:5000}},{id:'rising',name:'Rising star',need:{fans:50000}},{id:'top',name:'Top idol',need:{fans:500000,vocal:80,dance:80}}],
    activities:{vocal_lesson:{name:'Vocal lesson',gain:{vocal:[2,5]},cost:{stamina:8,stress:3}},dance_practice:{name:'Dance practice',gain:{dance:[2,5]},cost:{stamina:12,stress:4}},rap_session:{name:'Rap session',gain:{rap:[2,5]},cost:{stamina:6,stress:3}},
      photoshoot:{name:'Photoshoot',gain:{visual:[1,3],fans:[100,800]},cost:{stamina:5,stress:2}},variety_show:{name:'Variety show',gain:{variety:[2,4],fans:[500,3000]},cost:{stamina:10,stress:6},needRank:'rookie'},
      rest:{name:'Rest day',gain:{stamina:[20,30]},cost:{stress:-15}},fan_meeting:{name:'Fan meeting',gain:{fans:[300,2000]},cost:{stamina:8,stress:2},needRank:'predebut'}}},
  athlete:{name:'Athlete',stats:[['strength','Strength'],['speed','Speed'],['technique','Technique'],['stamina','Stamina',0,100,80],['ranking','Ranking points',0,100000,0],['injury','Injury risk',0,100,5]],
    ranks:[{id:'amateur',name:'Amateur'},{id:'semipro',name:'Semi-pro',need:{technique:45}},{id:'pro',name:'Professional',need:{technique:60,ranking:1000}},{id:'elite',name:'Elite',need:{ranking:10000}}],
    activities:{training:{name:'Training',gain:{strength:[1,4],speed:[1,3]},cost:{stamina:12,injury:3}},drills:{name:'Technique drills',gain:{technique:[2,5]},cost:{stamina:8,injury:1}},rest:{name:'Rest day',gain:{stamina:[20,30]},cost:{injury:-6}}}},
  musician:{name:'Musician',stats:[['skill','Skill'],['songwriting','Songwriting'],['stage','Stage presence'],['stamina','Stamina',0,100,80],['listeners','Listeners',0,10000000,0]],
    ranks:[{id:'busker',name:'Busker'},{id:'local',name:'Local act',need:{skill:40,listeners:500}},{id:'signed',name:'Signed artist',need:{songwriting:60,listeners:20000}},{id:'headliner',name:'Headliner',need:{listeners:1000000,stage:80}}],
    activities:{practice:{name:'Practice',gain:{skill:[2,5]},cost:{stamina:8}},write:{name:'Write songs',gain:{songwriting:[2,5]},cost:{stamina:6}},gig:{name:'Play a gig',gain:{stage:[1,4],listeners:[50,600]},cost:{stamina:12}},rest:{name:'Rest day',gain:{stamina:[20,30]},cost:{}}}}};
function careerList(){return Object.entries(CAREERS).map(([id,c])=>({id,name:c.name,stats:c.stats.map(s=>s[1]),ranks:c.ranks.map(r=>r.name),activities:Object.entries(c.activities).map(([k,a])=>({id:k,name:a.name,needRank:a.needRank||null}))}))}
function startCareer(game,id,o){o=o||{};const C=CAREERS[id]||o.custom;if(!C)return{ok:false,applied:false,reason:'unknown career',game};
  return mutate(game,'career',G=>{if(G.career)return{reason:'a career is already running'};for(const [sid,name,min,max,start] of C.stats)if(!G.stats[sid])G.stats[sid]={id:sid,name,min:num(min,0),max:num(max,100),value:num(start,num(o.start,20))};
    G.career={id:o.custom?(o.custom.id||'custom'):id,name:C.name,rank:C.ranks[0].id,ranks:clone(C.ranks),activities:clone(C.activities),week:0,history:[]};if(o.seed!=null)G.seed=num(o.seed,1);return{log:'Career started: '+C.name}})}
const rankIdx=(c,id)=>c.ranks.findIndex(r=>r.id===id);
function rankUp(G){const c=G.career;let i=rankIdx(c,c.rank),up=null;while(i+1<c.ranks.length){const n=c.ranks[i+1],need=n.need||{};if(Object.entries(need).every(([k,v])=>valueOf(G,k)>=v)){i++;up=n}else break}if(up){c.rank=up.id;c.history.push({week:c.week,rank:up.id})}return up}
/* doActivity: bounded seeded gains; the same seed, week and activity always give the same numbers. Exhaustion blocks training rather than going negative. */
function doActivity(game,act,o){o=o||{};return mutate(game,'activity',G=>{const c=G.career;if(!c)return{reason:'no career'};const a=c.activities[act];if(!a)return{reason:'unknown activity'};
  if(a.needRank&&rankIdx(c,c.rank)<rankIdx(c,a.needRank))return{reason:'needs rank '+(c.ranks.find(r=>r.id===a.needRank)||{}).name};
  const cost=a.cost||{};if(cost.stamina>0&&G.stats.stamina&&G.stats.stamina.value<cost.stamina)return{reason:'too tired: rest first'};
  const R=rng(hash(G.seed+':'+c.week+':'+act+':'+c.history.length)),got={};
  for(const [k,[lo,hi]] of Object.entries(a.gain||{})){const s=G.stats[k];if(!s)continue;const n=Math.round(lo+(hi-lo)*R());const v=clamp(s.value+n,s.min,s.max);got[k]=v-s.value;s.value=v}
  for(const [k,n] of Object.entries(cost)){const s=G.stats[k];if(!s)continue;const v=clamp(s.value-n,s.min,s.max);got[k]=(got[k]||0)+(v-s.value);s.value=v}
  c.week++;G.day+=num(o.days,7);c.history.push({week:c.week,act});const up=rankUp(G);
  return{log:a.name+': '+Object.entries(got).filter(([,v])=>v).map(([k,v])=>(G.stats[k].name)+' '+(v>0?'+':'')+v).join(', ')+(up?' · now '+up.name:''),result:{got,rank:c.rank,up:up?up.id:null}}},o)}

/* ---------- prompt ---------- */
function block(game){const G=game;if(!G||!G.enabled)return'';const L=[];const vis=Object.values(G.stats).filter(s=>!s.hidden);
  if(G.career){const r=G.career.ranks.find(x=>x.id===G.career.rank);L.push('Career: '+G.career.name+' · '+(r?r.name:G.career.rank)+' · week '+G.career.week)}
  if(vis.length)L.push('Stats: '+vis.map(s=>s.name+' '+s.value).join(', '));L.push('Level '+G.level+' ('+G.xp+' XP)');
  const aq=G.quests.filter(q=>q.status==='active');if(aq.length)L.push('Active quests: '+aq.map(q=>q.title+' ('+q.done.length+'/'+q.steps.length+')').join('; '));
  const rc=arr(G.log).filter(x=>x.kind==='consequence').slice(-3);if(rc.length)L.push('Recent consequences: '+rc.map(x=>x.text).join('; '));
  L.push('These numbers are tracked by the game. Describe effort and results consistently with them; never invent wins, promotions or stat changes the game has not recorded.');
  return'GAMEPLAY STATE\n'+L.join('\n')}
function set(game,patch){return mutate(game,'settings',G=>{if('enabled' in patch)G.enabled=!!patch.enabled;if(patch.curve)G.curve=Object.assign({},G.curve,patch.curve);if(patch.seed!=null)G.seed=num(patch.seed,1);return{log:false}},{noRules:true})}

root.SFGame=Object.freeze({defaults,set,defineStat,change,gainXp,levelFor,addQuest,advanceQuest,failQuest,addRule,startCareer,careerList,doActivity,undo,block,CAREERS:Object.freeze(Object.keys(CAREERS))});
})(typeof window!=='undefined'?window:globalThis);
