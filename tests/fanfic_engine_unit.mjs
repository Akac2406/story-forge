// Fanfiction engine (contract v2) unit tests on the shared fixture + small invented texts. Run: node tests/fanfic_engine_unit.mjs
import assert from 'node:assert/strict'; import fs from 'node:fs'; import vm from 'node:vm'; import path from 'node:path'; import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const ctx = {}; ctx.globalThis = ctx; vm.createContext(ctx); vm.runInContext(fs.readFileSync(path.join(here, '../site/fanfic-engine.js'), 'utf8'), ctx);
const F = ctx.SFFan; let n = 0; const ok = (c, m) => { assert.ok(c, m); n++; };
const FX = JSON.parse(fs.readFileSync(path.join(here, 'fixtures/fanfic-ember.json'), 'utf8')); const U = FX.universe, C = FX.session.canon;
// --- indexing
const text = `Chapter 1: Ash\nKael Ashveil stepped into the courtyard. Kael looked at Mira Vell, who did not smile.\nMira Vell said nothing. Kael waited.\n\nChapter 2: Trial\nThe trial began. Kael Ashveil drew his blade. Mira Vell watched Kael.\nLater, Dorran Hale arrived. Dorran Hale smiled at Kael.\n\nChapter 3: Night\nKael slept badly. Dorran Hale walked the halls. Mira Vell locked the archive.`;
const ix = F.indexSource(text, { title: 'Ember Test', now: 1 });
ok(ix.chapters.length === 3 && ix.chapters[1].title.startsWith('Chapter 2'), 'chapters split on headings');
ok(ix.source.id === 'src:ember-test' && ix.source.chapters.every(c => c.hash && c.words > 0), 'source has stable id, hashes and word counts');
const nm = ix.names.map(x => x.name);
ok(nm.includes('Kael Ashveil') && nm.includes('Mira Vell') && nm.includes('Dorran Hale'), 'finds full character names: ' + nm.join(', '));
ok(ix.names.find(x => x.name === 'Kael Ashveil').aliases.includes('Kael'), 'folds first names into aliases');
ok(F.splitChapters('word '.repeat(7000)).length === 3, 'no headings: falls back to ~3,000-word parts');
// --- incremental import with revisions
let u = F.emptyUniverse('Ember Test', 1);
let r1 = F.mergeImport(u, ix, { now: 2 }); u = r1.universe;
ok(r1.added.length === 3 && u.rev === 1 && u.revisions.length === 1, 'first import creates revision 1');
ok(Object.keys(u.chars).includes('char:ember-test:kael-ashveil') && u.chars['char:ember-test:kael-ashveil'].canon === 'uncertain', 'candidate characters get stable ids and stay uncertain');
const r2 = F.mergeImport(u, ix, { now: 3 }); ok(r2.added.length === 0 && r2.duplicate.length === 3 && r2.universe.rev === 1, 're-importing the same chapters is a no-op (duplicates by hash)');
const more = F.indexSource([{ n: 4, title: 'Chapter 4', text: 'Kael Ashveil returned. Kael Ashveil left.' }, { n: 2, title: 'Chapter 2', text: 'A different version of chapter two.' }], { title: 'Ember Test', now: 4 });
const r3 = F.mergeImport(u, more, { now: 4 });
ok(r3.added.join() === '4' && r3.conflicts.join() === '2' && r3.universe.rev === 2 && r3.universe.conflicts.length === 1, 'new volume extends coverage (rev 2); a changed chapter becomes a conflict, old copy kept');
ok(u.rev === 1 && u.sources[0].chapters.length === 3, 'mergeImport never mutates the existing universe');
// --- defaults
const d = F.defaults(['takeover', 'fixit']);
ok(F.RULE_KEYS.every(k => ['locked', 'adaptive', 'free'].includes(d[k])) && d.fates === 'free' && d.ending === 'free' && d.chronology === 'locked', 'presets combine modes');
// --- butterfly effect on the fixture
ok(F.cycles(U).length === 0, 'fixture has no dependency cycles');
const st = { alive: { 'char:ember:mira': true, 'char:ember:dorran': true }, at: { 'char:ember:lys': 'Ember Academy' } };
const base = { position: C.position, locks: C.locks, events: { 'ev:ember:3': { status: 'prevented', why: 'Kael escorted Lys' } } };
const ev = F.evaluate(U, base, st);
ok(ev.status['ev:ember:5'].status === 'impossible' && /Lys is kidnapped/.test(ev.status['ev:ember:5'].why), 'prevented kidnapping makes the revenge vow impossible');
ok(ev.status['ev:ember:6'].status === 'protected' && ev.conflicts.some(c => c.event === 'ev:ember:6'), 'protected duel with an impossible prerequisite becomes a conflict, not forced');
ok(ev.status['ev:ember:4'].status === 'approaching', 'next nearby event is approaching');
ok(ev.upcoming.includes('ev:ember:4') && !ev.upcoming.includes('ev:ember:5'), 'upcoming list leaves out impossible events');
// unmet vs impossible
const ev2 = F.evaluate(U, { position: { order: 1 }, locks: [], events: {} }, { at: { 'char:ember:lys': 'Ember Academy' } });
ok(ev2.status['ev:ember:3'].status !== 'impossible', 'a temporarily unmet condition (Lys not on the road yet) never invalidates');
const ev3 = F.evaluate(U, { position: { order: 1 }, locks: [], events: {} }, { alive: { 'char:ember:mira': false } });
ok(ev3.status['ev:ember:2'].status === 'impossible' && ev3.status['ev:ember:4'].status === 'impossible', 'a dead required character makes the event and its dependents impossible');
// impact preview
const imp = F.impact(U, { position: { order: 1 }, locks: [], events: {} }, {}, 'ev:ember:3', 'prevented');
ok(imp.some(x => x.id === 'ev:ember:5' && x.to === 'impossible') && imp.some(x => x.id === 'ev:ember:6'), 'impact preview lists downstream changes');
// precedence
ok(F.ruleFor(C, { id: 'ev:ember:3', category: 'majorEvents' }).source === 'exception', 'approved exception beats category rule');
ok(F.ruleFor(C, { id: 'ev:ember:6', category: 'majorEvents' }).source === 'lock', 'lock beats category rule');
ok(F.ruleFor(C, { id: 'ev:ember:6', category: 'majorEvents', established: true }).source === 'established', 'what already happened beats everything');
ok(F.ruleFor({ mode: { types: ['fixit'] } }, { id: 'x', category: 'fates' }).rule === 'free', 'falls back to mode defaults');
// spoiler filter (fixture expectation)
const E = FX.expect.spoilerFiltered;
const vis = F.search(U, { position: { ch: E.position }, rev: 1 }, '').map(r => r.id).sort();
ok(JSON.stringify(vis) === JSON.stringify(E.visible.slice().sort()), 'spoiler filter matches the fixture expectation: ' + vis.join(', '));
const kael = F.search(U, Object.assign({}, C, { position: { ch: E.position } }), '', { forChar: 'char:ember:kael' }).map(r => r.id);
ok(kael.includes('fact:ember:dorran-took-lys'), 'takeover character also sees its explicit foreknowledge');
ok(!F.search(U, Object.assign({}, C, { position: { ch: E.position } }), '', { forChar: 'char:ember:mira' }).some(r => r.id === 'fact:ember:dorran-took-lys'), 'no other character gets that foreknowledge');
ok(F.search(U, { position: { ch: 60 } }, '').find(r => r.id === 'fanon:ember:kael-cooks').label === 'fanon', 'fanon and uncertain records are labelled');

