import assert from 'node:assert/strict';
import '../site/source-index.js';
const {candidates,search,batches,validate}=globalThis.SFSource;
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
const entries=validate({entries:[{chapter:1,title:'Silver lock',kind:'term',text:'A lock used on the bridge.',evidence:'silver lock',private:false}]},batch);
assert.equal(entries[0].offset,chapters[0].text.indexOf('silver lock'));
assert.equal(entries[0].private,false);
assert.throws(()=>validate({entries:[{chapter:2,title:'Silver lock',kind:'term',text:'A lock.',evidence:'silver lock'}]},batch));
const long=batches([{n:1,title:'Long',text:'x'.repeat(50000)}],1,1);
assert.equal(long.flat().map(x=>x.text).join('').length,50000);
console.log('Source indexing unit checks passed');
