/* Story Forge Story Director engine (roadmap phase 12). Pure functions, no network, no AI requests.
 * settings: narrative focus weights, pacing, dialogue, humor, suspense, time-skip approval, subplot freedom, canon speed.
 * analyze(): measures what recent replies actually did (dialogue share, plot movement, spotlight, open threads).
 * guidance(): short, non-forcing directions for the narrator that close the gap between settings and what is happening.
 * The player's choices always win; guidance never decides for the player or forces an event.
 */
(function(root){
'use strict';
const arr=x=>Array.isArray(x)?x:[];const low=x=>String(x||'').toLowerCase();
const LEVELS=['off','low','secondary','balanced','high'];
const FOCUS=['mainPlot','characters','worldbuilding','relationships','everyday','mystery','progression'];
const DEFAULTS={focus:{mainPlot:'high',characters:'high',worldbuilding:'balanced',relationships:'secondary',everyday:'secondary',mystery:'balanced',progression:'balanced'},
  pacing:'natural',dialogue:'balanced',humor:'low',suspense:'balanced',description:'balanced',timeSkips:'ask',subplots:'allowed',canonSpeed:'natural'};
function defaults(){return JSON.parse(JSON.stringify(DEFAULTS))}
const OPTS={pacing:['slow','natural','fast'],dialogue:LEVELS,humor:LEVELS,suspense:LEVELS,description:LEVELS,timeSkips:['ask','allowed','never'],subplots:['none','allowed','encouraged'],canonSpeed:['slow','natural','fast']};
/* set(settings, patch) -> {ok, applied, reason, settings} */
function set(settings,patch){const S=Object.assign(defaults(),JSON.parse(JSON.stringify(settings||{}))),p=patch||{};
  for(const k of Object.keys(p)){if(k==='focus'){for(const f of Object.keys(p.focus||{})){if(!FOCUS.includes(f))return{ok:false,applied:false,reason:'unknown focus '+f,settings};if(!LEVELS.includes(p.focus[f]))return{ok:false,applied:false,reason:'bad level for '+f,settings};S.focus[f]=p.focus[f]}}
    else if(OPTS[k]){if(!OPTS[k].includes(p[k]))return{ok:false,applied:false,reason:'bad value for '+k,settings};S[k]=p[k]}else return{ok:false,applied:false,reason:'unknown setting '+k,settings}}
  if(JSON.stringify(S)===JSON.stringify(Object.assign(defaults(),settings||{})))return{ok:false,applied:false,reason:'unchanged',settings};return{ok:true,applied:true,reason:null,settings:S}}
const W=s=>(String(s||'').match(/\S+/g)||[]).length;
/* analyze({replies:[text], events:[{t, imp, kind, who[], open}], t, cast:[names], important:[names]}) -> measures */
function analyze(o){o=o||{};const R=arr(o.replies).slice(-6),words=R.reduce((a,r)=>a+W(r),0)||1;
  const quoted=R.reduce((a,r)=>a+(String(r).match(/"[^"]{2,}"|“[^”]{2,}”/g)||[]).reduce((b,q)=>b+W(q),0)+(String(r).match(/^\s*[A-Z][\w .'-]{0,30}\s*\|.*$/gm)||[]).reduce((b,l)=>b+W(l),0),0);
  const E=arr(o.events),t=Number(o.t)||0,plot=E.filter(e=>(e.imp||0)>=4).sort((a,b)=>b.t-a.t)[0],sincePlot=plot?Math.round((t-plot.t)/2):null;
  const recent=E.filter(e=>e.t>t-20),seen={};recent.forEach(e=>arr(e.who).forEach(w=>seen[low(w)]=Math.max(seen[low(w)]||0,e.t)));
  const neglected=arr(o.important).filter(n=>!seen[low(n)]).slice(0,3);
  const open=E.filter(e=>e.open).length,humor=R.filter(r=>/\b(laugh\w*|grin\w*|joke\w*|chuckl\w*|snort\w*|tease\w*)\b/i.test(r)).length,tense=R.filter(r=>/\b(danger|threat\w*|blood|scream\w*|dread|chase\w*|trap\w*|ambush\w*)\b/i.test(r)).length;
  return{replies:R.length,avgWords:Math.round(words/(R.length||1)),dialogueShare:Math.round(100*quoted/words),turnsSincePlot:sincePlot,neglected,openThreads:open,humorShare:R.length?Math.round(100*humor/R.length):0,tensionShare:R.length?Math.round(100*tense/R.length):0}}
const LV=x=>LEVELS.indexOf(x);
/* guidance(settings, analysis) -> [text] (at most 5, most important first). Gentle, non-forcing. */
function guidance(settings,a){const S=Object.assign(defaults(),settings||{}),F=Object.assign({},DEFAULTS.focus,S.focus||{}),out=[];a=a||{};
  if(LV(F.mainPlot)>=3&&a.turnsSincePlot!=null&&a.turnsSincePlot>=(S.pacing==='fast'?3:S.pacing==='slow'?10:6))out.push('The main plot has not moved for '+a.turnsSincePlot+' turns; let it advance naturally through what happens next.');
  if(LV(F.mainPlot)<=1&&a.turnsSincePlot!=null&&a.turnsSincePlot<=1)out.push('Keep the main plot in the background for now; follow the player\'s interests.');
  if(LV(F.characters)>=3&&arr(a.neglected).length)out.push('Give '+a.neglected.join(', ')+' some attention when it fits; they have not appeared for a while.');
  if(LV(S.dialogue)>=4&&a.dialogueShare<25)out.push('Use more spoken dialogue between characters.');if(LV(S.dialogue)<=1&&a.dialogueShare>60)out.push('Use less dialogue; favour narration and action.');
  if(LV(S.humor)>=3&&a.humorShare<20)out.push('Allow some lighter, humorous moments that suit the characters.');if(LV(S.humor)<=0&&a.humorShare>0)out.push('Keep the tone serious; avoid jokes.');
  if(LV(S.suspense)>=4&&a.tensionShare<30)out.push('Build more tension and suspense.');if(LV(S.suspense)<=1&&a.tensionShare>50)out.push('Ease the tension; give the characters room to breathe.');
  if(LV(F.mystery)>=3&&a.openThreads>=4)out.push('Several threads are open; pick one up again before adding new ones.');
  if(S.subplots==='none'&&a.openThreads>=2)out.push('Do not start new subplots.');
  if(LV(F.everyday)>=4)out.push('Include everyday life between major events.');if(LV(F.worldbuilding)>=4)out.push('Show more of the world: places, customs and how things work.');
  if(LV(F.relationships)>=4)out.push('Let relationships develop through small moments.');if(LV(F.progression)>=4)out.push('Let the player\'s skills and progress show.');
  out.push(S.timeSkips==='ask'?'Never skip time unless the player asks.':S.timeSkips==='never'?'Never skip time.':'Skip uneventful time when it helps the story.');
  if(S.pacing!=='natural')out.push(S.pacing==='slow'?'Take your time; linger on scenes.':'Keep scenes moving; skip filler.');
  return out.slice(0,6)}
function block(settings,a){const g=guidance(settings,a);return g.length?'STORY DIRECTOR (guidance, never override the player\'s choices):\n'+g.map(x=>'- '+x).join('\n'):''}
root.SFDirector=Object.freeze({LEVELS,FOCUS,OPTS,defaults,set,analyze,guidance,block});
})(typeof window!=='undefined'?window:globalThis);
