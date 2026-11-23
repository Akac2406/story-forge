import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const html = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
const audioCode = html.slice(html.indexOf("const TTS="), html.indexOf("function chParas("));
let elapsed = 0;
let activation = false;
let serial = 0;
const timers = new Map();
const queue = [];
const spoken = [];
const notices = [];
const engine = {
  getVoices: () => [],
  speak(utterance) {
    spoken.push({utterance, activation});
    queue.push(utterance);
  },
  cancel() {
    for (const utterance of queue.splice(0)) utterance.onerror?.({error: "canceled"});
  },
};
const context = vm.createContext({
  DB: {spk: false}, view: {n: "fixture"}, navigator: {},
  window: {speechSynthesis: engine, SpeechSynthesisUtterance() {}},
  speechSynthesis: engine,
  SpeechSynthesisUtterance: class { constructor(text) { this.text = text; } },
  performance: {now: () => elapsed},
  setTimeout(callback, delay) { const id = ++serial; timers.set(id, {callback, delay}); return id; },
  clearTimeout: id => timers.delete(id),
  setInterval: () => 1, clearInterval() {},
  toast: message => notices.push(message),
  $: () => null,
  h: (tag, attrs, ...children) => ({tag, attrs, children}),
  ic: () => null,
});
vm.runInContext(audioCode, context);
const state = vm.runInContext("TTS", context);
function gesture(action) {
  activation = true;
  try { action(); } finally { activation = false; }
}
function resumeButton() {
  return context.playerEl().children[0].children.find(node => node.attrs?.["aria-label"] === "Resume reading");
}

gesture(() => context.ttsStart([
  "Chapter one starts by the river.",
  "Chapter two opens inside the old observatory.",
  "Mara unlocks the window and finds a map.",
], "chapters 1–3"));
assert.equal(spoken.length, 1);
assert(spoken[0].activation);
const old = queue[0];
old.onstart();
elapsed = 300;
assert(context.ttsPosition() > 0);
const seek = state.timeline[1].start + 2.1 * state.timeline[1].step;
gesture(() => context.ttsSeek(seek));
assert(spoken.at(-1).activation, "Seek must submit speech within the interaction");
assert.equal(queue.length, 1);
assert.equal(queue[0].text, "opens inside the old observatory.");
old.onend();
assert.equal(queue.length, 1, "A canceled utterance cannot advance the new queue");
const target = state.position;
elapsed = 2000;
assert.equal(context.ttsPosition(), target, "The timer waits for the new utterance to start");
const second = queue.shift();
second.onstart();
elapsed = 2400;
assert(context.ttsPosition() > target);
second.onend();
assert.equal(queue[0].text, "Mara unlocks the window and finds a map.");
assert.equal(queue.length, 1, "Narration advances one chunk at a time");

const stalled = state.position;
const timeout = timers.get(state.startTimer);
assert.equal(timeout.delay, 4000);
timeout.callback();
assert(state.on && state.paused, "A missing start becomes resumable");
assert.equal(context.ttsPosition(), stalled);
assert.match(notices.at(-1), /Tap Resume/);
gesture(() => resumeButton().attrs.onclick());
assert(spoken.at(-1).activation);
assert.equal(queue[0].text, "Mara unlocks the window and finds a map.");
const resumed = queue.shift();
resumed.onstart();
resumed.onend();
assert.equal(state.on, false, "Natural end closes the player");

gesture(() => context.ttsStart(["Another chapter."], "chapter"));
queue[0].onerror({error: "not-allowed"});
assert(state.on && state.paused);
assert.equal(context.ttsPosition(), 0);
context.ttsStop();
assert.equal(timers.size, 0);
console.log("PASS: chapter seek uses the active gesture, ignores stale callbacks, and recovers from silent or rejected starts.");
