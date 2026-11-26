import assert from 'node:assert/strict';
import '../site/source-index.js';
const {candidates,search,batches,reviewExtraction}=globalThis.SFSource;
const chapters=[
 {n:1,title:'Gate',text:'Mira Vale crossed the bridge. Today Mira Vale checked the silver lock. Mira unlocked the silver lock.'},
 {n:2,title:'Later',text:'Mira found the golden archive. Mira Vale opened the golden archive.'}
];
const mira=candidates(chapters).find(x=>x.name==='Mira Vale');
assert.equal(mira.stats.mentions,5);
assert.deepEqual(mira.aliases,['Mira']);
assert.deepEqual(mira.stats,{mentions:5,first:1,last:2,chapters:2});
assert.equal(search(chapters,'golden archive',{maxChapter:1}).length,0);
assert.equal(search(chapters,'silver lock',{maxChapter:1})[0].chapter,1);
assert.equal(search(chapters,'lock',{perChapter:1}).length,1);
const batch=batches(chapters,1,1)[0];
assert.equal(batch.length,1);
const {entries}=reviewExtraction({entries:[{chapter:1,title:'Silver lock',kind:'term',text:'A lock used on the bridge.',evidence:'silver lock',private:false}]},batch);
assert.equal(entries[0].offset,chapters[0].text.indexOf('silver lock'));
assert.equal(entries[0].private,false);
const excerpt='“Mira’s  silver\nlock”';
const reviewed=reviewExtraction({entries:[
 {chapter:1,title:'Silver lock',kind:'term',text:'A lock.',evidence:`"Mira's silver lock"`},
 {chapter:1,title:'Unsupported',kind:'term',text:'Unverified.',evidence:'silver necklace'},
 {chapter:2,title:'Wrong chapter',kind:'term',text:'A lock.',evidence:'silver lock'}
]},[{n:1,text:'About '+excerpt,offset:22}]);
assert.equal(reviewed.entries.length,1);
assert.equal(reviewed.entries[0].offset,28);
assert.equal(reviewed.entries[0].length,excerpt.length);
assert.deepEqual(reviewed.rejected.map(row=>row.chapter),[1,null]);
assert.throws(()=>reviewExtraction({},batch));
const long=batches([{n:1,title:'Long',text:'x'.repeat(50000)}],1,1);
assert.equal(long.flat().map(x=>x.text).join('').length,50000);
const shifted=[
  {n:1,title:'The Silver Archive',offset:0,text:'A note on the silver lock appears in the title page note.'},
  {n:2,title:'Chapter 1',offset:25,text:'Mira checks the silver lock beside the bronze gate.'},
  {n:3,title:'Chapter 2',offset:0,text:'The archive opens under a crescent moon.'}
];
const fact={title:'The lock',kind:'term',text:'Mira examines the lock.'};
const numbered=reviewExtraction({entries:[
  {...fact,chapter:'Chapter 1',evidence:'beside the bronze gate'},
  {...fact,chapter:1,evidence:'the silver lock'},
  {...fact,sourceRef:'section-2-25',chapter:1,evidence:'the silver lock'},
  {...fact,sourceRef:'section-2-0',chapter:2,evidence:'the silver lock'},
  {...fact,sourceRef:'section-2-25',evidence:'under a crescent moon'}
]},shifted);
assert.deepEqual(numbered.entries.map(row=>row.chapter),[2,2]);
assert.equal(numbered.entries[0].offset,25+shifted[1].text.indexOf('beside the bronze gate'));
assert.match(numbered.rejected[0].why,/multiple chapters/);
assert.match(numbered.rejected[1].why,/outside/);
assert.match(numbered.rejected[2].why,/absent/);
console.log('Source indexing unit checks passed');