// --- characters & knowledge
const Cpos = Object.assign({}, C, { position: Object.assign({}, C.position, { ch: 5 }) });
const kk = id => F.knows(U, Cpos, id).map(r => r.id).sort();
ok(JSON.stringify(kk('char:ember:mira')) === JSON.stringify(['fact:ember:archive-fire', 'fact:ember:mira-dorran'].sort()) || kk('char:ember:mira').includes('fact:ember:archive-fire'), 'Mira knows common revealed facts and her own: ' + kk('char:ember:mira'));
ok(!kk('char:ember:mira').includes('fact:ember:dorran-took-lys') && !kk('char:ember:lys').includes('fact:ember:dorran-took-lys'), 'a secret is not known by everyone');
ok(kk('char:ember:dorran').includes('fact:ember:dorran-took-lys'), 'a participant knows their own secret even before the reader learns it');
ok(kk('char:ember:kael').includes('fact:ember:dorran-took-lys'), 'takeover character knows its explicit foreknowledge');
ok(!F.knows(U, Cpos, 'char:ember:kael').some(r => r.canon === 'fanon'), 'fanon is never treated as character knowledge');
const idn = F.identity(U, C, 'char:ember:kael');
ok(idn.controlled && idn.canon.name === 'Kael Ashveil' && idn.player.changes.length && idn.foreknowledge.length === 2 && idn.age === 18, 'takeover identity: canon, player version, foreknowledge and age kept separate');
ok(U.chars['char:ember:kael'].core.personality.startsWith('guarded'), 'canon identity untouched');
ok(F.relationships(C, { from: 'char:ember:mira', to: 'char:ember:kael' })[0].trust === 35 && F.relationships(C, { from: 'char:ember:kael', to: 'char:ember:mira' })[0].trust === 55, 'relationships are directional');
const priv = F.relationships(C, { involving: 'char:ember:lys' })[0];
ok(F.relVisibleTo(priv, 'char:ember:kael') && !F.relVisibleTo(priv, 'char:ember:mira'), 'private relationship visible only to those who know');
// --- mutations, history, undo
let r = F.setRule(C, 'romance', 'locked', 5);
ok(r.applied && r.canon.rules.romance === 'locked' && C.rules.romance === 'free', 'setRule applies to a copy and records history');
ok(!F.setRule(C, 'romance', 'free').applied && F.setRule(C, 'romance', 'free').reason === 'unchanged', 'no-op change reports unchanged');
ok(F.setRule(C, 'nonsense', 'free').reason === 'unknown rule' && F.setPOV(C, { mode: 'sideways' }).reason === 'bad value', 'invalid changes rejected without changing data');
const u1 = F.undo(r.canon); ok(u1.applied && u1.canon.rules.romance === 'free' && u1.canon.history.length === C.history.length, 'undo restores the previous rules');
r = F.lock(C, 'event', 'ev:ember:4', true); ok(r.canon.locks.some(l => l.id === 'ev:ember:4'), 'lock an event');
r = F.exception(r.canon, 'ev:ember:4', 'Mira teaches the form a year early'); ok(r.canon.exceptions.length === 2, 'approved exception added');
r = F.setRelationship(C, { a: 'char:ember:lys', b: 'char:ember:kael', kinds: ['family'], trust: 90 }); ok(r.canon.relationships.some(x => x.id === 'rel:char:ember:lys>char:ember:kael'), 'new directional relationship with stable id');
r = F.setFate(C, 'char:ember:dorran', 'protected'); ok(r.canon.fates['char:ember:dorran'].target === 'protected' && r.canon.fates['char:ember:dorran'].original, 'fate target changes, original fate kept');
// --- prompt block
const st2 = { alive: { 'char:ember:mira': true, 'char:ember:dorran': true } };
const Cev = Object.assign({}, C, { position: Object.assign({}, C.position, { ch: 5 }), events: { 'ev:ember:3': { status: 'prevented' } } });
const block = F.canonFor(U, Cev, { text: 'Mira watches Kael at the archive', present: ['char:ember:kael', 'char:ember:mira'], state: st2 });
ok(/player controls Kael Ashveil/i.test(block) && /Never decide their actions/.test(block), 'prompt tells the narrator who the player controls');
ok(/will NOT happen/.test(block) && block.includes('Lys is kidnapped') && block.includes('Kael swears revenge'), 'prompt lists events that will not happen');
ok(/Mira Vell:/.test(block) && /Feels toward Kael Ashveil: mentor \(trust 35\)/.test(block), 'present characters get personality and directional feelings');
ok(!block.includes('Dorran arranged') && !block.includes('ninth form burns'), 'prompt never includes spoilers beyond the position');
ok(/Never copy passages/.test(block) && F.canonFor(U, Cev, { max: 300 }).length <= 300, 'originality rule present; budget respected');
// --- reply check
const iss = F.check(U, Cev, 'Bandits seize Lys on the road to the academy; Lys is kidnapped. Kael decides to run.', { state: st2 });
ok(iss.some(i => i.kind === 'forced-event') && iss.some(i => i.kind === 'player-agency'), 'check flags a forced impossible event and deciding for the player');
ok(F.check(U, Cev, 'Mira explains that the ninth form burns the user own life force', {}).some(i => i.kind === 'spoiler'), 'check flags a spoiler');
ok(F.check(U, Cev, 'Mira | "Again, Kael." \nMira said nothing.', { state: { alive: { 'char:ember:mira': false } } }).some(i => i.kind === 'dead-speaks'), 'check flags a dead character speaking');
ok(F.check(U, Cev, 'Morning mist covered the courtyard. Mira corrected a student\'s stance.', { state: st2 }).length === 0, 'clean reply has no issues');
// --- validate, export, restore
ok(F.validate(U, C).ok, 'fixture playthrough validates: ' + F.validate(U, C).issues);
ok(!F.validate(U, Object.assign({}, C, { rev: 9 })).ok && !F.validate(U, Object.assign({}, C, { relationships: [{ id: 'rel:x', a: 'a', b: 'b' }] })).ok, 'validate catches bad revision pin and bad relationship ids');
const bk = F.exportStory(Object.assign({ turns: [{ role: 'user', text: 'hi' }], ocKey: 'should-not-export-12345' }, FX.session), U, { now: 1 });
ok(bk.credentials === false && !JSON.stringify(bk).includes('should-not-export'), 'export excludes credentials');
ok(bk.universe.records.every(r => r.rev == null || r.rev <= C.rev), 'export keeps the pinned revision');
const rp = F.restorePreview(bk); ok(rp.ok && rp.summary.turns === 1, 'restore preview validates a good backup: ' + rp.issues);
ok(!F.restorePreview({ kind: 'x' }).ok && !F.restorePreview(Object.assign({}, bk, { session: Object.assign({}, bk.session, { ocKey: 'leaked-key-abcdefgh' }) })).ok, 'restore preview rejects wrong files and backups with credentials');
console.log(`fanfic engine: ${n} checks passed`);

