/* Story Forge v54: user-provided scene artwork and character staging. Presentation only. */
(()=>{'use strict';
const KEY='sf-v54-scene-presets';const max=1100000;let db={};try{const o=JSON.parse(localStorage.getItem(KEY)||'{}');if(o&&typeof o==='object'&&!Array.isArray(o))db=o}catch{}
const E=(t,c,txt)=>{const e=document.createElement(t);if(c)e.className=c;if(txt!==undefined)e.textContent=String(txt);return e};
const session=()=>{try{return view.n==='chat'?DB.sessions.find(s=>s.id===view.id):null}catch{return null}};
const artwork=c=>{for(const k of ['image','img','avatar','portrait','art','imageData','photo']){const v=c?.[k];if(typeof v==='string'&&/^(data:image\/(?:png|jpeg|webp|gif);base64,|blob:|https?:\/\/)/i.test(v))return v}return ''};
const config=()=>db[String(view.id)]||{};
function persist(id,obj){const next={...db,[id]:obj};try{localStorage.setItem(KEY,JSON.stringify(next));db=next;return true}catch{return false}}
function cast(){const se=session(),st=se&&getStory(se.storyId),all=[];if(se?.char?.name)all.push({name:se.char.name,...se.char});if(Array.isArray(st?.cast0))for(const c of st.cast0)all.push({name:c.n||c.name||'Character',...c});if(Array.isArray(DB.chars))for(const c of DB.chars)all.push(c);return all.filter(c=>c&&c.name).slice(0,100)}
function stage(){document.querySelector('.sf54-stage')?.remove();if(view.n!=='chat')return;const cfg=config();if(!cfg.background&&!cfg.portrait)return;const target=document.querySelector('#log');if(!target)return;const wrap=E('section','sf54-stage');wrap.setAttribute('aria-label','Optional user-selected scene artwork');
 if(cfg.background){const img=E('img','sf54-bg');img.src=cfg.background;img.alt='Selected scene background';wrap.append(img)}
 if(cfg.portrait){const c=cast().find(c=>c.name===cfg.portrait),src=c&&artwork(c);if(src){const img=E('img','sf54-portrait');img.src=src;img.alt=c.name+' portrait';wrap.append(img)}}
 wrap.append(E('div','sf54-caption',cfg.caption||'Scene artwork · user-selected'));target.before(wrap)}
let overlay=null;function close(){overlay?.remove();overlay=null}
function open(){if(view.n!=='chat')return;close();const id=String(view.id),cfg={...config()},shade=E('div','sf54-backdrop'),panel=E('section','sf54-panel'),head=E('h2','','Scene & Portrait Studio');panel.append(head,E('p','sf54-note','Use your own image as a scene background, then select an existing character portrait. Artwork is displayed locally and never sent to an AI model. This does not change story memories.'));
 const row=E('div','sf54-row'),bg=E('label','','Scene background (image file)'),file=E('input');file.type='file';file.accept='image/png,image/jpeg,image/webp';bg.append(file);row.append(bg);
 const ppl=E('label','','Character portrait'),sel=E('select');const blank=E('option','','No portrait');blank.value='';sel.append(blank);for(const c of cast()){if(!artwork(c))continue;const opt=E('option','',c.name);opt.value=c.name;sel.append(opt)}sel.value=cfg.portrait||'';ppl.append(sel);row.append(ppl);panel.append(row);
 const row2=E('div','sf54-row'),cap=E('label','','Scene caption'),input=E('input');input.type='text';input.maxLength=120;input.value=cfg.caption||'';cap.append(input);row2.append(cap);panel.append(row2);
 const note=E('p','sf54-note','Images are resized locally to a maximum of 1280 × 720 pixels. Storage limits vary by browser; if saving fails, the previous scene remains unchanged. Existing story artwork is not modified.');panel.append(note);
 const actions=E('div','sf54-actions'),clear=E('button','','Clear scene'),cancel=E('button','','Cancel'),save=E('button','','Save scene');for(const b of [clear,cancel,save])b.type='button';cancel.onclick=close;clear.onclick=()=>{if(persist(id,{})){close();stage()}else note.textContent='Unable to update local storage.'};
 save.onclick=async()=>{save.disabled=true;let image=cfg.background||'';try{if(file.files?.[0]){const f=file.files[0];if(!['image/png','image/jpeg','image/webp'].includes(f.type)||f.size>12e6)throw Error('Choose a PNG, JPEG, or WebP image under 12 MB.');image=await resize(f)}const next={background:image,portrait:sel.value,caption:input.value.slice(0,120)};if(JSON.stringify(next).length>max)throw Error('This image is too large to store locally. Try a smaller image.');if(!persist(id,next))throw Error('Browser storage is full. No changes were saved.');close();stage()}catch(err){note.textContent=err.message||'Could not save image.';save.disabled=false}};
 actions.append(clear,cancel,save);panel.append(actions);shade.append(panel);shade.onclick=e=>{if(e.target===shade)close()};shade.onkeydown=e=>{if(e.key==='Escape')close()};document.body.append(shade);overlay=shade;cancel.focus()}
function resize(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onerror=()=>reject(Error('Unable to read the image.'));reader.onload=()=>{const img=new Image();img.onerror=()=>reject(Error('Unable to decode the image.'));img.onload=()=>{const scale=Math.min(1,1280/img.width,720/img.height),canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(img.width*scale));canvas.height=Math.max(1,Math.round(img.height*scale));canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);resolve(canvas.toDataURL('image/jpeg',.77))};img.src=reader.result};reader.readAsDataURL(file)})}
function decorate(){if(view.n!=='chat')return;const header=document.querySelector('#app>header');if(!header)return;const controls=E('div','sf54-controls'),btn=E('button','','Scene & Portraits');btn.type='button';btn.onclick=open;controls.append(btn,E('span','sf54-hint','Local artwork · no AI charges'));header.after(controls);stage()}
const prev=render;render=function(...args){const result=prev.apply(this,args);decorate();return result};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',decorate);else decorate();
function exportPresets(sessions) {
  return Object.fromEntries(sessions.map(({id}) => [id, Object.hasOwn(db, id) ? db[id] : null])
    .filter(([, preset]) => preset?.background || preset?.portrait || preset?.caption));
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

window.SFScenesV54={open,close,exportPresets,importPresets};
})();