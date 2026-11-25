/* Story Forge presentation engines (roadmap: Cinematic / Visual Novel, Appearance & Customization). Pure, no storage, no model calls.
 * SFCinema: per-story presentation (se.cv). Presentation never touches story text, canon, memory, knowledge or gameplay.
 * SFAppearance: validated appearance settings in the existing v48 shape ({version:1, global, stories, devices, custom}),
 *   plus portable, versioned presets that never carry credentials or story data.
 * Artwork is referenced, never copied or altered: background and portrait values must be references (art:, idb:, v54:, cast:), not image data. */
(function(root){
'use strict';
const clone=x=>JSON.parse(JSON.stringify(x)),has=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isRef=v=>v===null||(typeof v==='string'&&/^(art|idb|v54|cast|story):[\w:.-]{1,120}$/.test(v));
function check(spec,patch){for(const [k,v] of Object.entries(patch||{})){const r=spec[k];if(!r)return'unknown setting '+k;
  if(Array.isArray(r)){if(!r.includes(v))return'bad value for '+k}else if(r==='bool'){if(typeof v!=='boolean')return k+' must be true or false'}
  else if(r==='ref'){if(!isRef(v))return k+' must be an artwork reference, not image data'}else if(r==='hex'){if(!(v===null||/^#[0-9a-f]{6}$/i.test(v)))return k+' must be a #rrggbb colour'}
  else if(typeof r==='object'&&'min' in r){if(typeof v!=='number'||!(v>=r.min&&v<=r.max))return k+' must be between '+r.min+' and '+r.max}
  else if(r==='text'){if(typeof v!=='string'||v.length>40)return k+' must be short text'}}return null}

/* ---------------- Cinema ---------------- */
const LAYOUTS=[
  {id:'novel',name:'Classic novel',caps:{portraits:false,background:false,dialogueBox:false,reveal:false}},
  {id:'visual-novel',name:'Visual novel',caps:{portraits:true,background:true,dialogueBox:true,reveal:true}},
  {id:'cinematic',name:'Cinematic',caps:{portraits:true,background:true,dialogueBox:true,reveal:true,letterbox:true}},
  {id:'rpg',name:'RPG',caps:{portraits:true,background:true,dialogueBox:true,reveal:true,hud:true}},
  {id:'chat',name:'Chat',caps:{portraits:true,background:false,dialogueBox:false,reveal:false,bubbles:true}},
  {id:'screenplay',name:'Screenplay',caps:{portraits:false,background:false,dialogueBox:false,reveal:false,sluglines:true}},
  {id:'illustrated',name:'Illustrated novel',caps:{portraits:true,background:true,dialogueBox:false,reveal:false,plates:true}},
  {id:'immersive',name:'Immersive',caps:{portraits:true,background:true,dialogueBox:true,reveal:true,hideUI:true}}];
const CV_SPEC={layout:LAYOUTS.map(l=>l.id),lighting:['neutral','dawn','day','dusk','night','candle','storm','neon','underwater'],overlay:['none','rain','snow','fog','embers','petals','film-grain','vignette','scanlines'],
  transition:['none','fade','dissolve','slide','wipe','flash'],dialogueBox:['classic','minimal','parchment','glass','comic','terminal'],nameplate:'bool',narration:['plain','italic','boxed','centered'],
  textReveal:['instant','typewriter','fade-in'],revealSpeed:{min:5,max:120},autoAdvance:'bool',autoDelay:{min:1,max:30},fullscreen:'bool',hideUI:'bool',reducedMotion:'bool'};
const CV_DEFAULTS={layout:'novel',lighting:'neutral',overlay:'none',transition:'fade',dialogueBox:'classic',nameplate:true,narration:'plain',textReveal:'instant',revealSpeed:40,autoAdvance:false,autoDelay:4,fullscreen:false,hideUI:false,reducedMotion:false};
const SCENE_SPEC={background:'ref',lighting:CV_SPEC.lighting,overlay:CV_SPEC.overlay,transition:CV_SPEC.transition,caption:'text'};
const CHAR_SPEC={expression:['neutral','happy','sad','angry','surprised','afraid','thoughtful','smug','tired','determined'],position:['far-left','left','center','right','far-right','offscreen'],scale:{min:0.5,max:1.5},visible:'bool',portrait:'ref'};
const PRESETS=[
  {id:'quiet-novel',name:'Quiet novel',settings:{layout:'novel',narration:'plain',textReveal:'instant',transition:'none'}},
  {id:'classic-vn',name:'Classic visual novel',settings:{layout:'visual-novel',dialogueBox:'classic',nameplate:true,textReveal:'typewriter',revealSpeed:40,transition:'fade'}},
  {id:'noir',name:'Noir',settings:{layout:'cinematic',lighting:'night',overlay:'film-grain',dialogueBox:'minimal',narration:'italic',transition:'dissolve'}},
  {id:'storybook',name:'Storybook',settings:{layout:'illustrated',lighting:'day',dialogueBox:'parchment',narration:'centered',transition:'fade'}},
  {id:'jrpg',name:'JRPG',settings:{layout:'rpg',dialogueBox:'classic',textReveal:'typewriter',revealSpeed:60,transition:'flash'}},
  {id:'neon-city',name:'Neon city',settings:{layout:'cinematic',lighting:'neon',overlay:'scanlines',dialogueBox:'glass',transition:'wipe'}},
  {id:'gothic',name:'Gothic',settings:{layout:'visual-novel',lighting:'candle',overlay:'vignette',dialogueBox:'parchment',transition:'dissolve'}},
  {id:'messenger',name:'Messenger',settings:{layout:'chat',textReveal:'fade-in',transition:'none'}},
  {id:'screenplay',name:'Screenplay',settings:{layout:'screenplay',narration:'plain',textReveal:'instant',transition:'none'}},
  {id:'immersive-theatre',name:'Immersive theatre',settings:{layout:'immersive',hideUI:true,textReveal:'fade-in',autoAdvance:true,autoDelay:5,transition:'fade'}},
  {id:'calm',name:'Calm (reduced motion)',settings:{reducedMotion:true,transition:'none',textReveal:'instant',overlay:'none',autoAdvance:false}}];
const cvEmpty=()=>({settings:{},scene:{},cast:{},preset:null});
function cvState(cv){cv=cv||cvEmpty();const s=Object.assign({},CV_DEFAULTS,cv.settings||{});if(s.reducedMotion){s.transition='none';if(s.textReveal==='typewriter')s.textReveal='fade-in';s.overlay=['rain','snow','embers','petals'].includes(s.overlay)?'none':s.overlay}
  const L=LAYOUTS.find(l=>l.id===s.layout)||LAYOUTS[0];return{settings:s,layout:L,scene:Object.assign({lighting:s.lighting,overlay:s.overlay,transition:s.transition},cv.scene||{}),cast:clone(cv.cast||{}),preset:cv.preset||null}}
const res=(ok,cv,reason)=>ok?{ok:true,applied:true,reason:null,cv}:{ok:false,applied:false,reason,cv:null};
function cvSet(cv,patch){const e=check(CV_SPEC,patch);if(e)return res(false,null,e);const C=clone(cv||cvEmpty());const before=JSON.stringify(C.settings);Object.assign(C.settings,patch);C.preset=null;return JSON.stringify(C.settings)===before?res(false,null,'unchanged'):res(true,C)}
function cvSetScene(cv,patch){const e=check(SCENE_SPEC,patch);if(e)return res(false,null,e);const C=clone(cv||cvEmpty());Object.assign(C.scene,patch);return res(true,C)}
function cvSetCharacter(cv,name,patch){if(!name||typeof name!=='string')return res(false,null,'needs a character name');const e=check(CHAR_SPEC,patch);if(e)return res(false,null,e);const C=clone(cv||cvEmpty());C.cast[name]=Object.assign({expression:'neutral',position:'center',scale:1,visible:true},C.cast[name]||{},patch);return res(true,C)}
function cvApplyPreset(cv,id){const p=PRESETS.find(x=>x.id===id);if(!p)return res(false,null,'unknown preset');const C=clone(cv||cvEmpty());C.settings=Object.assign({},C.settings,p.settings);C.preset=id;return res(true,C)}
function cvReset(cv){return res(true,Object.assign(cvEmpty(),{}))}

/* ---------------- Appearance ---------------- */
const ICONS=[
  {id:'line',name:'Fine line',style:{stroke:1.5,fill:'none',corner:'round',weight:'light'}},{id:'rounded',name:'Rounded',style:{stroke:2,fill:'none',corner:'round',weight:'regular',terminal:'round'}},
  {id:'solid',name:'Solid',style:{stroke:0,fill:'solid',corner:'round',weight:'bold'}},{id:'duotone',name:'Duotone',style:{stroke:1.5,fill:'tint',corner:'round',weight:'regular',layers:2}},
  {id:'pixel',name:'Pixel',style:{stroke:0,fill:'solid',corner:'square',grid:16,weight:'bold'}},{id:'sketch',name:'Hand-drawn',style:{stroke:1.75,fill:'none',corner:'round',jitter:true}},
  {id:'ink',name:'Ink brush',style:{stroke:2.5,fill:'none',taper:true,corner:'round'}},{id:'runic',name:'Runic',style:{stroke:2,fill:'none',corner:'sharp',angular:true}},
  {id:'neon',name:'Neon',style:{stroke:1.75,fill:'none',glow:true,corner:'round'}},{id:'engraved',name:'Engraved',style:{stroke:1.25,fill:'none',corner:'sharp',doubleLine:true}},
  {id:'geometric',name:'Geometric',style:{stroke:2,fill:'none',corner:'sharp',shapes:'primitive'}},{id:'sticker',name:'Sticker',style:{stroke:2,fill:'solid',outline:'white',corner:'round',shadow:true}},
  {id:'glyph',name:'Glyph serif',style:{stroke:0,fill:'solid',corner:'sharp',serif:true}},{id:'blueprint',name:'Blueprint',style:{stroke:1,fill:'none',corner:'square',dashed:true}}];
const AP_SPEC={theme:'text',layout:'text',format:'text',motion:['none','subtle','full'],icons:ICONS.map(i=>i.id),bg:'hex',card:'hex',accent:'hex',text:'hex',font:'text',fontScale:{min:0.8,max:1.4},
  spacing:['compact','cozy','roomy'],transparency:{min:0,max:0.6},borders:['none','thin','bold'],radius:{min:0,max:24},nav:['bottom','top','side','floating'],panel:['right','left','bottom','overlay'],
  reducedMotion:'bool',contrast:['normal','high'],background:'ref'};
const AP_KEYS=Object.keys(AP_SPEC);
const apEmpty=()=>({version:1,global:{},stories:{},devices:{mobile:{},desktop:{}},custom:{}});
function scopeOf(cfg,scope){if(scope==='global'||!scope)return cfg.global;if(scope==='mobile'||scope==='desktop')return cfg.devices[scope]=cfg.devices[scope]||{};const m=String(scope).match(/^story:(.+)$/);if(m)return cfg.stories[m[1]]=cfg.stories[m[1]]||{};return null}
function apSet(cfg,patch,scope,catalog){const C=Object.assign(apEmpty(),clone(cfg||{}));const tgt=scopeOf(C,scope);if(!tgt)return{ok:false,applied:false,reason:'scope must be global, mobile, desktop or story:<id>'};
  const nn={};for(const [k,v] of Object.entries(patch||{})){if(!AP_SPEC[k])return{ok:false,applied:false,reason:'unknown setting '+k};if(v!==null)nn[k]=v}const e=check(AP_SPEC,nn);if(e)return{ok:false,applied:false,reason:e};catalog=catalog||{};
  if(patch.theme&&catalog.themes&&!catalog.themes.includes(patch.theme)&&!/^Use /.test(patch.theme))return{ok:false,applied:false,reason:'unknown theme'};
  if(patch.layout&&catalog.layouts&&!catalog.layouts.includes(patch.layout)&&!/^Use /.test(patch.layout))return{ok:false,applied:false,reason:'unknown layout'};
  if(patch.format&&catalog.formats&&!catalog.formats.includes(patch.format)&&!/^Use /.test(patch.format))return{ok:false,applied:false,reason:'unknown format'};
  for(const [k,v] of Object.entries(patch)){if(v===null)delete tgt[k];else tgt[k]=v}return{ok:true,applied:true,reason:null,cfg:C}}
/* Effective settings: global, then story, then device (the order v48 uses). Reduced motion forces motion none. High contrast drops transparency. */
function apState(cfg,storyId,device){const C=Object.assign(apEmpty(),cfg||{});const s=Object.assign({icons:'rounded',fontScale:1,spacing:'cozy',transparency:0,borders:'thin',radius:12,nav:'bottom',panel:'right',reducedMotion:false,contrast:'normal',motion:'subtle'},C.global,storyId?C.stories[storyId]:null,C.devices[device]||null);
  if(s.reducedMotion)s.motion='none';if(s.contrast==='high')s.transparency=0;return s}
function apReset(cfg,scope){const C=Object.assign(apEmpty(),clone(cfg||{}));if(scope==='global'||!scope)C.global={};else if(scope==='mobile'||scope==='desktop')C.devices[scope]={};else{const m=String(scope).match(/^story:(.+)$/);if(!m)return{ok:false,applied:false,reason:'bad scope'};delete C.stories[m[1]]}return{ok:true,applied:true,reason:null,cfg:C}}
const pick=s=>{const o={};for(const k of AP_KEYS)if(s&&has(s,k)&&s[k]!==undefined)o[k]=s[k];return o};
function apSavePreset(presets,name,settings,now){name=String(name||'').trim().slice(0,60);if(!name)return{ok:false,applied:false,reason:'needs a name'};const st=pick(settings);const e=check(AP_SPEC,st);if(e)return{ok:false,applied:false,reason:e};
  const P=clone(presets||{});const id='p'+((now||Date.now()).toString(36))+Object.keys(P).length;P[id]={id,name,settings:st,created:now||Date.now()};return{ok:true,applied:true,reason:null,presets:P,id}}
function apDeletePreset(presets,id){if(!presets||!presets[id])return{ok:false,applied:false,reason:'not found'};const P=clone(presets);delete P[id];return{ok:true,applied:true,reason:null,presets:P}}
function apExport(preset){return{format:'story-forge-appearance',version:1,name:preset.name,settings:pick(preset.settings)}}
function apImportPreview(data){const issues=[];if(!data||data.format!=='story-forge-appearance')return{ok:false,issues:['not a Story Forge appearance preset']};if(data.version!==1)return{ok:false,issues:['unsupported version '+data.version]};
  const st=pick(data.settings),dropped=Object.keys(data.settings||{}).filter(k=>!has(st,k));if(dropped.length)issues.push('ignored: '+dropped.join(', '));const e=check(AP_SPEC,st);if(e)return{ok:false,issues:issues.concat([e])};
  return{ok:true,issues,name:String(data.name||'Imported preset').slice(0,60),settings:st}}

root.SFCinema=Object.freeze({LAYOUTS,PRESETS,DEFAULTS:CV_DEFAULTS,SPEC:{settings:CV_SPEC,scene:SCENE_SPEC,character:CHAR_SPEC},state:cvState,set:cvSet,setScene:cvSetScene,setCharacter:cvSetCharacter,applyPreset:cvApplyPreset,reset:cvReset,isRef});
root.SFAppearance=Object.freeze({ICONS,SPEC:AP_SPEC,KEYS:AP_KEYS,empty:apEmpty,set:apSet,state:apState,reset:apReset,savePreset:apSavePreset,deletePreset:apDeletePreset,exportPreset:apExport,importPreview:apImportPreview});
})(typeof window!=='undefined'?window:globalThis);
