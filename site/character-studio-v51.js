/* v51 character profile editor and read-only relationships; no memory engine hooks */
(()=>{'use strict';
const mk=(tag,cls,txt)=>{const x=document.createElement(tag);if(cls)x.className=cls;if(txt!==undefined)x.textContent=String(txt);return x};
const put=(p,...cs)=>{cs.flat().forEach(c=>{if(c)p.append(c)});return p};
const str=(v,n=500)=>String(v==null?'':v).slice(0,n);
let modal=null;
function currentSession(){try{return view.n==='chat'?DB.sessions.find(x=>x.id===view.id):null}catch{return null}}
function currentStory(){try{const s=currentSession();return s?getStory(s.storyId):view.n==='story'?getStory(view.id):null}catch{return null}}
function close(){modal?.remove();modal=null}
function field(name,value,limit=150,multi=false){const l=mk('label','',name),i=mk(multi?'textarea':'input');if(!multi)i.type='text';i.maxLength=limit;i.value=str(value,limit);put(l,i);return [l,i]}
function button(label,fn){const b=mk('button','',label);b.type='button';b.addEventListener('click',fn);return b}
function open(initial='Profiles'){
 close();const mask=mk('div','sf51-mask'),dialog=mk('section','sf51-dialog');modal=mask;dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');dialog.setAttribute('aria-label','Character Studio');
 const head=mk('div','sf51-head');put(head,mk('h2','','Character Studio'),button('Close',close));put(dialog,head,mk('p','sf51-muted','Manage saved character profiles or explore relationships already recorded in this story. Profile edits do not rewrite past story turns or memories.'));
 const tabs=mk('div','sf51-tabs'),area=mk('div');let tab=initial;const tabspec=['Profiles','Relationships'];
 function paint(){area.replaceChildren();Array.from(tabs.children).forEach(b=>b.setAttribute('aria-selected',String(b.textContent===tab)));if(tab==='Profiles')profiles();else relationships()}
 tabspec.forEach(t=>tabs.append(button(t,()=>{tab=t;paint()})));put(dialog,tabs,area);mask.append(dialog);mask.addEventListener('click',e=>{if(e.target===mask)close()});mask.addEventListener('keydown',e=>{if(e.key==='Escape')close()});document.body.append(mask);paint();head.lastChild.focus();
 function profiles(){const shell=mk('div','sf51-columns'),list=mk('div','sf51-list'),detail=mk('div');put(shell,list,detail);area.append(shell);const chars=Array.isArray(DB.chars)?DB.chars:[];let selected=chars[0]?.id||null;
  function show(){list.replaceChildren();detail.replaceChildren();const newBtn=button('+ New character',()=>{selected=null;show()});list.append(newBtn);chars.forEach(c=>{const b=button(str(c.name||'Unnamed',50),()=>{selected=c.id;show()});b.setAttribute('aria-selected',String(selected===c.id));list.append(b)});
   const c=chars.find(x=>x.id===selected)||{};const form=mk('form','sf51-fields');const [nameL,name]=field('Character name',c.name,100),[descL,desc]=field('Description',c.desc,1500,true),[traitL,trait]=field('Personality / traits',c.trait,800,true);put(form,nameL,descL,traitL);
   const actions=mk('div','sf51-actions'),status=mk('p','sf51-muted');put(actions,button(selected?'Save profile':'Create profile',()=>{const n=name.value.trim();if(!n){status.textContent='A name is required.';return}if(!Array.isArray(DB.chars))DB.chars=[];const existing=DB.chars.find(x=>x.id===selected);if(existing){existing.name=n;existing.desc=desc.value;existing.trait=trait.value}else{if(DB.chars.length>=30){status.textContent='The current app supports up to 30 saved avatars.';return}const id=typeof uid==='function'?uid():'char-'+Date.now();DB.chars.unshift({id,name:n,desc:desc.value,trait:trait.value});selected=id}try{save();status.textContent='Profile saved locally.';show()}catch{status.textContent='Unable to save the profile.'}}));
   if(selected)actions.append(button('Duplicate',()=>{if(DB.chars.length>=30){status.textContent='The avatar limit is 30.';return}const cp={...c,id:typeof uid==='function'?uid():'char-'+Date.now(),name:str((c.name||'Character')+' copy',100)};DB.chars.unshift(cp);selected=cp.id;save();show()}));
   put(detail,form,actions,status,mk('p','sf51-muted','Existing character artwork and other profile fields are retained when editing. Profile changes apply to saved avatar templates, not existing sessions.'));}
  show();
 }
 function relationships(){const se=currentSession(),st=currentStory(),cast=se?.cast&&typeof se.cast==='object'?se.cast:null;const entries=cast?Object.entries(cast):[];
  put(area,mk('div','sf51-note','This explorer shows recorded character relationships only. It does not infer friendships, calculate bonds, or modify memory.'));
  if(!se){area.append(mk('p','sf51-muted','Open an active story session to explore its recorded character relationships.'));return}
  const intro=mk('p','sf51-muted','Story: '+str(st?.title||'Current session',90)+' · '+entries.length+' recorded characters');area.append(intro);
  if(!entries.length){area.append(mk('p','sf51-muted','No relationship records are available yet for this session.'));return}
  const grid=mk('div','sf51-relations');entries.slice(0,80).forEach(([name,raw])=>{const r=raw&&typeof raw==='object'?raw:{},card=mk('article','sf51-card');put(card,mk('strong','',str(name,90)));if(r.r)card.append(mk('p','','Role: '+str(r.r,200)));if(r.a)card.append(mk('p','','Recorded connection: '+str(r.a,300)));if(r.l)card.append(mk('p','','Details: '+str(r.l,250)));if(Array.isArray(r.t)&&r.t.length)card.append(mk('p','','Recorded notes: '+r.t.slice(0,3).map(x=>str(typeof x==='string'?x:JSON.stringify(x),120)).join(' · ')));if(!r.r&&!r.a&&!r.l&&!(Array.isArray(r.t)&&r.t.length))card.append(mk('p','','No relationship details recorded.'));grid.append(card)});area.append(grid);
 }
}
function decorate(){const header=document.querySelector('#app>header');if(!header||header.querySelector('.sf51-launch'))return;if(!['home','chat','story','settings'].includes(view.n))return;const b=button('Characters',()=>open('Profiles'));b.className='sf51-launch';header.append(b)}
const previous=render;render=function(...args){const result=previous.apply(this,args);decorate();return result};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',decorate);else decorate();
window.SFCharacterStudioV51={open,close};
})();
