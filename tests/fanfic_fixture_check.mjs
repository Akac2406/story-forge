// Fanfiction contract v2: the shared fixture must stay consistent (ChatGPT builds screens on it). Run: node tests/fanfic_fixture_check.mjs
import assert from 'node:assert/strict'; import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const { universe: U, session: S } = JSON.parse(fs.readFileSync(path.join(here, 'fixtures/fanfic-ember.json'), 'utf8'));
const C = S.canon, ev = new Map(U.events.map(e => [e.id, e])); let n = 0; const ok = (c, m) => { assert.ok(c, m); n++; };
ok(U.events.every(e => e.id.startsWith('ev:' + U.id + ':')) && Object.keys(U.chars).every(k => k.startsWith('char:' + U.id + ':')), 'ids are namespaced by universe');
ok(U.events.every(e => e.requires.every(r => ev.has(r)) && e.leadsTo.every(r => ev.has(r))), 'every dependency points at a real event');
// no cycles
const seen = new Set(), stack = new Set(); const dfs = id => { if (stack.has(id)) return false; if (seen.has(id)) return true; seen.add(id); stack.add(id); const ok2 = ev.get(id).leadsTo.every(dfs); stack.delete(id); return ok2; };
ok(U.events.every(e => dfs(e.id)), 'no dependency cycles');
ok(U.events.every(e => e.leadsTo.every(x => ev.get(x).requires.includes(e.id))), 'leadsTo and requires agree');
ok(C.rev <= U.rev, 'playthrough pins an existing universe revision');
const st = C.events; ok(Object.entries(st).every(([id, s]) => s.status !== 'impossible' || ev.get(id).requires.some(r => st[r] && ['prevented', 'impossible'].includes(st[r].status))), 'every impossible event has a prevented or impossible prerequisite');
ok(Object.entries(st).filter(([, s]) => s.status === 'protected' && s.conflict).every(([id, s]) => C.eventConflicts.some(c => c.id === s.conflict && c.event === id)), 'protected events with broken prerequisites carry a conflict');
ok(C.relationships.every(r => r.id === 'rel:' + r.a + '>' + r.b), 'relationships are directional (rel:A>B)');
ok(C.identity.canon === C.mode.takeover && U.chars[C.identity.canon], 'takeover identity points at a read-only canon character');
ok(U.records.every(r => ['source', 'fanon', 'uncertain'].includes(r.canon)), 'every universe record says source, fanon or uncertain');
ok(Object.keys(C.rules).length === 14 && Object.values(C.rules).every(v => ['locked', 'adaptive', 'free'].includes(v)), 'all 14 canon rule categories set');
console.log(`fanfic fixture: ${n} checks passed`);
