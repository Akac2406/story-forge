// Large universe stress test (ChatGPT integration case): 400 characters, 3,000 events. Run: node tests/fanfic_large_universe.mjs
import assert from 'node:assert/strict'; import fs from 'node:fs'; import vm from 'node:vm'; import path from 'node:path'; import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url)); const ctx = {}; ctx.globalThis = ctx; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(here, '../site/fanfic-engine.js'), 'utf8'), ctx); const F = ctx.SFFan;
const U = { v: 1, id: 'big', name: 'Big', rev: 1, chars: {}, aliases: {}, events: [], records: [], sources: [], conflicts: [], rules: {} };
for (let i = 0; i < 400; i++) { const id = 'char:big:c' + i; U.chars[id] = { id, name: 'Person ' + i, core: { personality: 'trait ' + i }, speech: {} }; U.aliases[id] = ['Person ' + i]; }
for (let i = 1; i <= 3000; i++) { const req = i > 1 ? ['ev:big:' + (i - 1)] : []; if (i > 10 && i % 7 === 0) req.push('ev:big:' + (i - 10));
  U.events.push({ id: 'ev:big:' + i, title: 'Event ' + i, summary: 'Person ' + (i % 400) + ' does thing ' + i, ch: Math.ceil(i / 6), order: i, who: ['char:big:c' + (i % 400)], requires: req, needs: [{ kind: 'alive', who: 'char:big:c' + (i % 400), value: true }], leadsTo: [] }); }
U.events.forEach(e => e.requires.forEach(r => U.events[Number(r.split(':')[2]) - 1].leadsTo.push(e.id)));
for (let i = 0; i < 2000; i++) U.records.push({ id: 'fact:big:f' + i, layer: 'universe', kind: 'fact', text: 'Fact ' + i + ' about Person ' + (i % 400), who: ['char:big:c' + (i % 400)], canon: 'source', spoilerAt: { ch: Math.ceil(i / 4) } });
const canon = { rev: 1, position: { ch: 100, order: 600 }, locks: [{ kind: 'event', id: 'ev:big:2500' }], events: { 'ev:big:700': { status: 'prevented' } }, rules: F.defaults(['oc']) };
let t = performance.now(); const cy = F.cycles(U); const tC = performance.now() - t;
t = performance.now(); const ev = F.evaluate(U, canon, { alive: {} }); const tE = performance.now() - t;
t = performance.now(); const block = F.canonFor(U, canon, { text: 'Person 5 and Person 7 at the gate', present: ['char:big:c5', 'char:big:c7'], max: 4500 }); const tP = performance.now() - t;
t = performance.now(); const v = F.validate(U, canon); const tV = performance.now() - t;
assert.equal(cy.length, 0, 'no cycles');
assert.ok(ev.status['ev:big:701'].status === 'impossible' && ev.status['ev:big:3000'].status === 'impossible', 'a prevented early event cascades down the whole chain');
assert.ok(ev.status['ev:big:2500'].status === 'protected' && ev.conflicts.some(c => c.event === 'ev:big:2500'), 'protected event far downstream becomes a conflict');
assert.ok(block.length <= 4500 && !/Fact 1999/.test(block), 'prompt block within budget and spoiler-safe');
assert.ok(v.ok, 'validates');
const total = tC + tE + tP + tV;
console.log(`large universe: cycles ${tC.toFixed(1)} ms, evaluate ${tE.toFixed(1)} ms, prompt ${tP.toFixed(1)} ms, validate ${tV.toFixed(1)} ms`);
assert.ok(total < 2000, 'all under 2 s');
console.log('fanfic large universe: passed');
