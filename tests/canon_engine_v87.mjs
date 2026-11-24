// v87 canon engine unit checks (no browser, no network). Run: node tests/canon_engine_v87.mjs
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const ctx = vm.createContext({});
vm.runInContext(readFileSync(new URL("../site/canon-engine.js", import.meta.url), "utf8"), ctx);
const C = ctx.SFCanon;
let n = 0; const ok = (c, m) => { assert.ok(c, m); n++; };

// word matching
ok(!C.hasKey("Anna walks in", "Ann"), "Ann does not match Anna");
ok(C.hasKey("Ann walks in", "Ann"), "Ann matches Ann");
ok(C.hasKey("Kakashi's mask slips", "Kakashi"), "possessive matches");
ok(C.hasKey("two Sharingans glow", "Sharingan"), "plural matches");
ok(C.hasKey("the Hidden Leaf gate", "Hidden Leaf"), "multi-word key matches");
ok(!C.hasKey("hidden leafy gate", "Hidden Leaf"), "partial word does not match");

// canon mode
ok(C.mode({}, {follow: "strict"}) === "strict" && C.mode({}, {follow: "loose"}) === "adaptive", "follow maps to modes");
ok(C.mode({canonMode: "au"}, {canonMode: "strict"}) === "au", "session mode beats story mode");
ok(C.mode({}, {follow: "keep the Chunin exams but change the ending"}) === "adaptive", "custom follow text reads as adaptive");

// retrieval: score order, budget, locked
const st = {entries: [
  {k: "Old Friend", t: "x".repeat(900), a: false},
  {k: "Itachi, Itachi Uchiha", t: "Itachi is loyal to the Leaf in secret.", pri: 3},
  {k: "Hokage Rock", t: "Faces carved into the cliff.", a: true},
  {k: "Chakra", t: "Chakra rules: hand seals mold it.", lock: true, id: "rule-chakra"},
  {k: "Sasuke", t: "Sasuke seeks his brother.", aliases: "the avenger"},
]};
const hist = [{role: "user", text: "I train."}, {role: "ai", text: "Old Friend waves from afar."}];
let L = C.lore(st, {}, hist, "I ask Itachi about the avenger.", {budget: 200, present: []});
ok(L.locked.includes("hand seals") && L.lockedIds[0] === "rule-chakra", "locked entry always included");
ok(L.included[0].id === "entry-2" && L.included[1].id === "entry-1", "always-include entry first, then the entry named in the action");
ok(L.included.some(x => x.id === "entry-4"), "alias match includes entry");
ok(L.dropped.some(x => x.id === "entry-0" && x.reason === "over budget"), "over-budget entry reported, not silently lost");
L = C.lore(st, {}, hist, "I sit down.", {budget: 7000, present: ["Sasuke"]});
ok(L.included.some(x => x.id === "entry-4" && /in scene/.test(x.why)), "character present in scene pulls their entry");
ok(L.dropped.some(x => x.id === "entry-1" && /not relevant/.test(x.reason)), "unmentioned entry is reported as not relevant");

// notes
const DB = {globalNote: "Keep dialogue natural.", notes: [
  {id: "n1", text: "Never let Sakura heal anyone.", pri: "must", scope: {type: "character", value: "Sakura"}},
  {id: "n2", text: "Mention the rain.", pri: "style", scope: {type: "always"}},
  {id: "n3", text: "Old note", pri: "must", on: false},
  {id: "n4", text: "Ch 2 only", pri: "should", scope: {type: "chapter", value: "2"}},
]};
const se = {note: "Itachi must stay mysterious.", notes: [{id: "s1", text: "Sasuke is 13.", pri: "must", scope: {type: "keyword", value: "Sasuke, age"}}]};
let N = C.notes(DB, se, {}, [], "I wave at Sakura.", {present: [], chapter: 1});
const ids = N.active.map(x => x.id);
ok(ids.includes("legacy-global") && ids.includes("legacy-story"), "legacy notes read as must notes");
ok(ids.includes("n1") && !ids.includes("s1") && !ids.includes("n4"), "scopes resolve: character yes, keyword no, chapter no");
ok(N.inactive.find(x => x.id === "n3").reason === "turned off", "turned-off note reported");
ok(N.inactive.find(x => x.id === "s1")?.reason === "keyword not in this scene" && N.inactive.find(x => x.id === "n4")?.reason === "outside its chapters", "out-of-scope notes reported with reasons");
ok(N.active[N.active.length - 1].pri === "style", "notes ordered must > should > style");
N = C.notes(DB, se, {}, [], "Sasuke glares.", {chapter: 2});
ok(N.active.some(x => x.id === "s1") && N.active.some(x => x.id === "n4"), "keyword and chapter scopes switch on");

