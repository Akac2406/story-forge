/* Story Forge v50: read-only dashboard. No memory, model, story mutation or paid operations. */
(()=>{'use strict';
const el=(tag,cls,txt)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(txt!==undefined)n.textContent=String(txt);return n};
const add=(parent,...children)=>{children.flat().forEach(c=>c&&parent.append(c));return parent};
const short=(s,n=110)=>String(s||'').slice(0,n);
function session(){try{return view.n==='chat'?DB.sessions.find(s=>s.id===view.id):null}catch{return null}}
function story(){try{const se=session();return se?getStory(se.storyId):view.n==='story'?getStory(view.id):null}catch{return null}}
function person(name,subtitle){const row=el('div','sf50-person'),avatar=el('span','sf50-avatar',(name||'?').slice(0,1).toUpperCase()),meta=el('div');add(meta,el('strong','',short(name||'Unnamed',55)),el('small','',short(subtitle||'',100)));return add(row,avatar,meta)}
function tile(name){return add(el('section','sf50-tile'),el('h3','',name))}
function empty(t){return el('p','sf50-empty',t)}
function close(){document.querySelector('.sf50-backdrop')?.remove()}
function open(){close();const se=session(),st=story(),overlay=el('div','sf50-backdrop'),panel=el('section','sf50-panel');overlay.setAttribute('role','dialog');overlay.setAttribute('aria-modal','true');overlay.setAttribute('aria-label','Story dashboard');
 const head=el('div','sf50-top'),closeBtn=el('button','','Close');closeBtn.addEventListener('click',close);add(head,el('h2','','Story Dashboard'),closeBtn);add(panel,head,el('p','sf50-lead','Read-only overview of available story information. Empty sections indicate information not recorded yet. Nothing here changes story memories.'));
 const nav=el('div','sf50-nav'),grid=el('div','sf50-grid');
 const pages=['Overview','Characters','Progress'];let active='Overview';
 function build(){grid.replaceChildren();for(const btn of nav.children)btn.setAttribute('aria-selected',String(btn.textContent===active));
  if(active==='Overview'){
   const summary=tile('Current story');add(summary,person(st?.title||st?.charName||'Untitled',st?.tag||st?.style||'Interactive story'));if(st?.desc)add(summary,empty(short(st.desc,230)));grid.append(summary);
   const player=tile('Your character');if(se?.char?.name)add(player,person(se.char.name,se.char.desc||se.char.trait||''));else add(player,empty('Open a story session to view your character.'));grid.append(player);
   const progress=tile('Story progress');add(progress,el('div','sf50-stat','Recorded turns: '+(Array.isArray(se?.turns)?se.turns.length:0)));if(se?.life)add(progress,el('div','sf50-stat','Age: '+(se.life.age??'—')));if(se?.ending)add(progress,empty('Current ending: '+short(se.ending)));grid.append(progress);
   const settings=tile('Appearance');add(settings,empty('Your theme, reading layout and gameplay format can be changed in Appearance Studio.'));grid.append(settings);
  }else if(active==='Characters'){
   const cast=tile('Story characters'),members=Array.isArray(st?.cast0)?st.cast0:[];if(members.length)members.slice(0,30).forEach(c=>cast.append(person(c.n||c.name||'Unnamed',c.role||c.hook||c.looks||'')));else add(cast,empty('No character roster recorded for this story.'));grid.append(cast);
   const avatars=tile('Saved avatars'),chars=Array.isArray(DB.chars)?DB.chars:[];if(chars.length)chars.slice(0,30).forEach(c=>avatars.append(person(c.name,c.trait||c.desc||'')));else add(avatars,empty('No saved avatars.'));grid.append(avatars);
  }else{
   const stats=tile('Character statistics'),values=se?.stats&&typeof se.stats==='object'?Object.entries(se.stats):[];if(values.length)values.slice(0,24).forEach(([key,value])=>{const r=el('div','sf50-stat');add(r,el('span','',short(key,35)),el('b','',String(value)));stats.append(r);if(typeof value==='number'&&Number.isFinite(value)){const m=el('div','sf50-meter'),bar=el('i');bar.style.width=Math.max(0,Math.min(100,value))+'%';m.append(bar);stats.append(m)}});else add(stats,empty('No numeric statistics have been recorded.'));grid.append(stats);
   const events=tile('Recent story turns'),turns=Array.isArray(se?.turns)?se.turns.filter(t=>t&&t.text):[];if(turns.length)turns.slice(-5).reverse().forEach(t=>events.append(person(t.role==='user'?'You':'Narrator',short(t.text,100))));else add(events,empty('No story turns yet.'));grid.append(events);
  }
 }
 for(const name of pages){const btn=el('button','',name);btn.type='button';btn.addEventListener('click',()=>{active=name;build()});nav.append(btn)}add(panel,nav,grid);build();overlay.append(panel);overlay.addEventListener('click',e=>{if(e.target===overlay)close()});overlay.addEventListener('keydown',e=>{if(e.key==='Escape')close()});document.body.append(overlay);closeBtn.focus();}
function decorate(){const head=document.querySelector('#app>header');if(!head||head.querySelector('.sf50-open'))return;if(!['chat','story'].includes(view.n))return;const btn=el('button','sf50-open','Dashboard');btn.type='button';btn.addEventListener('click',open);head.append(btn)}
const old=render;render=function(...args){const result=old.apply(this,args);decorate();return result};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',decorate);else decorate();
window.SFCharacterV50={open,close};
})();
