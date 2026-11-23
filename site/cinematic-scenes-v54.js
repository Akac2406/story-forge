/* Story Forge v54: user-provided scene artwork and character staging. Presentation only. */
(()=>{'use strict';
const KEY='sf-v54-scene-presets';const max=1100000;let db={};try{const o=JSON.parse(localStorage.getItem(KEY)||'{}');if(o&&typeof o==='object'&&!Array.isArray(o))db=o}catch{}
const E=(t,c,txt)=>{const e=document.createElement(t);if(c)e.className=c;if(txt!==undefined)e.textContent=String(txt);return e};
const session=()=>{try{return view.n==='chat'?DB.sessions.find(s=>s.id===view.id):null}catch{return null}};
const artwork=c=>['pic','th','image','img','avatar','portrait','art','imageData','photo'].map(key=>c?.[key])
  .find(value=>typeof value==='string'&&/^(data:image\/(?:png|jpeg|webp|gif);base64,|blob:|https?:\/\/)/i.test(value))||'';
const config=()=>db[String(view.id)]||{};
const portableImage=value=>typeof value==='string'&&value.length<=max&&
  /^data:image\/(?:png|jpeg|webp|gif);base64,[A-Za-z0-9+/]+=*$/.test(value);
function selectedPortrait(cfg,portraits){
  return portraits.get(cfg.portrait)||(cfg.portrait&&portableImage(cfg.portraitImage)?cfg.portraitImage:'');
}
const BACKGROUND=['top','center','bottom'], PORTRAIT=['left','center','right'];
const BRIGHTNESS=['soft','balanced','bright'], PORTRAIT_SIZE=['small','medium','large'];
function framing(preset){
  const allowed=(value,choices)=>choices.includes(value)?value:choices[1];
  return {
    backgroundPosition:allowed(preset.backgroundPosition,BACKGROUND),
    backgroundLight:allowed(preset.backgroundLight,BRIGHTNESS),
    portraitPosition:allowed(preset.portraitPosition,PORTRAIT),
    portraitSize:allowed(preset.portraitSize,PORTRAIT_SIZE),
  };
}
function persist(id,obj){
  const next={...db,[id]:obj};
  try{localStorage.setItem(KEY,JSON.stringify(next));db=next;return true}catch{return false}
}
function cast(se=session()){
  const st=se&&getStory(se.storyId),all=[];
  if(se?.char?.name)all.push(se.char);
  for(const [name,character] of Object.entries(se?.cast||{}))all.push({...character,name});
  for(const character of Array.isArray(st?.cast0)?st.cast0:[])all.push({...character,name:character.n||character.name});
  if(Array.isArray(DB.chars))all.push(...DB.chars);
  const portraits=new Map();
  for(const character of all){
    const src=artwork(character);
    if(character?.name&&src&&!portraits.has(character.name))portraits.set(character.name,src);
  }
  return new Map([...portraits].slice(0,100));
}
function sceneArtwork(cfg,portraits){
  const wrap=E('section','sf54-stage');
  wrap.setAttribute('aria-label','Scene artwork');
  const layout=framing(cfg);
  Object.assign(wrap.dataset,layout);
  if(cfg.background){
    const img=E('img','sf54-bg');
    img.src=cfg.background;img.alt='';wrap.append(img);
  }
  const src=selectedPortrait(cfg,portraits);
  if(src){
    const img=E('img','sf54-portrait');
    img.src=src;img.alt=cfg.portrait+' portrait';wrap.append(img);
  }
  if(cfg.caption)wrap.append(E('div','sf54-caption',cfg.caption));
  return wrap;
}
function readerPreset(se){
  const preset=Object.hasOwn(db,se.id)?db[se.id]:null;
  if(!preset?.background&&!preset?.portrait&&!preset?.caption)return null;
  return {...preset,...framing(preset),selectedImage:preset.portrait?selectedPortrait(preset,cast(se)):''};
}
function cinematicMode(){
  return view.n==='chat'&&DB.uiLayout==='illustrated'&&DB.readerPresentation==='cinematic';
}
function refreshScene(){
  if(cinematicMode())rerender();
  else stage();
}
function stage(){
  document.querySelector('#app .sf54-stage')?.remove();
  if(view.n!=='chat'||cinematicMode())return;
  const cfg=config(),target=document.querySelector('#log'),portraits=cast();
  if(target&&(cfg.background||cfg.caption||selectedPortrait(cfg,portraits)))target.before(sceneArtwork(cfg,portraits));
}
let overlay=null;
function close(){overlay?.remove();overlay=null}
function open(){
  if(view.n!=='chat')return;
  close();
  const id=String(view.id),cfg=config(),portraits=cast();
  if(cfg.portrait&&!portraits.has(cfg.portrait)&&portableImage(cfg.portraitImage))portraits.set(cfg.portrait,cfg.portraitImage);
  const draft={background:cfg.background||'',portrait:cfg.portrait||'',caption:cfg.caption||'',...framing(cfg)};
  const importedPortrait=cfg.portraitImage;
  const shade=E('div','sf54-backdrop'),panel=E('section','sf54-panel'),head=E('h2','','Scene & Portrait Studio');
  head.id='sf54-title';
  panel.setAttribute('role','dialog');panel.setAttribute('aria-modal','true');panel.setAttribute('aria-labelledby',head.id);
  const preview=E('div','sf54-preview');
  const paint=()=>preview.replaceChildren(draft.background||draft.caption||portraits.has(draft.portrait)?
    sceneArtwork(draft,portraits):E('p','sf54-note','Add a background or choose a portrait to preview the scene.'));
  const field=(label,input)=>{const box=E('label','',label);box.append(input);return box};
  const select=(label,key,options)=>{
    const input=E('select');
    for(const [value,title] of options){
      const option=E('option','',title);option.value=value;input.append(option);
    }
    input.value=draft[key];
    input.onchange=()=>{draft[key]=input.value;paint()};
    return field(label,input);
  };
  const choice=values=>values.map(value=>[value,value[0].toUpperCase()+value.slice(1)]);
  const file=E('input');
  file.type='file';file.accept='image/png,image/jpeg,image/webp';
  const caption=E('input');
  caption.type='text';caption.maxLength=120;caption.value=draft.caption;
  caption.oninput=()=>{draft.caption=caption.value.slice(0,120);paint()};
  const note=E('p','sf54-note');
  note.setAttribute('role','status');
  const clearBackground=E('button','','Remove background'),clear=E('button','','Clear scene');
  const cancel=E('button','','Cancel'),save=E('button','','Save scene');
  for(const button of [clearBackground,clear,cancel,save])button.type='button';
  let selection=0;
  clearBackground.onclick=()=>{
    ++selection;draft.background='';file.value='';save.disabled=false;note.textContent='';paint();
  };
  file.onchange=async()=>{
    const request=++selection,chosen=file.files?.[0];
    if(!chosen){save.disabled=false;note.textContent='';return}
    save.disabled=true;note.textContent='Preparing preview…';
    try{
      if(!['image/png','image/jpeg','image/webp'].includes(chosen.type)||chosen.size>12e6)
        throw Error('Choose a PNG, JPEG, or WebP image under 12 MB.');
      const image=await resize(chosen);
      if(request!==selection||overlay!==shade)return;
      draft.background=image;note.textContent='';paint();
    }catch(error){
      if(request!==selection||overlay!==shade)return;
      file.value='';note.textContent=error.message||'Could not prepare the image.';
    }finally{
      if(request===selection&&overlay===shade)save.disabled=false;
    }
  };
  cancel.onclick=close;
  clear.onclick=()=>{
    if(persist(id,{})){close();refreshScene()}else note.textContent='Unable to update local storage.';
  };
  save.onclick=()=>{
    if(save.disabled)return;
    const next={...draft};
    if(draft.portrait===cfg.portrait&&portableImage(importedPortrait))next.portraitImage=importedPortrait;
    if(JSON.stringify(next).length>max){note.textContent='This image is too large to store locally. Try a smaller image.';return}
    if(!persist(id,next)){note.textContent='Browser storage is full. The previous scene is still saved.';return}
    close();refreshScene();
  };
  const row=E('div','sf54-row'),layout=E('div','sf54-row'),actions=E('div','sf54-actions');
  row.append(field('Scene background',file),select('Character portrait','portrait',[['','No portrait'],...Array.from(portraits.keys(),name=>[name,name])]));
  layout.append(select('Background crop','backgroundPosition',choice(BACKGROUND)),
    select('Background lighting','backgroundLight',choice(BRIGHTNESS)),
    select('Portrait placement','portraitPosition',choice(PORTRAIT)),
    select('Portrait size','portraitSize',choice(PORTRAIT_SIZE)),
    field('Scene caption',caption));
  actions.append(clearBackground,clear,cancel,save);
  panel.append(head,preview,row,layout,note,actions);shade.append(panel);
  shade.onclick=event=>{if(event.target===shade)close()};
  shade.onkeydown=event=>{if(event.key==='Escape')close()};
  document.body.append(shade);overlay=shade;paint();cancel.focus();
}
function resize(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onerror=()=>reject(Error('Unable to read the image.'));reader.onload=()=>{const img=new Image();img.onerror=()=>reject(Error('Unable to decode the image.'));img.onload=()=>{const scale=Math.min(1,1280/img.width,720/img.height),canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(img.width*scale));canvas.height=Math.max(1,Math.round(img.height*scale));canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);resolve(canvas.toDataURL('image/jpeg',.77))};img.src=reader.result};reader.readAsDataURL(file)})}
function decorate(){if(view.n!=='chat')return;const header=document.querySelector('#app>header');if(!header)return;const controls=E('div','sf54-controls'),btn=E('button','','Scene & Portraits');btn.type='button';btn.onclick=open;controls.append(btn,E('span','sf54-hint','Local artwork · no AI charges'));header.after(controls);stage()}
const prev=render;render=function(...args){const result=prev.apply(this,args);decorate();return result};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',decorate);else decorate();
function exportPresets(sessions, includePortraitImages=false) {
  const presets=[];
  for(const se of sessions){
    const preset=Object.hasOwn(db,se.id)?db[se.id]:null;
    if(!preset?.background&&!preset?.portrait&&!preset?.caption)continue;
    let exported=preset;
    if(includePortraitImages&&preset.portrait){
      const image=selectedPortrait(preset,cast(se));
      const withImage={...preset,portraitImage:image};
      if(portableImage(image)&&JSON.stringify(withImage).length<=max)exported=withImage;
    }
    presets.push([se.id,exported]);
  }
  return Object.fromEntries(presets);
}

