// Memory v2 unit tests (pure). Run: node tests/memory_v2_unit.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs'; import vm from 'node:vm'; import path from 'node:path'; import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const ctx = { globalThis: {} }; ctx.globalThis = ctx; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(here, '../site/memory-v2.js'), 'utf8'), ctx);
const M = ctx.SFMem2; let n = 0; const ok = (c, m) => { assert.ok(c, m); n++; };
const fx = JSON.parse(fs.readFileSync(path.join(here, 'fixtures/mem2-source.json'), 'utf8'));
const store = M.build(fx);
ok(M.integrity(store).ok, 'fixture builds with unique ids and valid layers');
const st = M.stats(store);
ok(M.LAYERS.every(l => st[l] > 0), 'all nine layers populated from the fixture: ' + JSON.stringify(st));
ok(store.records.some(r => r.id === 'e1' && r.layer === 'episodic'), 'existing event ids are preserved');
ok(store.records.some(r => r.id === 'f1' && r.layer === 'semantic'), 'existing fact ids are preserved');
ok(store.records.find(r => r.id === 'entry-0').lock, 'locked canon stays locked');
ok(store.records.some(r => r.layer === 'relationship' && r.who.includes('Rae') && r.who.includes('Dale')), 'bond events become a relationship record');
// knowledge boundaries
ok(M.knows(store, 'Rae').map(r => r.id).join() === 'f1', 'Rae knows only what her record links');
ok(M.knows(store, 'Dale').map(r => r.id).join() === 's1', 'Dale knows his own secret but not the forged entry');
ok(!M.knows(store, 'Dale').some(r => r.layer === 'universe') && !M.knows(store, 'Rae').some(r => r.layer === 'universe'), 'universe facts are never character knowledge by themselves');
// overlays: edit, pin, delete, undo
let ed = M.emptyEdits();
ed = M.edit(ed, 'e1', { text: 'Rae reads the forged ledger entry (corrected)' });
ed = M.pin(ed, 'f1', true);
ed = M.remove(ed, 'e2');
let v = M.apply(store, ed);
ok(v.records.find(r => r.id === 'e1').text.includes('corrected') && v.records.find(r => r.id === 'e1').src === 'player', 'edit applies and marks the record as player-trusted');
{ const q = M.query(v, {}); const iF = q.findIndex(r => r.id === 'f1'), iU = q.findIndex(r => !r.pin); ok(iF >= 0 && iF < iU && q.slice(0, iU).every(r => r.pin), 'pinned records (including locked canon and the newly pinned fact) sort first'); }
ok(!M.query(v, { layer: 'episodic' }).some(r => r.id === 'e2') && M.query(v, { layer: 'episodic', deleted: true }).some(r => r.id === 'e2'), 'delete is soft and visible when asked');
ok(M.apply(store, M.undo(ed)).records.find(r => r.id === 'e2').deleted === false, 'undo reverses the last operation');
ok(M.apply(store, M.restore(ed, 'e2')).records.find(r => r.id === 'e2').deleted === false, 'restore brings a deleted record back');
// locked canon can't be edited or deleted by an overlay
const v2 = M.apply(store, M.remove(M.edit(M.emptyEdits(), 'entry-0', { text: 'changed' }), 'entry-0'));
ok(v2.records.find(r => r.id === 'entry-0').text === store.records.find(r => r.id === 'entry-0').text && !v2.records.find(r => r.id === 'entry-0').deleted, 'locked canon ignores overlay edits and deletes');
// regeneration safety: a rebuilt store (as after a regenerate changes v1 memory) keeps player edits
const fx2 = JSON.parse(JSON.stringify(fx)); fx2.mem.events = fx2.mem.events.filter(e => e.id !== 'e3'); fx2.mem.events.push({ id: 'e9', t: 9, kind: 'action', who: ['Rae'], text: 'New regenerated event' });
const v3 = M.apply(M.build(fx2), ed);
ok(v3.records.find(r => r.id === 'e1').text.includes('corrected') && v3.records.find(r => r.id === 'f1').pin, 'player edits survive a rebuild after regeneration');
ok(!v3.records.some(r => r.id === 'e3') && v3.records.some(r => r.id === 'e9'), 'the rebuild reflects the regenerated memory');
// player-added record
const v4 = M.apply(store, M.add(M.emptyEdits(), { id: 'p1', layer: 'semantic', kind: 'fact', text: 'The harbor master is Dale\'s uncle' }));
ok(v4.records.find(r => r.id === 'p1').src === 'player', 'player can add a memory');
// queries
ok(M.query(store, { who: 'Rae', layer: 'episodic' }).every(r => r.who.includes('Rae')), 'query by character');
ok(M.query(store, { text: 'ledger' }).length >= 2, 'text search');
ok(M.query(store, { from: 2, to: 4 }).every(r => r.t >= 2 && r.t <= 4), 'turn range');
ok(JSON.stringify(M.query(store, {})) === JSON.stringify(M.query(M.build(fx), {})), 'deterministic order');
// purity
ok(JSON.stringify(fx) === JSON.stringify(JSON.parse(fs.readFileSync(path.join(here, 'fixtures/mem2-source.json'), 'utf8'))), 'build does not mutate the source');
const before = JSON.stringify(store); M.apply(store, ed); ok(JSON.stringify(store) === before, 'apply does not mutate the store');
console.log(`memory v2: ${n} checks passed`);
