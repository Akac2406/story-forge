// Living characters engine (phase 6). Run: node tests/character_engine_unit.mjs
import assert from 'node:assert/strict'; import fs from 'node:fs'; import vm from 'node:vm'; import path from 'node:path'; import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url)); const ctx = {}; ctx.globalThis = ctx; vm.createContext(ctx);
for (const f of ['character-engine.js', 'memory-v2.js']) vm.runInContext(fs.readFileSync(path.join(here, '../site/' + f), 'utf8'), ctx);
const C = ctx.SFChar, M = ctx.SFMem2; let n = 0; const ok = (c, m) => { assert.ok(c, m); n++; };
const ev = [
  { id: 'e1', t: 2, kind: 'action', who: ['Rae', 'Dale'], text: 'Rae saves Dale from the falling crates' },
  { id: 'e2', t: 4, kind: 'action', who: ['Dale', 'Rae'], text: 'Dale lies to Rae about the ledger' },
  { id: 'e3', t: 6, kind: 'betrayal', who: ['Dale', 'Rae'], text: 'Dale betrays Rae to the smugglers' },
  { id: 'e4', t: 7, kind: 'action', who: ['Rae'], text: 'Rae walks home alone' },
  { id: 'e5', t: 8, kind: 'action', who: ['June', 'Rae'], text: 'June helps Rae bandage her arm and thanks her' }];
let r = C.evolve([], ev);
const get = (a, b) => r.rels.find(x => x.id === 'rel:' + a + '>' + b) || {};
ok(get('Dale', 'Rae').trust > 0 && get('Dale', 'Rae').history[0].why.includes('saved'), 'being saved raises the rescued character\'s trust, with evidence');
ok(get('Rae', 'Dale').trust < 0 && get('Rae', 'Dale').history.some(h => h.why.includes('betrayal')), 'lies and betrayal lower the victim\'s trust in the actor');
ok(get('Rae', 'Dale').trust !== get('Dale', 'Rae').trust, 'relationships are directional');
ok(get('Rae', 'June').affection > 0 && get('June', 'Rae').affection >= 0, 'help and thanks build affection');
ok(!r.rels.some(x => x.history.some(h => h.event === 'e4')), 'a solo action changes no relationship');
ok(r.rels.every(x => x.history.every(h => Object.values(h.change).every(v => Math.abs(v) <= C.LIMIT))), 'each event moves a relationship by at most ' + C.LIMIT);
const r2 = C.evolve(r.rels, ev); ok(r2.applied.length === 0 && JSON.stringify(r2.rels) === JSON.stringify(r.rels), 'replaying the same events changes nothing (idempotent)');
const big = Array.from({ length: 40 }, (_, i) => ({ id: 'b' + i, t: 10 + i, kind: 'betrayal', who: ['X', 'Y'], text: 'X betrays Y' }));
ok(C.evolve([], big).rels.find(x => x.id === 'rel:Y>X').trust === -100, 'values stay within -100..100');
ok(C.history(r.rels, 'Rae', 'Dale').map(h => h.event).join() === 'e1,e2,e3' && C.label(get('Rae', 'Dale')) !== 'devoted', 'history and label per direction');
ok(C.evolve([], ev, { idOf: nm => 'char:x:' + nm.toLowerCase() }).rels.every(x => x.a.startsWith('char:x:')), 'names can be mapped to stable character ids');
// journal from memory v2
const view = M.build({ mem: { events: [{ id: 'e1', t: 2, kind: 'action', who: ['Rae', 'Dale'], wit: ['June'], text: 'Rae saves Dale' }, { id: 'e9', t: 3, kind: 'action', who: ['Dale'], wit: [], text: 'Dale counts coins' }],
  facts: [{ id: 'f1', text: 'The ledger is forged', since: 3 }], chars: { June: { kernel: { core: 'medic' }, state: {}, knows: ['f1'] } } } });
const j = C.journal(view, 'June');
ok(j.some(x => x.role === 'witnessed' && x.text === 'Rae saves Dale') && j.some(x => x.role === 'learned' && x.text.includes('forged')) && !j.some(x => x.text.includes('counts coins')), 'journal: witnessed and learned, nothing she was not part of');
ok(C.journal(view, 'Dale').filter(x => x.role === 'did').length === 2, 'journal: what a character did');
// agenda
const npc = { name: 'Dale', goals: ['Hide the debt'], schedule: [{ day: 0, where: 'harbor office', doing: 'works late' }, { day: 3, where: 'smugglers cove', doing: 'pays the smugglers' }, { day: 6, where: 'pier', doing: 'waits for a ship' }] };
const ag = C.agenda(npc, 1, 6);
ok(ag.where === 'pier' && ag.developments.map(d => d.day).join() === '3,6', 'agenda advances with story days and lists off-screen developments');
ok(C.agenda(npc, 6, 6).developments.length === 0 && C.agenda(npc, 7, 9).developments[0].text.includes('Hide the debt'), 'no time passing, no developments; otherwise goals continue');
// voice check
const mira = { name: 'Mira Vell', speech: { tone: 'formal', vocabulary: 'precise' }, core: { personality: 'strict, secretly kind', temperament: 'patient' } };
ok(C.checkVoice(mira, 'Mira | "Yeah, gonna be fine, dude."').some(x => x.text.includes('slang')), 'flags slang from a formal speaker');
ok(C.checkVoice(mira, '"STOP! NOW! GET OUT!" Mira shouted.').some(x => x.text.includes('shouting')), 'flags shouting from a patient character');
ok(C.checkVoice(mira, 'Mira | "Stand straighter, Kael. Again."').length === 0, 'in-character line passes');
ok(C.checkVoice(mira, 'Kael | "Yeah, gonna be fine, dude."').length === 0, 'other characters\' lines are not attributed to her');
console.log(`character engine: ${n} checks passed`);
