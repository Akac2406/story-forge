import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const html = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
const section = (start, end) => {
  const from = html.indexOf(start);
  const to = html.indexOf(end, from);
  assert(from >= 0 && to > from);
  return html.slice(from, to);
};

const first = {id: "first", name: "Angelice", desc: "White hair\nSilver eyes", trait: "Calculating"};
const second = {id: "second", name: "Angelice", desc: "Short black hair", trait: "Curious"};
const DB = {stories: [], chars: [first, second], sessions: [], modes: [{n: "Test"}], globalNote: "Keep dialogue natural."};
const messages = [];
let serial = 0;
let currentSheet;
let destination;
const node = (tag, attrs, ...children) => ({
  tag, attrs, children: children.flat(Infinity).filter(Boolean),
  replaceChildren() { this.children = []; },
});
const control = (value, change) => ({value, change});
const context = vm.createContext({
  DB,
  STYLES: [],
  ctlText: () => "",
  fmtPrompt: () => "",
  loreFor: () => "",
  visText: () => "",
  recText: () => "",
  rsText: () => "",
  ed: () => [],
  rsOn: () => false,
  memOn: () => false,
  lenLabel: value => value+" words",
  rawFrom: () => 0,
  window: {},
  h: node,
  ap: (parent, ...children) => parent.children.push(...children.flat(Infinity).filter(Boolean)),
  sheet: (title, content) => { currentSheet = {title, content}; },
  fld: (label, input) => node("label", {text: label}, input),
  sel: (value, options, change) => control(value, change),
  area: control,
  inp: control,
  busy: false,
  soft() {},
  save() {},
  render() {},
  begin() {},
  go(next) { destination = next; },
  confirmBtn: (text, onclick) => node("button", {text, onclick}),
  toast: text => messages.push(text),
  hasKey: () => true,
  uid: () => "new-" + ++serial,
  sd: () => [],
  chapsOf: session => session.chaps || [{i: 0}],
  GUIDE: "Quill",
  SIMHI: "Welcome",
});
// v87: the prompt builder uses the canon engine (site/canon-engine.js).
vm.runInContext(readFileSync(new URL("../site/canon-engine.js", import.meta.url), "utf8"), context);
vm.runInContext([
  section("function avatarSetup(", "function vStory("),
  section("function play(", "function begin("),
  section("const PROGRESSION=", "function worldDay("),
  section("function worldDay(", "function worldScheduleSheet("),
  section("const SIMF=", "function applySim("),
  section("function branchAt(", "function saveSheet("),
  section("const ERA_PRESETS=", "function buildMsgs("),
  section("function buildMsgs(", "function applyMeta("),
  section("const WORLD_SHARE_FIELDS=", "function worldSharingSheet("),
  section("const STORY_TEMPLATE_FIELDS=", "function storyBanner("),
  section("function storyConsequences(", "function recSheet("),
].join("\n"), context);

const setup = context.avatarSetup(first);
context.savedAvatarField(setup).children[0].change("second");
assert.equal(context.savedAvatarField(setup).children[0].value, "second");
assert.equal(setup.desc, second.desc);
const premise = "Reincarnated at age ten.\nShe rebuilds the company.";
context.storyDescriptionField("", text => { setup.storyDescription = text; }).children[0].change(premise);
context.play({id: "story", kind: "story"}, {...setup, desc: "A session-specific appearance"});
const original = DB.sessions[0];
assert.equal(original.cid, "second");
assert.equal(original.char.desc, "A session-specific appearance");
assert.equal(original.note, premise);
assert.equal(DB.chars[0], second);
assert.equal(second.desc, "Short black hair");
assert.equal(first.desc, "White hair\nSilver eyes");

context.play({id: "sim", kind: "story", sim: true}, setup);
assert(context.simMsgs(DB.sessions[1], {}, "Begin")[0].content.includes(premise));
context.play({id: "other", kind: "story"}, {name: "New avatar", desc: "New description"});
assert.equal(DB.chars[0].desc, "New description");
assert.equal(DB.sessions[2].note, "");
assert.equal(DB.globalNote, "Keep dialogue natural.");

original.turns = [
  {role: "user", text: "Begin"},
  {role: "ai", text: "The office opens."},
  {role: "user", text: "Check the paperwork."},
  {role: "ai", text: "The logbook needs an audit."},
];
const deadline = {kind: "Deadline", text: "Logbook audit", day: 1, createdAfter: 4};
original.worldSchedule = [deadline];
context.reviewStoryChanges(original);
const descend = function* (element) {
  yield element;
  for (const child of element.children || []) yield* descend(child);
};
const find = (root, label) => [...descend(root)].find(el => el.attrs?.text === label);
assert(!find(currentSheet.content, "Review due entry · Logbook audit"));

