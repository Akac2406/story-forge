import '../story-forge-pwa/memory-engine.js';
const M=globalThis.SFMemory;let f=0;const ok=(c,m)=>{console.log((c?'PASS ':'FAIL ')+m);if(!c)f++};
let mem=M.init();
M.record(mem,M.parseMeta('[[META]]\nSCENE: chapel | Ilse, Aled | morning'),{t:1});
const p=M.parseMeta('[[META]]\nEVENTS: 2 | threat | unknown | yard | a man paces in the yard | none\nLEARNED: unknown: something\nSCENE: unknown | Ilse, Aled | unknown');
ok(p.events.length===1&&p.events[0].who.length===0,'unknown participant dropped, event kept');
ok(p.learned.length===0,'LEARNED for unknown dropped');
M.record(mem,p,{t:3});
ok(mem.scene.where==='chapel'&&mem.scene.when==='morning'&&mem.scene.who.join()==='Ilse,Aled','unknown where/when keep the stored scene, who still updates');
ok(!mem.chars.unknown,'no character called unknown');
console.log(f+' failure(s)');process.exit(f?1:0)