// standing OOC
const long = [
  {role: "user", text: "(OOC: from now on, keep chapters short)"}, {role: "ai", text: "ok"},
  {role: "user", text: "(OOC: describe the hat)"}, {role: "ai", text: "ok"},
  {role: "user", text: "(OOC: never kill Naruto)"}, {role: "ai", text: "ok"},
];
ok(JSON.stringify(C.standingOoc(long, 4)) === JSON.stringify(["from now on, keep chapters short"]), "only lasting OOC from trimmed turns is kept");
ok(C.detectStandingOoc("I nod. (OOC: Never kill Naruto)").length === 1 && C.detectStandingOoc("(OOC: describe the hat)").length === 0, "detectStandingOoc");

// mandatory block and echo
const mb = C.mandatoryBlock(C.notes(DB, se, {}, [], "Sakura", {present: ["Sakura"]}), "- Chakra: rules", "- Rae owns the ship", ["keep it short"]);
ok(mb.indexOf("MUST follow") < mb.indexOf("Earlier standing") && mb.indexOf("Earlier standing") < mb.indexOf("Locked canon") && mb.includes("Player-confirmed"), "mandatory block order");
ok(C.echo(C.notes(DB, se, {}, [], "", {}), ["x"]).includes("re-check"), "echo present");
ok(C.precedence("au").includes("story record of this playthrough") && C.precedence("strict").includes("locked canon and the story record"), "precedence per mode");

// divergences
ok(C.metaLine({}, {entries: []}) === "" && C.metaLine({canonMode: "creative"}, st) === "" && C.metaLine({}, st).includes("CANON:"), "CANON meta line only when useful");
const pd = C.parseDivergence("Itachi | drift | made him openly evil; Hokage Rock | player-choice | the player blew it up");
ok(pd.length === 2 && pd[0].kind === "drift" && pd[1].kind === "player-choice", "parse CANON line");
ok(C.parseDivergence("none").length === 0, "none parses to nothing");
const s2 = {canonMode: "au"};
C.record(s2, st, 5, "t5", pd);
ok(s2.divergences.length === 2 && s2.divergences[0].kind === "au" && s2.divergences[0].status === "accepted", "AU mode records drift as au");
const s3 = {}; C.record(s3, st, 5, "t5", pd); C.record(s3, st, 5, "t5", pd);
ok(s3.divergences.length === 2 && s3.divergences[0].status === "open", "strict drift is open; duplicates ignored");
C.record(s3, st, 9, "t9", [{entry: "Sasuke", kind: "drift", text: "x"}]);
const b = JSON.parse(JSON.stringify(s3)); C.trimForBranch(b, 6);
ok(b.divergences.length === 2 && b.divergences.every(d => d.turn < 6), "branch trims later divergences");
ok(C.localChecks({dead: ["Kakashi"]}, 'The door opens.\n\nKakashi | "Yo."').length === 1, "dead character speaking is flagged");
ok(C.localChecks({dead: ["Kakashi"]}, "They mourn Kakashi.").length === 0, "mentioning a dead character is fine");

// prompt size control
const A = C.assemble([{name: "role", text: "R".repeat(100), keep: true}, {name: "wiki", text: "W".repeat(500), drop: 6},
  {name: "record", text: "S".repeat(300), drop: 1}, {name: "notes", text: "N".repeat(200), keep: true}], 700);
ok(A.report.trimmed.join() === "wiki" && A.text.includes("N") && A.text.includes("S"), "highest-drop optional section trimmed first; kept sections stay");

// Phase 2 knowledge view (read-only)
const M = {charView: (s, n) => n === "Rae" ? {knows: ["The ledger is forged"]} : {knows: []}};
const sk = {mem: {scene: {where: "dock", who: ["Rae", "Dale"], when: "night"}, facts: [{id: "f1", text: "The ledger is forged"}],
  chars: {Rae: {knows: ["f1"]}, Dale: {knows: []}}, events: [{imp: 4, text: "Rae found the ledger"}]}};
const K = C.knowledge(sk, M);
ok(K.includes("Rae knows: The ledger is forged") && K.includes("Dale Does NOT know: The ledger is forged") && K.includes("Rae found the ledger"), "knowledge lists who knows and who does not");

// timeline markers and extraction
const tl = C.lore({entries: [{k: "Sasuke", t: "Sasuke is in the Leaf.", before: "he defects", id: "s"}, {k: "Seal", t: "The seal holds.", lock: true, after: "the Kyuubi attack"}]}, {}, [], "Sasuke waits", {});
ok(tl.text.includes("[until: he defects]") && tl.locked.includes("[applies from: the Kyuubi attack]"), "timeline markers shown with canon entries");
const sug = C.suggestEntries(["Kakashi Hatake raised his hand. The Hokage watched.", "Kakashi Hatake smiled at the Hokage of the Leaf.", "Later Kakashi Hatake left. The Hokage sighed.", "Kakashi Hatake returned."], [{k: "Hokage"}]);
ok(sug.length && sug[0].k === "Kakashi Hatake" && sug[0].src === "source" && !sug.some(x => x.k === "Hokage") && !sug.some(x => x.k === "The"), "extraction suggests recurring names not already in the Bible");
console.log(`${n} passed, 0 failed`);
console.log("ERRORS: []");