const skipPrompt = context.worldSchedulePrompt(original, original.turns, 1);
assert.match(skipPrompt, /reached by this skip, Deadline/);
original.turns.push(
  {role: "user", text: "A day passes.", worldDays: 1},
  {role: "ai", text: "The manager finishes reviewing the logbook."},
);
context.reviewStoryChanges(original);
assert(find(currentSheet.content, "Review due entry · Logbook audit"));
find(currentSheet.content, "Outcome").children[0].change("Resolved");
find(currentSheet.content, "Review note").children[0].change("The audit was filed.");
find(currentSheet.content, "Effect on future scenes (optional)").children[0].change("The public desk opens again.");
find(currentSheet.content, "Accept").attrs.onclick();
assert.equal(context.worldScheduleState(deadline, 6).status, "Resolved");
assert(!find(currentSheet.content, "Review due entry · Logbook audit"));
assert.match(context.worldSchedulePrompt(original, original.turns, 0), /Resolved, Deadline.*The audit was filed\./);

const npcPlan = {kind: "Character plan", actor: "Manager", text: "Appoint a deputy", day: 1, createdAfter: 4};
context.recordWorldOutcome(npcPlan, 6, "Resolved", "The manager appointed Rae.", "Rae can now admit visitors.");
const missed = {kind: "Quest deadline", text: "Renew the permit", day: 1, createdAfter: 4, fallback: "Use the appeal process."};
context.recordWorldOutcome(missed, 6, "Missed", "No permit was filed.", "");
const cancelled = {kind: "Quest deadline", text: "Renew the old permit", day: 1, createdAfter: 4, fallback: "Old appeal route."};
context.recordWorldOutcome(cancelled, 6, "Cancelled", "The old permit was withdrawn.", "");
original.worldSchedule.push(npcPlan, missed, cancelled);
const link = {a: "Manager", b: "Rae", history: [
  {turn: 1, chapter: 1, note: "They went to school together."},
]};
original.relationshipLinks = [link];
original.mem = {events: [{t: 5, who: ["Manager", "Rae"], text: "The manager trusted Rae with the logbook."}]};
context.reviewStoryChanges(original);
find(currentSheet.content, "Accept").attrs.onclick();
assert.equal(link.history.at(-1).recordedAfter, 6);

const messagesFor = (session, turns = session.turns) =>
  context.buildMsgs(session, {kind: "story", title: "Harbor"}, turns, "I return to the office.");
const later = messagesFor(original);
assert.match(later[0].content, /public desk opens again/);
assert.match(later[0].content, /Character plan.*Manager.*appointed Rae.*Rae can now admit visitors/);
assert.match(later[0].content, /Effect on future scenes: Use the appeal process/);
assert.doesNotMatch(later[0].content, /Old appeal route/);
assert.match(later[0].content, /Manager \/ Rae: The manager trusted Rae with the logbook/);
assert.doesNotMatch(later.at(-1).content, /Playthrough schedule/);
assert.doesNotMatch(messagesFor(original, original.turns.slice(0, 2))[0].content, /Logbook audit|admit visitors|trusted Rae/);
assert.doesNotMatch(messagesFor(original, [...original.turns.slice(0, 5), {role: "ai", text: "A different reply."}])[0].content, /trusted Rae/);
const record = context.storyConsequences(original);
assert(find(record, "Consequences (6)"));
assert(find(record, "Effect on future scenes · The public desk opens again."));
assert(find(record, "Relationship · Manager / Rae"));

context.progressionSheet(original);
assert.equal(currentSheet.title, "Progression");
const sheetButton = text => find(currentSheet.content, text).attrs.onclick();
find(currentSheet.content, "Skill").children[0].change("Navigation");
find(currentSheet.content, "Rating (0 to 100)").children[0].change("45");
find(currentSheet.content, "Effect in the story (optional)").children[0].change("Can read coastal charts.");
sheetButton("Save entry");
assert(find(currentSheet.content, "Rating 45"));
find(currentSheet.content, "Category").children[0].change("item");
find(currentSheet.content, "Item").children[0].change("Harbor pass");
find(currentSheet.content, "Quantity (0 to 999)").children[0].change("2");
find(currentSheet.content, "Effect in the story (optional)").children[0].change("Admits the bearer to the harbor.");
sheetButton("Save entry");
assert(find(currentSheet.content, "Quantity 2"));
assert.equal(context.saveProgression(original, "reputation", "Port Authority", -30, "Guards ask for a witness."), true);
assert.equal(context.saveProgression(original, "skill", "Navigation", 101, ""), false);
assert.equal(context.saveProgression(original, "item", "harbor pass", 2, "Admits the bearer to the harbor."), true);
assert.equal(original.progression.length, 3);

