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
ok(M.query(store, { asOf: 3, layer: 'episodic' }).map(r => r.id).join() === 'e1', 'asOf: only events up to that turn');
ok(M.query(store, { asOf: 2, layer: 'semantic' }).every(r => r.id !== 'f1'), 'asOf: a fact learned at turn 3 is not known at turn 2');
ok(M.history(ed, 'e1').length === 1 && M.history(ed, 'e1')[0].op === 'edit', 'history lists operations per record');

// ---- temporal: supersede keeps history, current vs asOf
{ const f2 = JSON.parse(JSON.stringify(fx)); f2.mem.facts.push({ id: 'f2', text: 'Ledger entry 12 was corrected by the clerk', since: 6 });
  const st2 = M.build(f2); const ed2 = M.supersede(M.emptyEdits(), 'f1', 'f2', 6); const v5 = M.apply(st2, ed2);
  const old = v5.records.find(r => r.id === 'f1'), nw = v5.records.find(r => r.id === 'f2');
  ok(old.until === 6 && old.expiredBy === 'f2' && !old.deleted && nw.supersedes.includes('f1'), 'supersede closes the old fact at turn 6, keeps it, links the new one');
  ok(M.query(v5, { layer: 'semantic', current: true }).every(r => r.id !== 'f1'), 'current-only query drops the superseded fact');
  ok(M.query(v5, { layer: 'semantic', asOf: 4 }).some(r => r.id === 'f1') && !M.query(v5, { layer: 'semantic', asOf: 4 }).some(r => r.id === 'f2'), 'asOf 4 shows the old fact, not the new one');
  ok(v5.records.find(r => r.id === 'f1').storyFrom === 3, 'facts carry storyFrom'); }
// ---- retrieval
{ const hits = M.retrieve(store, { text: 'Who forged the ledger entry?', present: ['Rae'], where: 'harbor office', t: 6 });
  ok(hits.length > 0 && hits.slice(0, 3).some(h => h.record.id === 'f1' || h.record.id === 'e1'), 'retrieval ranks ledger memories first for a ledger question');
  ok(hits.every(h => !h.record.deleted), 'retrieval skips deleted');
  ok(M.retrieve(store, { text: 'ledger', t: 2 }).every(h => h.record.id !== 'f1'), 'retrieval respects time: fact learned at turn 3 not used at turn 2');
  const small = M.retrieve(store, { text: 'ledger', max: 120 }); ok(small.reduce((a, h) => a + h.record.text.length + 20, 0) <= 120, 'retrieval stays within the character budget');
  ok(JSON.stringify(M.retrieve(store, { text: 'ledger safe', present: ['Dale'] })) === JSON.stringify(M.retrieve(store, { text: 'ledger safe', present: ['Dale'] })), 'retrieval is deterministic');
  const txt = M.render(hits); ok(/Known facts:|Past events:/.test(txt) && txt.includes('[turn 3]'), 'render groups by layer with turn tags'); }
// ---- contradictions
{ const f3 = JSON.parse(JSON.stringify(fx)); f3.dead = ['Dale']; f3.mem.facts.push({ id: 'f3', text: 'Ledger entry 12 is not forged', since: 5 });
  const c = M.contradictions(M.build(f3));
  ok(c.some(x => x.kind === 'dead-acts' && x.ids.includes('e2')), 'flags a dead character acting');
  ok(c.some(x => x.kind === 'fact' && x.ids.includes('f1') && x.ids.includes('f3')), 'flags two current facts that say opposite things');
  ok(M.contradictions(store).length === 0, 'no false alarms on the clean fixture'); }
// ---- NPC goals and schedules
{ const f4 = JSON.parse(JSON.stringify(fx)); f4.npcs = { Dale: { goals: ['Hide the debt'], schedule: [{ day: 0, where: 'harbor office', doing: 'working' }, { day: 3, where: 'smugglers cove', doing: 'paying the smugglers' }] } };
  const v6 = M.build(f4);
  ok(M.npcState(v6, 1)[0].where === 'harbor office' && M.npcState(v6, 3)[0].doing === 'paying the smugglers', 'NPC schedule advances with story days only');
  ok(M.npcState(v6, 5)[0].goals[0] === 'Hide the debt', 'NPC goals carried on the character'); }
console.log(`memory v2: ${n} checks passed`);
