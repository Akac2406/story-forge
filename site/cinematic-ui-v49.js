/* Story Forge v49: non-invasive visual enhancement only. */
(()=>{'use strict';
const h=(tag,cls,txt)=>{const x=document.createElement(tag);if(cls)x.className=cls;if(txt)x.textContent=txt;return x};
function decorate(){
 const page=document.querySelector('#app>.page'),tabs=document.querySelector('#app>.tabs');
 if(!page)return;
 if(tabs&&tabs.querySelector('button.on')?.textContent.trim()==='Discover'&&!page.querySelector('.sf49-hero')){
  const hero=h('section','sf49-hero');hero.setAttribute('aria-label','Story Forge featured');
  hero.append(h('span','sf49-kicker','YOUR UNIVERSE · YOUR STORY'),h('h2','','Infinite worlds. One imagination.'),h('p','','Explore original adventures, create your own worlds, and return to the stories that matter to you.'));
  const actions=h('div','sf49-hero-actions'),start=h('button','sf49-primary','Create a world'),browse=h('button','','Browse stories');
  start.addEventListener('click',()=>go({n:'build'}));browse.addEventListener('click',()=>page.querySelector('.grid')?.scrollIntoView({behavior:document.documentElement.dataset.sfMotion==='off'?'instant':'smooth',block:'start'}));
  actions.append(start,browse);hero.append(actions);page.prepend(hero);
 }
 if(typeof view!=='undefined'&&view.n==='chat'){
  const log=document.querySelector('#log');if(log&&!document.querySelector('.sf49-viewbar')){
   const bar=h('div','sf49-viewbar');bar.append(h('span','','Reading view'));
   const modes=[['Character RPG','RPG'],['Visual Novel','Visual Novel'],['Novel Reader','Reader'],['Immersive Cinema','Cinema']];
   const current=()=>{try{return document.documentElement.dataset.sfLayout||''}catch(e){return ''}};
   for(const [mode,label] of modes){const b=h('button','',label);b.type='button';b.setAttribute('aria-pressed',String(current()===mode.replace(/[^a-z]/gi,'').toLowerCase()));b.addEventListener('click',()=>{
    const key='sf.visual.v48';try{const raw=JSON.parse(localStorage.getItem(key));if(!raw||raw.version!==1)throw Error('No settings');
     const id=(typeof view!=='undefined'&&view.n==='chat'&&typeof DB!=='undefined')?(DB.sessions.find(s=>s.id===view.id)||{}).storyId:null;
     if(id){raw.stories=raw.stories||{};raw.stories[id]={...(raw.stories[id]||{}),layout:mode}}else{raw.global={...(raw.global||{}),layout:mode}}
     localStorage.setItem(key,JSON.stringify(raw));
     /* v48 keeps its configuration in closure; reload to synchronize safely. */
     location.reload();
    }catch(e){alert('Unable to switch reading view. Open Appearance Studio to select a layout.')}});bar.append(b)}
   log.before(bar);
  }
 }
}
const original=render;render=function(...args){const result=original.apply(this,args);decorate();return result};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',decorate);else decorate();
window.SFCinematicV49={decorate};
})();