function importPresets(presets, sessions) {
  if (!presets || typeof presets !== 'object' || Array.isArray(presets)) return true;
  const additions = [];
  for (const {id} of sessions) {
    if (Object.hasOwn(db, id) || !Object.hasOwn(presets, id)) continue;
    const preset = presets[id];
    if (!preset || typeof preset !== 'object' || Array.isArray(preset)) continue;
    const {background, portrait, caption} = preset;
    if (typeof background !== 'string' || background.length > max ||
        (background && !/^data:image\/(?:png|jpeg|webp);base64,[A-Za-z0-9+/]+=*$/.test(background)) ||
        typeof portrait !== 'string' || typeof caption !== 'string' || caption.length > 120) continue;
    const config = {background, portrait, caption};
    if (portrait && portableImage(preset.portraitImage)) config.portraitImage = preset.portraitImage;
    const layout = framing(preset);
    for (const key of Object.keys(layout)) {
      if (Object.hasOwn(preset, key)) config[key] = layout[key];
    }
    if (JSON.stringify(config).length > max) delete config.portraitImage;
    if (JSON.stringify(config).length <= max) additions.push([id, config]);
  }
  if (!additions.length) return true;
  const next = {...db, ...Object.fromEntries(additions)};
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
    db = next;
    return true;
  } catch {
    return false;
  }
}

window.SFScenesV54={open,close,readerPreset,exportPresets,importPresets};
})();