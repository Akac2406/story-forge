/* Story Forge v49: non-invasive visual enhancement only. */
(()=>{'use strict';
const h=(tag,cls,txt)=>{const x=document.createElement(tag);if(cls)x.className=cls;if(txt)x.textContent=txt;return x};
function readerControls(log,settings){
 const old=log.parentNode.querySelector('.sf-cv-controls');
 if(!settings.autoAdvance&&!settings.fullscreen){old?.remove();return}
 if(old?.dataset.options===JSON.stringify([settings.autoAdvance,settings.autoDelay,settings.fullscreen]))return;
 old?.remove();
 const bar=h('div','sf-cv-controls');
 bar.dataset.options=JSON.stringify([settings.autoAdvance,settings.autoDelay,settings.fullscreen]);
 if(settings.autoAdvance){
  const play=h('button','','Play saved replies');let timer=null;
  function stop(){clearTimeout(timer);timer=null;play.textContent='Play saved replies';play.setAttribute('aria-pressed','false')}
  play.type='button';stop();
  play.addEventListener('click',()=>{
   if(timer!==null){stop();return}
   const replies=[...log.querySelectorAll('.turn.ai:not(.streaming)')];let index=0;
   function step(){
    if(!bar.isConnected||document.hidden||index>=replies.length){stop();return}
    const reply=replies[index++];
    log.scrollTop+=reply.getBoundingClientRect().top-log.getBoundingClientRect().top;
    timer=setTimeout(step,settings.autoDelay*1000);
   }
   play.textContent='Pause saved replies';play.setAttribute('aria-pressed','true');step();
  });
  bar.append(play);
 }
 if(settings.fullscreen&&document.fullscreenEnabled){
  const button=h('button','','Toggle fullscreen');button.type='button';
  button.addEventListener('click',async()=>{
   try{if(document.fullscreenElement)await document.exitFullscreen();else await document.querySelector('#app').requestFullscreen()}
   catch(e){toast('Fullscreen is unavailable in this browser.')}
  });
  bar.append(button);
 }
 if(bar.children.length)log.before(bar);
}
const SCENE_KEYS=new Map();
function decorate(){
 const page=document.querySelector('#app>.page'),tabs=document.querySelector('#app>.tabs');
 /* The Discover hero needs the home page; the reader part below runs on the story view, which has no .page. */
 if(page&&tabs&&tabs.querySelector('button.on')?.textContent.trim()==='Discover'&&!page.querySelector('.sf49-hero')){
  const hero=h('section','sf49-hero');hero.setAttribute('aria-label','Story Forge featured');
  hero.append(h('span','sf49-kicker','YOUR UNIVERSE · YOUR STORY'),h('h2','','Infinite worlds. One imagination.'),h('p','','Explore original adventures, create your own worlds, and return to the stories that matter to you.'));
  const actions=h('div','sf49-hero-actions'),start=h('button','sf49-primary','Create a world'),browse=h('button','','Browse stories');
  start.addEventListener('click',()=>go({n:'build'}));browse.addEventListener('click',()=>page.querySelector('.grid')?.scrollIntoView({behavior:document.documentElement.dataset.sfMotion==='off'?'instant':'smooth',block:'start'}));
  actions.append(start,browse);hero.append(actions);page.prepend(hero);
 }
 if(typeof view==='undefined'||view.n!=='chat'){for(const k of Object.keys(document.documentElement.dataset))if(k.startsWith('sfCv'))delete document.documentElement.dataset[k]}
 if(typeof view!=='undefined'&&view.n==='chat'){
  const se=DB.sessions.find(s=>s.id===view.id),root=document.documentElement;
  if(se&&typeof cvState==='function'){
   const cv=cvState(se),c=cv.settings,scene=(typeof cvScene==='function'?cvScene(se):cv.scene)||{},reduced=c.reducedMotion||root.dataset.sfReducedMotion==='true'||matchMedia('(prefers-reduced-motion: reduce)').matches;
   for(const [k,v] of Object.entries({layout:c.layout,lighting:scene.lighting||c.lighting,overlay:scene.overlay||c.overlay,dialogue:c.dialogueBox,narration:c.narration,reveal:reduced&&c.textReveal==='typewriter'?'fade-in':c.textReveal,transition:reduced?'none':scene.transition||c.transition}))root.dataset['sfCv'+k[0].toUpperCase()+k.slice(1)]=v||'none';
   root.dataset.sfCvReduced=String(!!reduced);
   root.dataset.sfCvNameplate=String(c.nameplate!==false);
   root.dataset.sfCvHideTools=String(!!c.hideUI);
   if(reduced&&['rain','snow','embers','petals'].includes(root.dataset.sfCvOverlay))root.dataset.sfCvOverlay='none';
   const stageLog=document.querySelector('#log');document.querySelector('.sf-cv-cast')?.remove();
   if(stageLog&&cv.layout?.caps?.portraits&&typeof cvCast==='function'){
    const stage=h('section','sf-cv-cast');stage.setAttribute('aria-label','Scene characters');
    const order=['far-left','left','center','right','far-right'];
    for(const p of cvCast(se).filter(p=>p.visible!==false&&p.position!=='offscreen').sort((a,b)=>order.indexOf(a.position)-order.indexOf(b.position))){
     const src=cvExpressionArt(se,p);if(!src)continue;
     const card=h('figure','sf-cv-portrait');card.dataset.position=p.position;card.style.setProperty('--portrait-scale',Math.max(.5,Math.min(1.5,Number(p.scale)||1)));
     const img=h('img');img.src=src;img.alt=p.name;img.loading='lazy';card.append(img,h('figcaption','',p.name+' · '+(p.expression||'neutral')));stage.append(card);
    }
    if(stage.children.length)stageLog.before(stage);
   }

   const log0=document.querySelector('#log'),ref=scene.background;
   const backdrop=typeof apState==='function'?apState(se).background:null;
   const sceneArt=ref&&typeof cvArt==='function'?cvArt(se,ref):null;
   const appearanceArt=backdrop&&typeof cvArt==='function'?cvArt(se,backdrop):null;
   const src=(cv.layout?.caps?.background?sceneArt:null)||appearanceArt;
   if(log0){
    if(src)log0.style.backgroundImage='var(--sf-cv-rain,linear-gradient(transparent,transparent)),linear-gradient(#0005,#0009),url('+JSON.stringify(src)+')';
    else log0.style.removeProperty('background-image');
    const sceneKey=JSON.stringify([ref,backdrop,scene.lighting,scene.overlay,root.dataset.sfCvTransition]);
    /* Remember the last scene per playthrough, not on #log: menus re-render #log, and that must not replay the transition. */
    const lastKey=SCENE_KEYS.get(se.id);log0.dataset.sceneKey=sceneKey;
    if(lastKey!==sceneKey){
     SCENE_KEYS.set(se.id,sceneKey);
     log0.classList.remove('sf-cv-scene-enter');
     if(root.dataset.sfCvTransition!=='none'){
      requestAnimationFrame(()=>{if(log0.dataset.sceneKey===sceneKey)log0.classList.add('sf-cv-scene-enter')});
     }
    }
    readerControls(log0,c);
   }
  }
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
