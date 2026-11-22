/* Story Forge v52: read-only relationship map and artwork roster; no story/memory writes. */
(()=>{'use strict';
const NS='http://www.w3.org/2000/svg';
const node=(tag,cls,txt)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(txt!==undefined)n.textContent=String(txt);return n};
const svg=(tag,attrs,txt)=>{const n=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,String(v));if(txt!==undefined)n.textContent=String(txt);return n};
const cut=(x,n=100)=>String(x==null?'':x).slice(0,n);
let modal;
function active(){try{return view.n==='chat'?DB.sessions.find(s=>s.id===view.id):null}catch{return null}}
function artwork(c){const fields=['image','img','avatar','portrait','art','imageData','photo'];for(const k of fields){const v=c?.[k];if(typeof v==='string'&&/^(data:image\/(?:png|jpeg|webp|gif);base64,|blob:|https?:\/\/)/i.test(v))return v}return null}
function close(){modal?.remove();modal=null}
function open(){
 close();const shade=node('div','sf52-shade'),box=node('section','sf52-modal'),head=node('div','sf52-head'),title=node('h2','','Relationship Map & Portraits'),dismiss=node('button','','Close');
 dismiss.type='button';dismiss.onclick=close;head.append(title,dismiss);box.append(head);
 const intro=node('p','sf52-note','Read-only views of recorded character information. Lines represent characters appearing in the same story session, not confirmed friendships or family ties. No AI generation or story changes.');
 box.append(intro);
 const tools=node('div','sf52-tools'),body=node('div'),session=active(),cast=session?.cast&&typeof session.cast==='object'&&!Array.isArray(session.cast)?Object.entries(session.cast).slice(0,24):[],saved=Array.isArray(DB.chars)?DB.chars.slice(0,30):[];
 let mode='map';
 function btn(label,key){const b=node('button','',label);b.type='button';b.onclick=()=>{mode=key;draw()};b.dataset.mode=key;tools.append(b)}
 btn('Relationship map','map');btn('Character portraits','portraits');box.append(tools,body);
 function draw(){
  body.replaceChildren();for(const b of tools.children)b.setAttribute('aria-pressed',String(b.dataset.mode===mode));
  if(mode==='map'){
   if(!session){body.append(node('p','sf52-note','Open an active story session to view its recorded cast.'));return}
   if(!cast.length){body.append(node('p','sf52-note','This session has no recorded cast yet.'));return}
   const width=740,height=Math.max(330,Math.ceil(cast.length/8)*155+95),graph=svg('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':'Character map: recorded characters connected to the current story'});
   const cx=width/2,cy=height/2;
   const center=svg('circle',{cx,cy,r:42,class:'sf52-node'});graph.append(center,svg('text',{x:cx,y:cy+4,'text-anchor':'middle',class:'sf52-label'},'Story'));
   cast.forEach(([name,raw],i)=>{const angle=(i/cast.length)*Math.PI*2-Math.PI/2,rx=Math.min(290,width*.38),ry=Math.max(105,height*.36),x=cx+Math.cos(angle)*rx,y=cy+Math.sin(angle)*ry;
    graph.append(svg('line',{x1:cx,y1:cy,x2:x,y2:y,class:'sf52-line'}));
    graph.append(svg('circle',{cx:x,cy:y,r:26,class:'sf52-node'}));
    graph.append(svg('text',{x,y:y+5,'text-anchor':'middle',class:'sf52-label'},cut(name,2).toUpperCase()));
    graph.append(svg('text',{x,y:y+44,'text-anchor':'middle',class:'sf52-label'},cut(name,17)));
    const r=raw&&typeof raw==='object'?raw:{};if(r.r)graph.append(svg('text',{x,y:y+58,'text-anchor':'middle',class:'sf52-sub'},cut(r.r,24)));
   });
   const wrapper=node('div','sf52-canvas');wrapper.append(graph);body.append(wrapper);
   body.append(node('p','sf52-note',`${cast.length} recorded characters. Connections indicate shared story participation only; relationship types are not inferred.`));
  }else{
   if(!saved.length){body.append(node('p','sf52-note','No saved character profiles yet. Add profiles in Character Studio.'));return}
   const grid=node('div','sf52-grid');
   for(const c of saved){const card=node('article','sf52-person'),src=artwork(c),portrait=src?node('img','sf52-portrait'):node('div','sf52-portrait sf52-initial',cut(c.name||'?',1).toUpperCase());
    if(src){portrait.src=src;portrait.alt=cut(c.name||'Character',80)+' portrait';portrait.loading='lazy';portrait.onerror=()=>portrait.replaceWith(node('div','sf52-portrait sf52-initial',cut(c.name||'?',1).toUpperCase()))}
    card.append(portrait,node('strong','',cut(c.name||'Unnamed character',90)),node('p','',cut(c.trait||c.desc||'No profile notes yet.',220)));grid.append(card)}
   body.append(grid);
  }
 }
 draw();shade.append(box);shade.onclick=e=>{if(e.target===shade)close()};shade.onkeydown=e=>{if(e.key==='Escape')close()};document.body.append(shade);modal=shade;dismiss.focus();
}
function decorate(){const header=document.querySelector('#app>header');if(!header||header.querySelector('.sf52-launch')||!['home','chat','story'].includes(view.n))return;const b=node('button','sf52-launch','Map & Art');b.type='button';b.onclick=open;header.append(b)}
const prev=render;render=function(...args){const out=prev.apply(this,args);decorate();return out};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',decorate);else decorate();
window.SFRelationshipV52={open,close};
})();
