/* Story Forge v48 presentation-only customization. No memory engine hooks. */
(()=>{'use strict';
const KEY='sf.visual.v48';
const names=['Royal Fantasy','Enchanted Forest','Dark Kingdom','Celestial','Arcane Grimoire','Oceanic','Classic JRPG','Academy Life','Samurai Ink','Magical Dream','Shonen Arena','Cozy Anime','Neon Cyberpunk','Starship Command','Tactical Ops','Glitch Matrix','Future Minimal','Retro Synthwave','Crimson Gothic','Noir Detective','Wasteland','Eldritch Void','Midnight Gold','Clockwork','Modern Life','Cottagecore','Pastel Glass','Sports Career','Aviation Pro','Editorial Minimal'];
const colors=[['#0c1329','#202b49','#dfb55c'],['#0d221c','#1d3d31','#b5e68a'],['#1c101b','#37212d','#dd7885'],['#17243a','#324967','#f3d99c'],['#211b2b','#3d3150','#c7a2fa'],['#0a2731','#174a57','#83e2e0'],['#111b38','#263f75','#86baff'],['#30273d','#554365','#f5a8d0'],['#1e1b1d','#3a3330','#f0a37e'],['#34243d','#654a78','#ffb7e9'],['#2b1b25','#603145','#ffac65'],['#2d322b','#4c5c48','#e1d7aa'],['#0c142a','#25204b','#46e5e6'],['#091b30','#1c3959','#80caff'],['#1a2527','#304145','#e8b877'],['#170d22','#3b1d40','#ff5e92'],['#202b35','#3b5360','#a9e5f4'],['#271331','#542a60','#fc8cd8'],['#200e17','#45222d','#f07c90'],['#171a23','#323844','#e0c69a'],['#29221e','#514034','#e6ad72'],['#180e2b','#382052','#b39aff'],['#141419','#2c2931','#e8c17e'],['#30251c','#574230','#e4b676'],['#17252e','#2c4654','#a0d4e7'],['#273229','#435b48','#e0d4ab'],['#29283d','#4e4c70','#e2b9fa'],['#172539','#294d70','#f4c16e'],['#0b1b2e','#1d3854','#61c8eb'],['#26262b','#40404a','#d5d5e2']];
const themes=Object.fromEntries(names.map((n,i)=>[n,colors[i]]));
const layouts=['Game Launcher','Character RPG','Visual Novel','Novel Reader','Character Chat','Life Simulator','World Explorer','Timeline Explorer','Party Manager','Inventory Grid','Choice Cards','Quest Journal','Relationship Web','World Codex','Creator Workspace','Immersive Cinema'];
const formats=['RPG Adventure','Visual Novel','Novel Reader','Life Simulator','World Explorer','Character Chat','Interactive Story','Creator Studio'];
const appTheme='Use Settings theme';
const defaults={theme:appTheme,layout:'Use Settings layout',format:'Use story format',motion:'subtle'};
let cfg={global:{...defaults},stories:{},devices:{mobile:{},desktop:{}},custom:{}};
function load(){try{let d=JSON.parse(localStorage.getItem(KEY));if(d&&d.version===1){cfg.global={...defaults,...d.global};cfg.stories=d.stories||{};cfg.devices=d.devices||{mobile:{},desktop:{}};cfg.custom=d.custom||{}}}catch(e){}}load();
function valid(s){return typeof s==='string'&&s.length<100}
function palettes(){return {...themes,...cfg.custom}}
function storyId(){try{return view.n==='chat'?(DB.sessions.find(s=>s.id===view.id)||{}).storyId:(view.n==='story'?view.id:null)}catch(e){return null}}
function device(){return matchMedia('(max-width:700px)').matches?'mobile':'desktop'}
function mergeAppearance(...layers){
  return {...defaults,...Object.assign({},...layers),interfaceLook:Object.assign({},...layers.map(layer=>layer?.interfaceLook))};
}
function resolved(){const id=storyId();return mergeAppearance(cfg.global,id?cfg.stories[id]:null,cfg.devices[device()])}
function save(){try{localStorage.setItem(KEY,JSON.stringify({version:1,...cfg}))}catch(e){alert('Unable to save appearance settings; browser storage may be full.')}}
const themeGroups={
  ornamental:['Royal Fantasy','Dark Kingdom','Crimson Gothic','Midnight Gold','Clockwork'],
  organic:['Enchanted Forest','Oceanic','Cottagecore','Cozy Anime'],
  soft:['Academy Life','Magical Dream','Pastel Glass','Modern Life'],
  celestial:['Celestial','Eldritch Void','Arcane Grimoire','Retro Synthwave'],
  technical:['Classic JRPG','Neon Cyberpunk','Starship Command','Tactical Ops','Glitch Matrix','Shonen Arena','Sports Career','Aviation Pro','Future Minimal'],
  editorial:['Samurai Ink','Noir Detective','Wasteland','Editorial Minimal']
};
const treatments=Object.fromEntries(Object.entries(themeGroups).flatMap(([style,items])=>items.map(name=>[name,style])));
const designs={
  gallery:{nav:"bottom",overlay:"bottom",icons:"outline",font:"system",layouts:["Game Launcher","Inventory Grid","Choice Cards"]},
  dashboard:{nav:"side",overlay:"right",icons:"filled",font:"system",layouts:["Character RPG","Party Manager","Quest Journal","Creator Workspace"]},
  editorial:{nav:"top",overlay:"left",icons:"outline",font:"editorial",layouts:["Novel Reader","Timeline Explorer","World Codex"]},
  cinema:{nav:"bottom",overlay:"center",icons:"ornate",font:"soft",layouts:["Visual Novel","Immersive Cinema"]},
  social:{nav:"bottom",overlay:"right",icons:"filled",font:"soft",layouts:["Character Chat","Life Simulator"]},
  explorer:{nav:"side",overlay:"left",icons:"ornate",font:"mono",layouts:["World Explorer","Relationship Web"]}
};
const uiDesigns=Object.fromEntries(Object.entries(designs).flatMap(([style,design])=>design.layouts.map(name=>[name,style])));
const playStyles={
 "RPG Adventure":"rpg","Visual Novel":"cinema","Novel Reader":"reader","Life Simulator":"journal",
 "World Explorer":"explorer","Character Chat":"chat","Interactive Story":"interactive","Creator Studio":"studio"
};
function apply(){const c=resolved(),pal=palettes()[c.theme],r=document.documentElement;
  const properties=['--bg','--card','--card2','--accent','--accent2','--border','--hdr','--grad','--text','--muted','--onacc','--dlg','--ub','--ubb','--ubt','--em','color-scheme'];
  for(const k of properties)r.style.removeProperty(k);
  if(pal){
    const [bg,card,accent]=pal;
    const luminance=hex=>[.2126,.7152,.0722].reduce((sum,weight,i)=>{
      const channel=parseInt(hex.slice(1+i*2,3+i*2),16)/255;
      return sum+weight*(channel<=.04045?channel/12.92:((channel+.055)/1.055)**2.4);
    },0);
    const light=luminance(card)>.35;
    const ink=light?'#171422':'#f5f1f4', muted=light?'#48404c':'#c8c2ce';
    const tokens={'--bg':bg,'--card':card,'--card2':card,'--accent':accent,'--accent2':accent,
      '--border':accent+'66','--hdr':bg,'--grad':'linear-gradient(145deg,'+bg+','+card+')',
      '--text':ink,'--muted':muted,'--onacc':luminance(accent)>.179?'#000':'#fff',
      '--dlg':ink,'--ub':card,'--ubb':accent+'66','--ubt':ink,'--em':muted,'color-scheme':light?'light':'dark'};
    for(const [k,v] of Object.entries(tokens))r.style.setProperty(k,v);
  }
  if(pal)r.dataset.sfThemeTreatment=treatments[c.theme]||'soft';
  else delete r.dataset.sfThemeTreatment;
  const design=uiDesigns[c.layout];
  const motion=c.motion;
  const format=playStyles[c.format];
  if(design)r.dataset.sfDesign=design;
  else delete r.dataset.sfDesign;
  if(format)r.dataset.sfPlay=format;
  else delete r.dataset.sfPlay;
  applyInterfaceLook(r,r.dataset.theme,designs[design],c.interfaceLook);
  const customKeys=['bg','card','accent','text'];
  for(const k of customKeys)if(/^#[0-9a-f]{6}$/i.test(c[k]||''))r.style.setProperty('--'+k,c[k]);
  for(const [key,values] of Object.entries({icons:['line','rounded','solid','duotone','pixel','sketch','ink','runic','neon','engraved','geometric','sticker','glyph','blueprint'],spacing:['compact','cozy','roomy'],borders:['none','thin','bold'],nav:['bottom','top','side','floating'],panel:['right','left','bottom','overlay'],contrast:['normal','high']})){
    const attr='sf'+key[0].toUpperCase()+key.slice(1);if(values.includes(c[key]))r.dataset[attr]=c[key];else delete r.dataset[attr];
  }
  const bounded=(key,min,max,unit)=>{const n=c[key];if(typeof n==='number'&&Number.isFinite(n))r.style.setProperty('--sf-'+key,Math.max(min,Math.min(max,n))+unit);else r.style.removeProperty('--sf-'+key)};
  const font=typeof c.font==='string'?c.font.trim():'';
  const family=/^[\p{L}\p{N}][\p{L}\p{N} -]{0,79}$/u.test(font)?font:null;
  if(family)r.style.setProperty('--sf-custom-font',/^(serif|sans-serif|monospace|system-ui|cursive|fantasy)$/i.test(family)?family:JSON.stringify(family)+', system-ui');
  else r.style.removeProperty('--sf-custom-font');
  bounded('radius',0,24,'px');bounded('fontScale',.8,1.4,'');bounded('transparency',0,.6,'');
  if(c.contrast==='high')r.style.setProperty('--sf-transparency','0');
  r.dataset.sfReducedMotion=String(!!c.reducedMotion||motion==='none'||matchMedia('(prefers-reduced-motion: reduce)').matches);
  r.dataset.sfMotion=r.dataset.sfReducedMotion==='true'?'off':motion;
  r.dataset.sfLayout=c.layout.replace(/[^a-z]/gi,'').toLowerCase();r.dataset.sfFormat=c.format.replace(/[^a-z]/gi,'').toLowerCase();
}
function el(tag,props={},...kids){const x=document.createElement(tag);for(const [k,v] of Object.entries(props)){if(k==='text')x.textContent=v;else if(k==='class')x.className=v;else if(k==='on')x.addEventListener('click',v);else x.setAttribute(k,v)}kids.flat().forEach(k=>x.append(k));return x}
function selector(label,values,current,change){const s=el('select',{'aria-label':label});values.forEach(v=>s.append(el('option',{value:v,text:v})));s.value=current;s.addEventListener('change',()=>change(s.value));return el('label',{},el('span',{text:label}),s)}
function close(){document.getElementById('sf48-modal')?.remove()}
function open(){close();const backdrop=el('div',{id:'sf48-modal',role:'dialog','aria-modal':'true','aria-label':'Appearance Studio'});const panel=el('div',{class:'sf48-panel'}),heading=el('div',{class:'sf48-head'},el('strong',{text:'Appearance'}),el('button',{text:'Close',on:close}));panel.append(heading,el('p',{class:'sf48-muted',text:'Preview your menu and reading layout as you make changes.'}));
const scope=el('select',{'aria-label':'Settings scope'});let id=storyId();[['global','Global defaults'],...(id?[['story','This story']]:[]),['device','This '+device()+' device']].forEach(([v,t])=>scope.append(el('option',{value:v,text:t})));panel.append(el('label',{},el('span',{text:'Apply settings to'}),scope));
const controls=el('div',{class:'sf48-controls'});
const sample=el('div',{class:'sf48-sample','aria-hidden':'true'},
  el('div',{class:'turn ai'},el('div',{class:'who',text:'Narrator'}),el('div',{class:'body',text:'The station lights flicker as the last train rolls in.'})),
  el('div',{class:'turn user'},el('div',{class:'body',text:'I step onto the platform.'})));
panel.append(interfaceLookPreview(),sample,controls);
function target(){return scope.value==='story'?(cfg.stories[id]||(cfg.stories[id]={})):scope.value==='device'?(cfg.devices[device()]||(cfg.devices[device()]={})):cfg.global}
function redraw(){
  controls.replaceChildren();
  const current=target();
  const change=(key,value)=>{current[key]=value;save();apply()};
  const presetControls=[
    ['Theme',[appTheme,...Object.keys(palettes())],'theme'],
    ['UI design',['Use Settings layout',...layouts],'layout'],
    ['Reading presentation',['Use story format',...formats],'format'],
    ['Motion',['off','subtle','cinematic'],'motion']
  ];
  for(const [label,values,key] of presetControls){
    const inherit='Inherit global setting';
    const choices=scope.value==='global'?values:[inherit,...values];
    controls.append(selector(label,choices,current[key]||(scope.value==='global'?defaults[key]:inherit),value=>{
      if(value===inherit){delete current[key];save();apply()}
      else change(key,value);
    }));
  }
  for(const [key,label,options] of LOOK_CONTROLS){
    controls.append(fld(label,sel((scope.value==="global"?DB.interfaceLook:current.interfaceLook)?.[key]||"",[["","Use layout or inherited setting"],...options],value=>{
      if(scope.value==="global"){DB.interfaceLook={...DB.interfaceLook,[key]:value};window.save?.();apply();return}
      const overrides={...current.interfaceLook};
      if(value)overrides[key]=value;
      else delete overrides[key];
      change('interfaceLook',overrides);
    })));
  }
}
scope.addEventListener('change',redraw);redraw();
const custom=el('div',{class:'sf48-custom'});const n=el('input',{placeholder:'Custom theme name',maxlength:'50','aria-label':'Custom theme name'}),base=el('input',{type:'color',value:'#121b30','aria-label':'Background color'}),surface=el('input',{type:'color',value:'#293955','aria-label':'Panel color'}),accent=el('input',{type:'color',value:'#d2a7ff','aria-label':'Accent color'});
custom.append(el('h3',{text:'Create a custom theme'}),n,el('div',{class:'sf48-colors'},base,surface,accent),el('button',{text:'Save custom theme',on:()=>{const name=n.value.trim();if(!name||name.length>50||palettes()[name]){alert('Choose a unique name (1–50 characters).');return}if(Object.keys(cfg.custom).length>=100){alert('Custom theme limit reached.');return}cfg.custom[name]=[base.value,surface.value,accent.value];target().theme=name;save();apply();redraw();n.value=''}}));panel.append(custom);
const actions=el('div',{class:'sf48-actions'});actions.append(el('button',{text:'Export themes',on:()=>{const blob=new Blob([JSON.stringify({format:'story-forge-visual-presets',version:1,custom:cfg.custom},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a',{href:url,download:'story-forge-visual-presets.json'});a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}}));const inp=el('input',{type:'file',accept:'.json,application/json','aria-label':'Import theme presets'});inp.addEventListener('change',async()=>{const f=inp.files[0];if(!f||f.size>100000){alert('Theme file must be under 100 KB.');return}try{const d=JSON.parse(await f.text());if(d.format!=='story-forge-visual-presets'||d.version!==1||!d.custom||typeof d.custom!=='object'||Object.keys(d.custom).length>100)throw Error();let added=0;for(const [k,v] of Object.entries(d.custom)){if(!valid(k)||!k.trim()||!Array.isArray(v)||v.length!==3||!v.every(x=>typeof x==='string'&&/^#[0-9a-f]{6}$/i.test(x))||themes[k])continue;cfg.custom[k]=v;added++}save();redraw();alert('Imported '+added+' theme preset(s).')}catch(e){alert('Invalid Story Forge theme file.')}inp.value=''});actions.append(inp);panel.append(actions,el('p',{class:'sf48-muted',text:'UI designs change navigation and layout. Reading presentation changes how story turns are displayed.'}));backdrop.append(panel);backdrop.addEventListener('click',e=>{if(e.target===backdrop)close()});document.body.append(backdrop);panel.querySelector('button').focus()}
function addButton(){const head=document.querySelector('#app > header');if(!head||head.querySelector('.sf48-launch'))return;const b=el('button',{class:'sf48-launch',text:'Appearance',on:open});head.append(b)}
const oldRender=render;render=function(...args){const result=oldRender.apply(this,args);apply();addButton();return result};
const oldGo=go;go=function(...args){const r=oldGo.apply(this,args);apply();return r};
addEventListener('resize',apply);apply();
/* reload(): re-read storage after the appearance adapters (ap*) change it, so this module never overwrites them with a stale copy. */
window.SFVisualV48={themes:names.slice(),layouts:layouts.slice(),formats:formats.slice(),open,apply,reload(){load();apply()},palette:n=>palettes()[n]||null,KEY,useAppTheme(){if(cfg.global.theme!==appTheme){cfg.global.theme=appTheme;save()}apply()}};
})();