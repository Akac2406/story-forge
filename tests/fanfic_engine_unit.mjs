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
console.log(`fanfic engine: ${n} checks passed`);
