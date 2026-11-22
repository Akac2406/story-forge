// Unit tests for the Phase 1 memory engine (pure functions). Run: node tests/memory_phase1_unit.mjs
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
globalThis.window = globalThis;
eval(readFileSync(path.join(here, "..", "site", "memory-engine.js"), "utf8"));
const M = globalThis.SFMemory;
let pass = 0, fail = 0;
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
function t(name, fn) { try { fn(); pass++; console.log("ok  ", name); } catch (e) { fail++; console.log("FAIL", name, "-", e.message); } }
function assert(c, m) { if (!c) throw new Error(m || "assertion failed"); }
const snap = m => JSON.parse(JSON.stringify(m));
const R1 = `Text.\n\n[[META]]\nCAST: none\nEVENTS: 4 | reveal | Lumia | east wing | Lumia admits she forged the healer's report | Riette; 2 | action | Lenox, Lumia | gates | Lenox offers Lumia his arm | none\nLEARNED: Riette: Lumia forged the healer's report (overheard)\nSCENE: Veillard east wing | Lumia, Riette | night, return day 2\nNEXT: a | b | c`;
const R2 = `More.\n\n[[META]]\nEVENTS: 5 | death | Marek | courtyard | Marek is killed by an arrow | Julian\nSCENE: courtyard | Julian | dawn`;