const currentPrompt = messagesFor(original)[0].content;
assert.match(currentPrompt, /Navigation \(Rating 45\) — Can read coastal charts/);
assert.match(currentPrompt, /Harbor pass \(Quantity 2\)/);
assert.match(currentPrompt, /Port Authority \(Standing -30\)/);
assert.doesNotMatch(messagesFor(original, original.turns.slice(0, 4))[0].content, /Player-tracked RPG progression/);
assert.equal(JSON.stringify(context.portablePlaythrough(original).progression), JSON.stringify(original.progression));
const imported = context.importSharedWorld({
  format: "story-forge-world", version: 1,
  story: {kind: "story", title: "Harbor"},
  playthroughs: [context.portablePlaythrough(original)],
}).copies[0];
assert.equal(JSON.stringify(imported.progression), JSON.stringify(original.progression));
assert(context.saveProgression(imported, "item", "Harbor pass", 0, "Used at the gate.") === false);
DB.sessions.push(imported);
assert(context.saveProgression(imported, "item", "Harbor pass", 0, "Used at the gate."));
assert.match(messagesFor(imported)[0].content, /Harbor pass \(Quantity 0\)/);
assert.match(messagesFor(original)[0].content, /Harbor pass \(Quantity 2\)/);

const beforeBranch = JSON.stringify(original);
const beforeCreation = context.branchAt(original, 1);
assert.equal(beforeCreation.worldSchedule.length, 0);
const beforeOutcome = context.branchAt(original, 3);
assert.equal(beforeOutcome.worldSchedule.length, 4);
assert.equal(context.worldScheduleState(beforeOutcome.worldSchedule[0], 4).status, "Pending");
const afterOutcome = context.branchAt(original, 5);
assert.equal(context.worldScheduleState(afterOutcome.worldSchedule[0], 6).status, "Resolved");
assert.equal(afterOutcome.note, premise);
assert.equal(beforeCreation.relationshipLinks[0].history.length, 1);
assert.equal(beforeOutcome.relationshipLinks[0].history.length, 1);
assert.equal(afterOutcome.relationshipLinks[0].history.length, 2);
assert.doesNotMatch(messagesFor(beforeOutcome)[0].content, /admit visitors|public desk opens again|trusted Rae/);
assert.match(messagesFor(afterOutcome)[0].content, /public desk opens again/);
assert.equal(JSON.stringify(original), beforeBranch);
assert.equal(context.progressionState(beforeOutcome, 4).length, 0);
assert.match(messagesFor(afterOutcome)[0].content, /Navigation \(Rating 45\)/);
afterOutcome.turns.push({role: "user", text: "Use the pass."}, {role: "ai", text: "The guard cancels it."});
context.progressionSheet(afterOutcome);
find(currentSheet.content, "Category").children[0].change("item");
sheetButton("Edit Harbor pass");
sheetButton("Remove entry");
assert.doesNotMatch(messagesFor(afterOutcome)[0].content, /Harbor pass/);
assert.match(messagesFor(original)[0].content, /Harbor pass/);
const restored = context.branchAt(afterOutcome, 5);
assert.match(messagesFor(restored)[0].content, /Harbor pass/);
context.trimProgression(afterOutcome, 6);
assert.equal(context.progressionState(afterOutcome, 8).length, 3);
context.shiftProgressionAfterDeletion(afterOutcome, 5);
assert.equal(context.progressionState(afterOutcome, 5).length, 3);
const sourceStory = {
  id: "harbor-story", kind: "story", title: "Harbor", storyDescription: premise,
  starts: ["Before the audit"], entries: [{k: "Harbor", t: "Closes at sunset", a: true}],
  cast0: [{n: "Rae", role: "Deputy", img: "local-reference", th: "data:image/jpeg;base64,YQ=="}],
  coverT: "data:image/jpeg;base64,YQ==", proImg: "local-prologue", sessions: [original],
};
DB.stories.push(sourceStory);
context.storyTemplatesSheet();
assert.equal(currentSheet.title, "Story templates");
assert.equal(find(currentSheet.content, "Save as template").attrs.disabled, true);
find(currentSheet.content, "Source story").children[0].change(sourceStory.id);
find(currentSheet.content, "Template name").children[0].change("Harbor starter");
find(currentSheet.content, "Save as template").attrs.onclick();
assert.equal(DB.storyTemplates.length, 1);
assert.equal(context.saveStoryTemplate(sourceStory, " HARBOR STARTER "), false);
sourceStory.entries[0].t = "Closes at midnight";
find(currentSheet.content, "Use template").attrs.onclick();
assert.equal(destination.n, "edit");
assert.notEqual(destination.w.id, sourceStory.id);
assert.equal(destination.w.storyDescription, premise);
assert.equal(destination.w.entries[0].t, "Closes at sunset");
assert.equal(destination.w.cast0[0].role, "Deputy");
assert(!Object.hasOwn(destination.w, "coverT"));
assert(!Object.hasOwn(destination.w.cast0[0], "img"));
assert(!Object.hasOwn(destination.w, "sessions"));
const firstDraft = destination.w;
firstDraft.entries[0].t = "Always open";
find(currentSheet.content, "Use template").attrs.onclick();
assert.notEqual(destination.w.id, firstDraft.id);
assert.equal(destination.w.entries[0].t, "Closes at sunset");
assert.equal(context.portableStory(sourceStory).storyDescription, premise);
const stage = {
  background: "data:image/jpeg;base64,YQ==", portrait: "Rae", caption: "Night shift",
  portraitPosition: "right", portraitSize: "small",
};
context.window.SFScenesV54 = {
  exportPresets(sessions, includePortraits) {
    assert.equal(includePortraits, true);
    assert.equal(sessions.length, 2);
    return {[original.id]: stage, [afterOutcome.id]: {...stage, caption: "Branch"}};
  },
};
const setupPackage = context.makeWorldPackage(sourceStory, [], true);
assert.equal(setupPackage.playthroughs.length, 0);
assert(!Object.hasOwn(setupPackage, "scenePresets"));
const textPackage = context.makeWorldPackage(sourceStory, [original], false);
assert.equal(textPackage.playthroughs.length, 1);
assert(!Object.hasOwn(textPackage, "scenePresets"));
const worldPackage = context.makeWorldPackage(sourceStory, [original, afterOutcome], true);
worldPackage.scenePresets.unrelated = stage;
const worldCopy = context.importSharedWorld(worldPackage);
const [copiedOriginal, copiedBranch] = worldCopy.copies;
assert.notEqual(copiedOriginal.id, original.id);
assert.equal(copiedBranch.parent, copiedOriginal.id);
assert.equal(worldCopy.scenePresets[copiedOriginal.id].caption, "Night shift");
assert.equal(worldCopy.scenePresets[copiedBranch.id].portraitPosition, "right");
assert(!Object.hasOwn(worldCopy.scenePresets, original.id));
assert(!Object.hasOwn(worldCopy.scenePresets, "unrelated"));
assert.equal(Object.keys(context.importSharedWorld(textPackage).scenePresets).length, 0);
const simulatorSession = {
  ...original, id: "simulator", world: "The harbor", role: "Deputy harbor master",
  genre: "Mystery", nmode: "mystery", lenSet: true, dead: ["Arthur"],
  sim: {ph: "play", canon: "", prev: "Fog settles over the harbor.", ready: true,
    log: [{role: "user", text: "Set the opening at dawn."}, {role: "invalid", text: "Ignore."}]},
  cast: {Rae: {r: "Deputy", pic: "data:image/png;base64,YQ=="}, legacyEmpty: null},
};
const simulatorPackage = JSON.parse(JSON.stringify(context.makeWorldPackage(sourceStory, [simulatorSession], false)));
const simulatorCopy = context.importSharedWorld(simulatorPackage).copies[0];
assert.equal(simulatorCopy.sim.ph, "play");
assert.equal(simulatorCopy.sim.log.length, 1);
assert.equal(simulatorCopy.sim.log[0].text, "Set the opening at dawn.");
assert.equal(simulatorCopy.sim.prev, simulatorSession.sim.prev);
assert.equal(simulatorCopy.role, simulatorSession.role);
assert.equal(simulatorCopy.world, simulatorSession.world);
assert.equal(simulatorCopy.nmode, simulatorSession.nmode);
assert.equal(simulatorCopy.dead[0], "Arthur");
assert.equal(simulatorCopy.cast.Rae.pic, simulatorSession.cast.Rae.pic);
assert(!Object.hasOwn(simulatorCopy.cast, "legacyEmpty"));
assert.match(messagesFor(simulatorCopy)[0].content, /Deputy harbor master/);
assert.match(messagesFor(simulatorCopy)[0].content, /Harbor pass/);
const setupCopy = context.importSharedWorld(context.makeWorldPackage(sourceStory, [
  {...simulatorSession, sim: {...simulatorSession.sim, ph: "setup"}},
], false)).copies[0];
assert.equal(setupCopy.sim.ph, "setup");
assert.match(context.simMsgs(setupCopy, {}, "Proceed")[0].content, /Deputy harbor master/);

find(currentSheet.content, "Remove template").attrs.onclick();
assert.equal(DB.storyTemplates.length, 0);
assert.equal(DB.stories[0], sourceStory);

assert(!messages.some(text => text.includes("Reopen the review")));
console.log("Avatar descriptions, per-story notes, due-entry review, consequences in narrator context and Story Record, RPG progression, story templates, and branch cutoffs passed.");
