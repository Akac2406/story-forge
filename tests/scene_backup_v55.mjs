// Exercise the Settings backup handlers with disposable data and browser API doubles.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const html = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
const scenes = readFileSync(new URL("../site/cinematic-scenes-v54.js", import.meta.url), "utf8");
const settings = html.slice(html.indexOf("function vSettings(){"));
const setup = settings.slice(0, settings.indexOf('  ap(m,h("h2",{text:"AI service"})'));
const controls = settings.split("\n").find(line => line.includes('text:"Save or send a backup"'));
assert.ok(setup && controls);

const preset = {
  background: "data:image/jpeg;base64,YQ==",
  portrait: "Pilot",
  caption: "Night shift",
};
const original = {id: "turn-1", turns: [{role: "ai", text: "The lights come on."}]};
const retained = {id: "local", turns: [{role: "ai", text: "Local story text."}]};
const state = sessions => ({stories: [], sessions, chars: [], key: "test-secret", refs: ["private"]});

function device(sessions, presets = {}) {
  const elements = new Map();
  const notices = [];
  let stored = JSON.stringify(presets);
  let download;
  let quota = false;
  const context = vm.createContext({
    app: {}, view: {n: "settings"}, back() {}, render() {}, save() {}, applyFs() {},
    norm: data => ({sessions: [], stories: [], chars: [], ...data}),
    ap() {},
    h(tag, props) {
      const element = {...props, click() {}, remove() {}};
      if (tag === "input") elements.set("file", element);
      if (props?.text) elements.set(props.text, element);
      return element;
    },
    confirmBtn() {},
    Blob,
    URL: {createObjectURL(blob) { download = blob; return "blob:fixture"; }},
    FileReader: class {
      readAsText(file) { this.result = file; this.onload(); }
    },
    toast: message => notices.push(message),
    window: {},
    document: {readyState: "loading", addEventListener() {}, body: {}},
    navigator: {},
    DB: state(structuredClone(sessions)),
    localStorage: {
      getItem: () => stored,
      setItem(key, value) {
        assert.equal(key, "sf-v54-scene-presets");
        if (quota) throw new Error("Quota exceeded");
        stored = value;
      },
    },
  });
  vm.runInContext(scenes, context);
  // Evaluate the real input and action callbacks without unrelated Settings controls.
  vm.runInContext(setup + "ap(m," + controls + "\nvSettings();", context);
  return {
    async backup() {
      await elements.get("Save or send a backup").onclick();
      return JSON.parse(await download.text());
    },
    add(data) {
      elements.get("Add stories from a backup").onclick();
      elements.get("file").onchange({target: {files: [JSON.stringify(data)]}});
    },
    get scenes() { return JSON.parse(stored); },
    get sessions() { return JSON.parse(JSON.stringify(context.DB.sessions)); },
    get message() { return notices.at(-1); },
    setQuota(value) { quota = value; },
  };
}

const backup = await device([original], {[original.id]: preset, orphan: preset}).backup();
assert.deepEqual(backup.scenePresets, {[original.id]: preset});
assert.equal("key" in backup, false);
assert.equal("refs" in backup, false);

const target = device([retained], {[retained.id]: preset});
target.add(backup);
assert.deepEqual(target.sessions, [retained, original]);
assert.deepEqual(target.scenes, {[retained.id]: preset, [original.id]: preset});
target.add({...backup, sessions: [{...original, turns: []}],
  scenePresets: {[original.id]: {...preset, caption: "Duplicate"}}});
assert.deepEqual(target.sessions, [retained, original]);
assert.equal(target.scenes[original.id].caption, preset.caption);

const legacy = device([]);
const {scenePresets, ...oldBackup} = backup;
legacy.add(oldBackup);
assert.deepEqual(legacy.sessions, [original]);
assert.deepEqual(legacy.scenes, {});
legacy.add({...backup, scenePresets: {[original.id]: {...preset, background: "https://example.test/remote.jpg"}}});
assert.deepEqual(legacy.scenes, {});

const full = device([retained], {[retained.id]: preset});
full.setQuota(true);
full.add(backup);
assert.match(full.message, /Scene artwork could not be saved/);
assert.deepEqual(full.scenes, {[retained.id]: preset});
assert.deepEqual(full.sessions, [retained, original]);
full.setQuota(false);
full.add(backup);
assert.deepEqual(full.scenes, {[retained.id]: preset, [original.id]: preset});
assert.deepEqual(full.sessions, [retained, original]);
console.log("PASS: Settings backup round trip, private-field exclusion, older backups, collision protection, invalid artwork, and quota retry");