t("parseMeta reads EVENTS, LEARNED and SCENE", () => {
  const p = M.parseMeta(R1);
  assert(p.events.length === 2, "2 events");
  assert(p.events[0].imp === 4 && p.events[0].kind === "reveal" && eq(p.events[0].who, ["Lumia"]) && eq(p.events[0].wit, ["Riette"]), "event 1 fields");
  assert(eq(p.events[1].who, ["Lenox", "Lumia"]) && eq(p.events[1].wit, []), "event 2 people");
  assert(p.learned.length === 1 && p.learned[0].who === "Riette" && p.learned[0].text === "Lumia forged the healer's report" && p.learned[0].how === "overheard", "learned");
  assert(p.scene.where === "Veillard east wing" && eq(p.scene.who, ["Lumia", "Riette"]) && p.scene.when === "night, return day 2", "scene");
});
t("parseMeta handles none, missing block and junk", () => {
  assert(eq(M.parseMeta("no meta here"), { events: [], learned: [], scene: null }), "no block");
  const p = M.parseMeta("x\n[[META]]\nEVENTS: none\nLEARNED: none\nSCENE: none");
  assert(!p.events.length && !p.learned.length && p.scene === null, "none values");
  const q = M.parseMeta("x\n[[META]]\nEVENTS: garbage without pipes; 9 | weird | A | - | Something happens");
  assert(q.events.length === 1 && q.events[0].imp === 5 && q.events[0].kind === "action" && q.events[0].where === "", "clamped and defaulted");
});
t("record adds events, facts, knowledge, character links and scene", () => {
  const mem = M.init(); const mx = M.record(mem, M.parseMeta(R1), { t: 3, ch: 0, tid: "a" });
  assert(mem.events.length === 2 && mem.facts.length === 1, "added");
  assert(mem.chars.Riette.knows.includes(mem.facts[0].id), "Riette knows");
  assert(mem.chars.Lumia.mem.length === 2 && mem.chars.Riette.mem.length === 1, "links");
  assert(mem.scene.where === "Veillard east wing" && mem.chars.Lumia.state.where === "Veillard east wing", "scene");
  assert(mem.events[0].open === false && mem.events[0].t === 3, "anchors");
  assert(!M.empty(mx), "delta not empty");
});
t("undo restores the exact previous memory", () => {
  const mem = M.init(); M.record(mem, M.parseMeta(R1), { t: 1 }); const before = snap(mem);
  const mx = M.record(mem, M.parseMeta(R2), { t: 3 }); assert(!eq(mem, before), "changed");
  M.undo(mem, mx); const after = snap(mem); after.seq = before.seq; // ids are never reused, so seq may stay ahead
  assert(eq(after, before), "identical after undo");
});
t("undo of the only turn returns to an empty memory (apart from the id counter)", () => {
  const mem = M.init(); const base = snap(mem); const mx = M.record(mem, M.parseMeta(R1), { t: 1 });
  M.undo(mem, mx); const a = snap(mem); a.seq = 0; assert(eq(a, base), JSON.stringify(a));
});
t("apply re-applies a stored delta identically (version switching)", () => {
  const mem = M.init(); const mx = M.record(mem, M.parseMeta(R1), { t: 1 }); const withIt = snap(mem);
  M.undo(mem, mx); M.apply(mem, mx); assert(eq(snap(mem), withIt), "same after redo");
  M.apply(mem, mx); assert(eq(snap(mem), withIt), "apply is idempotent");
});
t("switching between two versions of the same turn", () => {
  const mem = M.init(); M.record(mem, M.parseMeta(R2), { t: 1 }); const base = snap(mem);
  const a = M.record(mem, M.parseMeta(R1), { t: 3 }); const withA = snap(mem);
  M.undo(mem, a); const b = M.record(mem, M.parseMeta("x\n[[META]]\nEVENTS: 3 | promise | Julian | gate | Julian swears to guard the duchess\nSCENE: gatehouse | Julian | noon"), { t: 3 }); const withB = snap(mem);
  assert(mem.events.some(e => e.kind === "promise" && e.open) && !mem.events.some(e => e.kind === "reveal"), "B only");
  M.undo(mem, b); M.apply(mem, a); const x = snap(mem); x.seq = withA.seq; assert(eq(x, withA), "back to A");
  M.undo(mem, a); M.apply(mem, b); const y = snap(mem); y.seq = withB.seq; assert(eq(y, withB), "back to B");
  M.undo(mem, b); const z = snap(mem); z.seq = base.seq; assert(eq(z, base), "base");
});
t("undoing an older turn leaves later scene changes alone", () => {
  const mem = M.init(); const a = M.record(mem, M.parseMeta(R1), { t: 1 }); M.record(mem, M.parseMeta(R2), { t: 3 });
  M.undo(mem, a); assert(mem.scene.where === "courtyard", "later scene kept"); assert(!mem.events.some(e => e.kind === "reveal"), "older events removed");
  assert(mem.events.some(e => e.kind === "death"), "later events kept");
});
t("duplicate events within 6 turns are not added twice", () => {
  const mem = M.init(); M.record(mem, M.parseMeta(R2), { t: 1 }); const mx = M.record(mem, M.parseMeta(R2), { t: 3 });
  assert(mem.events.filter(e => e.kind === "death").length === 1 && mx.ev.length === 0, "deduped");
  const far = M.record(mem, M.parseMeta(R2), { t: 20 }); assert(far.ev.length === 1, "same text far later is a new event");
});
t("learning a known fact links it instead of duplicating", () => {
  const mem = M.init(); M.record(mem, M.parseMeta(R1), { t: 1 });
  M.record(mem, M.parseMeta("x\n[[META]]\nLEARNED: Julian: Lumia forged the healer's report (Riette told him)"), { t: 3 });
  assert(mem.facts.length === 1 && mem.chars.Julian.knows.includes(mem.facts[0].id), "linked");
});
t("shiftTurns moves anchors after a deletion", () => {
  const mem = M.init(); M.record(mem, M.parseMeta(R1), { t: 1 }); M.record(mem, M.parseMeta(R2), { t: 5 });
  M.shiftTurns(mem, 2, -2); assert(mem.events.find(e => e.kind === "death").t === 3 && mem.events.find(e => e.kind === "reveal").t === 1, "shifted");
});
t("ids are never reused after undo", () => {
  const mem = M.init(); const a = M.record(mem, M.parseMeta(R1), { t: 1 }); M.undo(mem, a); const b = M.record(mem, M.parseMeta(R1), { t: 1 });
  const ia = a.ev.map(e => e.id), ib = b.ev.map(e => e.id); assert(!ia.some(x => ib.includes(x)), "fresh ids");
});
t("migrate output passes integrity and accepts deltas", () => {
  const mem = M.migrate({ facts: ["A fact"], mems: [{ t: "x", x: "old memory" }], chaps: [{ sum: "ch1" }], cast: { Lenox: { t: ["proud"] } }, dead: [], upto: 4 }, {});
  M.record(mem, M.parseMeta(R1), { t: 6 }); const r = M.integrity(mem); assert(r.ok, r.errors.join(", "));
  assert(mem.chars.Lenox.kernel.core === "proud", "existing char untouched");
});
t("events that differ by a number or by who took part are kept", () => {
  const mem = M.init(); M.record(mem, M.parseMeta("x\n[[META]]\nEVENTS: 3 | action | Kevin | hall | Kevin performs deed number 2"), { t: 1 });
  const b = M.record(mem, M.parseMeta("x\n[[META]]\nEVENTS: 3 | action | Kevin | hall | Kevin performs deed number 3"), { t: 3 });
  const c = M.record(mem, M.parseMeta("x\n[[META]]\nEVENTS: 3 | action | Mira | hall | Kevin performs deed number 3"), { t: 5 });
  assert(b.ev.length === 1 && c.ev.length === 1 && mem.events.length === 3, "kept");
});
t("deleting a middle turn keeps the later chain correct", () => {
  const S = w => M.parseMeta(`x\n[[META]]\nSCENE: ${w} | Kevin | night`);
  const mem = M.init(); const a = M.record(mem, S("hall 1"), { t: 1 }); const b = M.record(mem, S("hall 2"), { t: 3 }); const c = M.record(mem, S("hall 3"), { t: 5 });
  M.undo(mem, b, [c]); assert(mem.scene.where === "hall 3", "current kept");
  M.undo(mem, c, []); assert(mem.scene.where === "hall 1", "falls back past the deleted turn: " + mem.scene.where);
  assert(mem.chars.Kevin.state.where === "hall 1", "character location too: " + mem.chars.Kevin.state.where);
});
t("multi-line and bulleted META lists are read (v36)", () => {
  const raw = "Text.\n\n[[META]]\n**EVENTS:**\n- 4 | reveal | Lumia | east wing | Lumia admits the forgery | Riette\n2. 2 | travel | Kevin | docks | Kevin reaches the docks | none\nLEARNED:\n- Riette: the report was forged (overheard)\nSCENE: docks | Kevin | dusk\nNEXT: a | b | c";
  const p = M.parseMeta(raw);
  assert(p.events.length === 2 && p.events[1].where === "docks", "events: " + JSON.stringify(p.events));
  assert(p.learned.length === 1 && p.learned[0].who === "Riette", "learned");
  assert(p.scene && p.scene.where === "docks" && p.scene.when === "dusk", "scene not polluted by NEXT");
  const d = M.validateMeta(raw); assert(d.multi && d.events.valid === 2 && d.learned.valid === 1 && d.scene.valid && !d.issues.length, JSON.stringify(d));
});
t("validateMeta reports malformed parts without throwing (v36)", () => {
  const d = M.validateMeta("x\n[[META]]\nEVENTS: banana | gossip | | hall | ; 3 | action | Kevin\nLEARNED: Kevin knows things\nSCENE: hall");
  assert(d.events.total === 2 && d.events.valid === 0, "events invalid");
  assert(d.issues.some(i => i.includes("importance")) && d.issues.some(i => i.includes("fields")) && d.issues.some(i => i.startsWith("LEARNED")) && d.issues.some(i => i.startsWith("SCENE")), JSON.stringify(d.issues));
  const n = M.validateMeta("no block at all"); assert(!n.block && n.issues[0] === "no [[META]] block", "no block");
  const m = M.validateMeta("x\n[[META]]\nCAST: none"); assert(m.issues.includes("EVENTS missing") && m.issues.includes("SCENE missing"), "missing keys");
});
t("bold keys like **EVENTS:** keep the right importance (v36)", () => {
  const raw = "x\n[[META]]\n**EVENTS:** 2 | action | Ilse, Tamsin | bedchamber | Ilse visits Orla | none\n**LEARNED:** none\n**SCENE:** bedchamber | Tamsin | night";
  const p = M.parseMeta(raw); assert(p.events.length === 1 && p.events[0].imp === 2, "importance " + (p.events[0] || {}).imp);
  assert(p.learned.length === 0 && p.scene.where === "bedchamber", "none and scene");
  const d = M.validateMeta(raw); assert(!d.issues.length, JSON.stringify(d.issues));
});
t("importance written as a word is understood (v36)", () => {
  const p = M.parseMeta("x\n[[META]]\nEVENTS: high | reveal | Tamsin | cellar | Tamsin learns the truth | none; critical | death | Orla | bedchamber | Lady Orla dies | Tamsin; banana | action | Kevin | hall | Kevin waits | none");
  assert(p.events.map(e => e.imp).join(",") === "4,5,3", p.events.map(e => e.imp).join(","));
  const d = M.validateMeta("x\n[[META]]\nEVENTS: high | reveal | Tamsin | cellar | Tamsin learns the truth | none\nLEARNED: none\nSCENE: a | b | c");
  assert(!d.issues.length && d.recovered === 1, JSON.stringify(d));
});
console.log(`\n${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
