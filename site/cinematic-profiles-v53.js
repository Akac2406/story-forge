/* Story Forge v53: presentation-only cinematic mode + read-only character details. */
(()=>{'use strict';
const E=(tag,cls,txt)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(txt!==undefined)e.textContent=String(txt);return e};
const clip=(v,n=500)=>String(v==null?'':v).slice(0,n);
const KEY='sf-v53-vn-preferences';let settings={};try{const raw=JSON.parse(localStorage.getItem(KEY)||'{}');if(raw&&typeof raw==='object'&&!Array.isArray(raw))settings=raw}catch{}
const session=()=>{try{return view.n==='chat'?DB.sessions.find(s=>s.id===view.id):null}catch{return null}};
const story=()=>{try{const se=session();return se?getStory(se.storyId):view.n==='story'?getStory(view.id):null}catch{return null}};
const enabled=()=>!!settings[String(view.id||'')];
function persist(){try{localStorage.setItem(KEY,JSON.stringify(settings))}catch{}}
function apply(){const on=view.n==='chat'&&enabled();document.querySelector('#app')?.classList.toggle('sf53-vn',on)}
function controls(){apply();if(view.n!=='chat')return;const log=document.querySelector('#log'),head=document.querySelector('#app>header');if(!log||!head)return;
 const tools=E('div','sf53-tools'),toggle=E('button','','Cinematic dialogue');toggle.type='button';toggle.setAttribute('aria-pressed',String(enabled()));toggle.setAttribute('aria-label','Toggle cinematic dialogue presentation');toggle.onclick=()=>{settings[String(view.id)]=!enabled();persist();apply();toggle.setAttribute('aria-pressed',String(enabled()))};
 const people=E('button','','Character profiles');people.type='button';people.onclick=open;
 tools.append(toggle,people,E('span','sf53-caption','Display only · no AI calls'));head.insertAdjacentElement('afterend',tools)
}
function image(c){for(const k of ['image','img','avatar','portrait','art','imageData','photo']){const v=c?.[k];if(typeof v==='string'&&/^(data:image\/(?:png|jpeg|webp|gif);base64,|blob:|https?:\/\/)/i.test(v))return v}return null}
let overlay=null;function close(){overlay?.remove();overlay=null}
function open(){close();const sh=E('div','sf53-overlay'),panel=E('section','sf53-dialog'),top=E('div','sf53-top'),x=E('button','','Close');x.type='button';x.onclick=close;top.append(E('h2','','Character Profiles'),x);panel.append(top,E('p','sf53-note','View existing saved character details and artwork. This panel does not change story memories or character records.'));
 const se=session(),st=story(),saved=Array.isArray(DB.chars)?DB.chars:[],items=[];
 if(se?.char?.name)items.push({name:se.char.name,description:se.char.desc||'',trait:se.char.trait||'',role:'Current player',...se.char});
 if(Array.isArray(st?.cast0))for(const c of st.cast0.slice(0,30))items.push({name:c.n||c.name||'Unnamed',role:c.role||'',description:c.hook||c.looks||'',...c});
 for(const c of saved.slice(0,30))items.push({...c,role:'Saved avatar'});
 const seen=new Set(),list=items.filter(c=>{const id=clip(c.id||c.name,100)+'|'+clip(c.role,50);if(seen.has(id))return false;seen.add(id);return true});
 if(!list.length)panel.append(E('p','sf53-note','No character profiles available yet. Add a character in Character Studio.'));
 const grid=E('div','sf53-roster'),detail=E('section','sf53-detail');detail.hidden=true;
 for(const c of list){const card=E('button','sf53-card'),src=image(c);card.type='button';if(src){const pic=E('img');pic.src=src;pic.alt=clip(c.name,80)+' artwork';pic.loading='lazy';pic.onerror=()=>pic.replaceWith(E('div','sf53-avatar',clip(c.name||'?',1)));card.append(pic)}else card.append(E('div','sf53-avatar',clip(c.name||'?',1).toUpperCase()));card.append(E('strong','',clip(c.name||'Unnamed',100)),E('small','',clip(c.role||'Character',70)));
 card.onclick=()=>{detail.replaceChildren(E('h3','',clip(c.name||'Unnamed',100)));const dl=E('dl');const fields=[['Role',c.role],['Description',c.desc||c.description||c.looks],['Personality',c.trait||c.personality],['Background',c.background],['Notes',c.notes]];let count=0;for(const [k,v] of fields){if(typeof v!=='string'||!v.trim())continue;dl.append(E('dt','',k),E('dd','',clip(v,1500)));count++}if(!count)detail.append(E('p','sf53-note','No additional profile information recorded.'));else detail.append(dl);detail.hidden=false;detail.scrollIntoView({block:'nearest',behavior:'auto'})};grid.append(card)}
 panel.append(grid,detail);sh.append(panel);sh.setAttribute('role','presentation');sh.onclick=e=>{if(e.target===sh)close()};sh.onkeydown=e=>{if(e.key==='Escape')close()};document.body.append(sh);overlay=sh;x.focus()}
const original=render;render=function(...args){const r=original.apply(this,args);controls();return r};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',controls);else controls();
window.SFCinematicV53={open,close};
})();
