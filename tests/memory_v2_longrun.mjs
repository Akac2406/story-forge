// Memory overhaul: simulated long stories (30/100/250/500/1,000 turns). No network. Run: node tests/memory_v2_longrun.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs'; import vm from 'node:vm'; import path from 'node:path'; import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const ctx = {}; ctx.globalThis = ctx; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(here, '../site/memory-v2.js'), 'utf8'), ctx);
const M = ctx.SFMem2;
// deterministic pseudo-random
let seed = 7; const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
const pick = a => a[Math.floor(rnd() * a.length)];
const CAST = ['Rae', 'Dale', 'June', 'Sam', 'Priya', 'Marco', 'Ilse', 'Tobin', 'Wren', 'Ada', 'Kofi', 'Lena'];
const PLACES = ['harbor office', 'pier', 'warehouse', 'lighthouse', 'market', 'chapel', 'tavern', 'customs house'];
const VERBS = ['argues with', 'follows', 'hides a letter from', 'warns', 'bargains with', 'confides in', 'searches the room of', 'helps'];
const OBJ = ['the brass key', 'a torn map', 'the tide tables', 'a sealed crate', 'the ledger', 'a silver locket', 'the night roster'];
function story(n) {
  seed = 7 + n; const events = [], facts = [], secrets = [], chars = {}; let id = 0;
  CAST.forEach(c => chars[c] = { kernel: { core: c + ' of the harbor' }, state: { mood: 'calm', status: 'alive' }, knows: [] });
  // planted early fact that only Rae knows
  facts.push({ id: 'fplant', text: 'The lighthouse keeper hid the gold under the third stair', since: 2 }); chars.Rae.knows.push('fplant');
  for (let t = 1; t <= n; t++) {
    const k = 1 + Math.floor(rnd() * 3);
    for (let j = 0; j < k; j++) { const a = pick(CAST), b = pick(CAST.filter(x => x !== a)); events.push({ id: 'e' + (++id), t, ch: Math.floor(t / 20), src: 'meta', kind: rnd() < .15 ? 'bond' : 'action', imp: 1 + Math.floor(rnd() * 5), who: [a, b], wit: [], where: pick(PLACES), text: `${a} ${pick(VERBS)} ${b} about ${pick(OBJ)}` }); }
    if (rnd() < .3) { const f = { id: 'f' + (++id), text: `${pick(CAST)} saw ${pick(OBJ)} at the ${pick(PLACES)}`, since: t }; facts.push(f); chars[pick(CAST)].knows.push(f.id); }
  }
  return { sessionId: 's' + n, mem: { v: 1, events, facts, secrets, chars, scene: { where: 'lighthouse', who: ['Rae', 'Dale'] } },
    canon: [{ id: 'entry-0', k: 'Lighthouse', t: 'Built 1820. The keeper never leaves at night.', lock: true }], notes: [{ id: 'n1', text: 'Keep it under 250 words.', pri: 'must', on: true }],
    player: { name: 'Avery' }, setup: 'A harbor town.', era: '1890s', days: Math.floor(n / 5), dead: [], quests: ['Find the gold'] };
}
const rows = [];
for (const n of [30, 100, 250, 500, 1000]) {
  const src = story(n), t0 = performance.now();
  const view = M.apply(M.build(src), M.edit(M.emptyEdits(), 'e1', { text: 'player-corrected first event' }));
  const t1 = performance.now();
  const hits = M.retrieve(view, { text: 'Where did the lighthouse keeper hide the gold?', present: ['Rae', 'Dale'], where: 'lighthouse', t: n, max: 4000 });
  const t2 = performance.now(); const prompt = M.render(hits); const c = M.contradictions(view); const t3 = performance.now();
  const integ = M.integrity(view);
  assert.ok(integ.ok, `integrity at ${n}: ${integ.errors.slice(0, 3)}`);
  assert.ok(view.records.find(r => r.id === 'e1').text === 'player-corrected first event', `player edit kept at ${n}`);
  assert.ok(M.knows(view, 'Rae').some(r => r.id === 'fplant') && !M.knows(view, 'Dale').some(r => r.id === 'fplant'), `knowledge boundary at ${n}`);
  const rank = hits.findIndex(h => h.record.id === 'fplant');
  assert.ok(rank >= 0 && rank < 5, `early fact recalled near the top at ${n} turns (rank ${rank})`);
  assert.ok(prompt.length <= 4000, `prompt budget kept at ${n} (${prompt.length})`);
  assert.equal(c.length, 0, `no false contradictions at ${n}`);
  rows.push({ turns: n, records: view.records.length, build_ms: +(t1 - t0).toFixed(1), recall_ms: +(t2 - t1).toFixed(1), checks_ms: +(t3 - t2).toFixed(1), prompt_chars: prompt.length, planted_rank: rank + 1, store_kb: Math.round(JSON.stringify(src.mem).length / 1024) });
}
console.table(rows);
const worst = rows[rows.length - 1];
assert.ok(worst.build_ms + worst.recall_ms + worst.checks_ms < 1500, 'all memory work for a 1,000-turn story under 1.5 s');
fs.writeFileSync(path.join(here, 'longrun-results.json'), JSON.stringify(rows, null, 1));
console.log('memory v2 long-run: all sizes passed');
