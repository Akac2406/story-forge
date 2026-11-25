// Contract section 14: real-world universes, romance eligibility, safeguards, competitions. Run: node tests/fanfic_realworld_unit.mjs
import assert from 'node:assert/strict'; import fs from 'node:fs'; import vm from 'node:vm'; import path from 'node:path'; import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url)); const ctx = {}; ctx.globalThis = ctx; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(here, '../site/fanfic-engine.js'), 'utf8'), ctx); const F = ctx.SFFan; let n = 0; const ok = (c, m) => { assert.ok(c, m); n++; };
const FX = JSON.parse(fs.readFileSync(path.join(here, 'fixtures/fanfic-idol.json'), 'utf8')); const FI = FX.fictional, RW = FX.realworld, E = FX.expect;
const uOf = id => id.startsWith('char:idol') || id === 'player' ? FI : RW;
// eligibility matches the fixture expectations
for (const [a, b] of E.romance.eligible) { const S = b.includes(':idol:') ? FI : RW; ok(F.romanceAllowed(S.universe, S.canon, a, b).ok, `eligible: ${a} + ${b}`); }
for (const [a, b, why] of E.romance.ineligible) { const S = b.includes(':idol:') ? FI : RW; const r = F.romanceAllowed(S.universe, S.canon, a, b); ok(!r.ok && r.reason === why, `ineligible (${why}): ${b} -> ${r.reason}`); }
ok(F.ageAt(FI.universe, FI.canon, 'char:idol:rin') === 16 && F.ageAt(FI.universe, FI.canon, 'char:idol:taeo') === null, 'ages from story date; unknown stays unknown');
const conflicting = JSON.parse(JSON.stringify(FI.canon)); conflicting.position.ages['char:idol:ari'] = 30;
ok(F.ageAt(FI.universe, conflicting, 'char:idol:ari') === null && !F.romanceAllowed(FI.universe, conflicting, 'player', 'char:idol:ari').ok, 'conflicting ages disable romance');
ok(!F.romanceAllowed(FI.universe, Object.assign({}, FI.canon, { romance: { pref: 'none' } }), 'player', 'char:idol:seo-jin').ok, 'romance off means no romance');
ok(F.isReal(RW.universe, 'person:demo-stage:public-a') && !F.isReal(FI.universe, 'char:idol:seo-jin'), 'public figures are recognised as real people');
// prompt lines
const pf = F.canonFor(FI.universe, FI.canon, { present: ['char:idol:seo-jin', 'char:idol:rin'] });
ok(/Romance preference: any, focus optional/.test(pf) && /Possible romantic interests here: Seo Jin/.test(pf) && /Never romantic with: Rin Hale \(minor\)/.test(pf), 'fictional prompt: romance preference, eligible and never-romantic lists');
ok(!/ALTERNATE-REALITY/.test(pf), 'fictional universes get no real-world framing');
const pr = F.canonFor(RW.universe, RW.canon, { present: ['person:demo-stage:public-a', 'char:demo-stage:oc-friend'] });
ok(/ALTERNATE-REALITY FICTION/.test(pr) && /Han Doyun/.test(pr) && /Never give them romance/.test(pr), 'real-world prompt: fiction framing and professional-only rule');
ok(/Never romantic with: Han Doyun \(real person\)/.test(pr) && /Possible romantic interests here: Lee Sora/.test(pr) && /BL/.test(pr), 'real-world prompt: real people excluded from romance; fictional adults allowed');
// checks
const c1 = F.check(RW.universe, RW.canon, 'After practice, Jun kissed Han Doyun backstage.', {});
ok(c1.some(i => i.kind === 'real-person-romance'), 'flags romance with a real person');
const c2 = F.check(FI.universe, FI.canon, 'Haneul held her hand and confessed to Rin under the stage lights.', {});
ok(c2.some(i => i.kind === 'minor-romance'), 'flags romance with a minor');
ok(F.check(RW.universe, RW.canon, 'Han Doyun corrected the choreography and Jun practised until midnight.', {}).length === 0, 'professional scene with a real person is fine');
ok(F.check(FI.universe, FI.canon, 'Seo Jin and Haneul went on a date after the evaluation.', {}).length === 0, 'romance between adults in a fictional universe is fine');
// competitions
const C = E.competition, r1 = F.rank(C.entries, C.config, C.seed), r2 = F.rank(C.entries.slice().reverse(), C.config, C.seed);
ok(JSON.stringify(r1) === JSON.stringify(r2), 'rankings are reproducible (same seed, any input order)');
ok(JSON.stringify(F.rank(C.entries, C.config, 'other-seed').results.map(x => x.score)) !== JSON.stringify(r1.results.map(x => x.score)), 'a different seed changes the random part');
ok(r1.results.every(x => Math.abs(x.parts.random) <= C.config.random), 'random variation stays within its bound');
ok(r1.results[0].id === 'person:demo-stage:public-a' && r1.results.find(x => x.id === 'player').rank > 1, 'the player can lose (no auto-win)');
let rc = F.recordCompetition(RW.canon, 'ep2', r1, { now: 1 }); ok(rc.applied && rc.canon.competitions.ep2.seed === C.seed, 'result recorded with seed and config');
const again = F.recordCompetition(rc.canon, 'ep2', F.rank(C.entries, C.config, 'reroll'), { now: 2 }); ok(!again.applied && again.reason === 'established', 'an established result is never re-rolled');
ok(F.recordCompetition(rc.canon, 'ep2', F.rank(C.entries, C.config, 'reroll'), { replace: true, now: 3 }).applied, 'only an explicit player replace changes it');
// romance settings
ok(F.setRomance(FI.canon, { pref: 'gl', focus: 'central' }).canon.romance.pref === 'gl' && !F.setRomance(FI.canon, { pref: 'nsfw' }).applied, 'romance preference changes validated');
ok(F.undo(F.setRomance(FI.canon, { pref: 'gl' }).canon).canon.romance.pref === 'any', 'romance change can be undone');
console.log(`fanfic real-world: ${n} checks passed`);
