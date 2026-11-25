// Exercise the Settings backup handlers with disposable data and browser API doubles.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const html = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
const scenes = readFileSync(new URL("../site/cinematic-scenes-v54.js", import.meta.url), "utf8");
const persistence = html.slice(html.indexOf("const pendingChapterRewrites="), html.indexOf("function idbOpen("));
const settings = html.slice(html.indexOf("function vSettings(){"));
const setup = settings.slice(0, settings.indexOf('  ap(m,h("h2",{text:"AI service"})'));
const controls = settings.split("\n").find(line => line.includes('text:"Save or send a backup"'));
assert.ok(setup && controls);

const preset = {
  background: "data:image/jpeg;base64,YQ==",
  portrait: "Pilot",
  caption: "Night shift",
  backgroundPosition: "top",
  backgroundLight: "bright",
  portraitPosition: "right",
  portraitSize: "small",
};
const avatar = {id: "avatar", name: "Angelice", desc: "White hair and silver eyes."};
const story = {id: "story", title: "The Lantern", storyDescription: "A pilot returns home."};
const template = {id: "template", name: "Lantern setup", story: {title: story.title, storyDescription: story.storyDescription}};
const original = {id: "turn-1", storyId: story.id, cid: avatar.id, note: story.storyDescription, turns: [{role: "ai", text: "The lights come on."}]};
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
  vm.runInContext(persistence + setup + "ap(m," + controls + "\nvSettings();", context);
  return {
    seedSetup(stories, chars, storyTemplates) { Object.assign(context.DB, {stories, chars, storyTemplates}); },
    async backup() {
      await elements.get("Save or send a backup").onclick();
      return JSON.parse(await download.text());
    },
    add(data) {
      elements.get("Add stories from a backup").onclick();
      elements.get("file").onchange({target: {files: [JSON.stringify(data)]}});
    },
    get scenes() { return JSON.parse(stored); },
    get setup() { return JSON.parse(JSON.stringify({stories: context.DB.stories, chars: context.DB.chars})); },
    get templates() { return JSON.parse(JSON.stringify(context.DB.storyTemplates || [])); },
    get sessions() { return JSON.parse(JSON.stringify(context.DB.sessions)); },
    get message() { return notices.at(-1); },
    setQuota(value) { quota = value; },
  };
}

const source = device([original], {[original.id]: preset, orphan: preset});
source.seedSetup([story], [avatar], [template]);
const backup = await source.backup();
assert.deepEqual(backup.stories, [story]);
assert.deepEqual(backup.chars, [avatar]);
assert.deepEqual(backup.storyTemplates, [template]);
assert.deepEqual(backup.scenePresets, {[original.id]: preset});
assert.equal("key" in backup, false);
assert.equal("refs" in backup, false);

const target = device([retained], {[retained.id]: preset});
target.add(backup);
assert.deepEqual(target.setup, {stories: [story], chars: [avatar]});
assert.deepEqual(target.templates, [template]);
assert.deepEqual(target.sessions, [retained, original]);
assert.deepEqual(target.scenes, {[retained.id]: preset, [original.id]: preset});
target.add({...backup, sessions: [{...original, turns: []}],
  scenePresets: {[original.id]: {...preset, caption: "Duplicate"}}});
assert.deepEqual(target.sessions, [retained, original]);
assert.equal(target.scenes[original.id].caption, preset.caption);
assert.deepEqual(target.templates, [template]);

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

// Drive the scene editor through its controls with disposable storage.
function element(tag) {
  return {
    tag, children: [], dataset: {}, textContent: "",
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = children; },
    setAttribute() {}, remove() {}, focus() {},
  };
}
const body = element("body");
const log = {before: art => { mounted = art; }};
let mounted;
let storage = JSON.stringify({demo: {...preset, portrait: "Rae"}});
let quotaFailure = false;
const charPic = "data:image/png;base64,Yg==";
const sceneSession = {id: "demo", storyId: "demo-story", cast: {Rae: {pic: charPic}}};
const browser = vm.createContext({
  view: {n: "chat", id: "demo"},
  DB: {sessions: [sceneSession], chars: []},
  getStory: () => ({cast0: [{n: "Avery", th: "data:image/png;base64,Yw=="}]}),
  render() {},
  window: {},
  document: {
    readyState: "loading", addEventListener() {}, body,
    createElement: element,
    querySelector: selector => selector === "#log" ? log : selector === "#app>header" ? {after() {}} : null,
  },
  localStorage: {
    getItem: () => storage,
    setItem(key, value) {
      if (quotaFailure) throw Error("Quota exceeded");
      storage = value;
    },
  },
});
vm.runInContext(scenes, browser);
const api = browser.window.SFScenesV54;
api.open();
const overlay = () => body.children.at(-1);
function* descendants(node) {
  yield node;
  for (const child of node.children) yield* descendants(child);
}
const text = label => [...descendants(overlay())].find(node => node.textContent === label);
const preview = () => [...descendants(overlay())].find(node => node.className === "sf54-stage");
const place = text("Portrait placement").children[0];
assert.equal(place.value, "right");
place.value = "left";
place.onchange();
assert.equal(preview().dataset.portraitPosition, "left");
assert.equal(preview().children.find(node => node.className === "sf54-portrait").src, charPic);
const picker = text("Character portrait").children[0];
assert(picker.children.some(option => option.value === "Avery"));
assert.equal(JSON.parse(storage).demo.portraitPosition, "right");
text("Remove background").onclick();
assert(!preview().children.some(node => node.className === "sf54-bg"));
quotaFailure = true;
text("Save scene").onclick();
assert.equal(JSON.parse(storage).demo.portraitPosition, "right");
quotaFailure = false;
text("Save scene").onclick();
assert.equal(mounted.dataset.portraitPosition, "left");
assert.equal(JSON.parse(storage).demo.background, "");
assert.equal(JSON.parse(storage).demo.caption, preset.caption);
api.open();
assert.equal(text("Portrait placement").children[0].value, "left");
text("Cancel").onclick();

const oldScene = {background: preset.background, portrait: "", caption: "Legacy scene"};
assert(api.importPresets({old: oldScene}, [{id: "old"}]));
assert.deepEqual(JSON.parse(storage).old, oldScene);
console.log("PASS: live preview, stored cast portraits, crop settings and quota-safe save.");


const packaged = api.exportPresets([sceneSession], true);
assert.equal(packaged.demo.portraitImage, charPic);
assert(!Object.hasOwn(JSON.parse(storage).demo, "portraitImage"));
const transferred = {id: "copy", storyId: "copy-story"};
quotaFailure = true;
assert.equal(api.importPresets({copy: packaged.demo}, [transferred]), false);
assert(!Object.hasOwn(JSON.parse(storage), "copy"));
quotaFailure = false;
assert(api.importPresets({copy: packaged.demo, unrelated: packaged.demo}, [transferred]));
assert(!Object.hasOwn(JSON.parse(storage), "unrelated"));
browser.DB.sessions.push(transferred);
browser.view.id = transferred.id;
browser.render();
assert.equal(mounted.children.find(node => node.className === "sf54-portrait").src, charPic);
assert.equal(mounted.dataset.portraitPosition, "left");
api.open();
assert.equal(text("Character portrait").children[0].value, "Rae");
text("Save scene").onclick();
assert.equal(JSON.parse(storage).copy.portraitImage, charPic);

const invalid = {...packaged.demo, portraitImage: "https://example.test/portrait.png"};
assert(api.importPresets({invalid}, [{id: "invalid"}]));
assert(!Object.hasOwn(JSON.parse(storage).invalid, "portraitImage"));
console.log("PASS: packaged scene artwork, portrait fallback, import isolation and quota failure.");

const readScene = html.slice(html.indexOf("function cinematicScene("), html.indexOf("function vChat()"));
const cinematic = vm.createContext({
  h(tag, attrs, ...children) {
    return {...element(tag), attrs, children: children.filter(Boolean),
      get childElementCount() { return this.children.length; }};
  },
  ap: (parent, child) => parent.append(child),
  fill: (parent, text) => { parent.textContent = text; },
  idbImg: id => ({tag: "img", attrs: {id}, children: []}),
  readerCover: () => ({tag: "img", attrs: {cover: true}, children: []}),
});
vm.runInContext(readScene, cinematic);
const sharedPreset = api.readerPreset(transferred);
assert.equal(sharedPreset.selectedImage, charPic);
assert.equal(sharedPreset.portraitPosition, "left");
const configured = {...sharedPreset, background: preset.background, backgroundPosition: "top", backgroundLight: "soft"};
const played = cinematic.cinematicScene(transferred, {}, {
  text: "The hangar doors opened.\n\nAvery | We have an hour.\n\nRae | I can help.",
}, configured);
const [art, caption, dialogue] = played.children;
const [background, portrait] = art.children;
assert.equal(background.attrs.src, preset.background);
assert.equal(background.attrs["data-background-position"], "top");
assert.equal(background.attrs["data-background-light"], "soft");
assert.equal(art.attrs["data-portrait-position"], "left");
assert.equal(art.attrs["data-portrait-size"], "small");
assert.equal(caption.attrs.text, preset.caption);
assert.equal(portrait.children[0].attrs.src, charPic);
const next = [...descendants(dialogue)].find(node => node.attrs?.text === "Next passage");
next.attrs.onclick();
assert.equal(portrait.children.length, 0);
next.attrs.onclick();
assert.equal(portrait.children[0].attrs.src, charPic);

const generated = cinematic.cinematicScene(sceneSession, {}, {text: "Rae | Go now.", img: "123"}, configured);
assert.equal(generated.children[0].children[0].attrs.id, "gen:123");
assert.equal(generated.children[0].children[1].children[0].attrs.src, charPic);
const plain = cinematic.cinematicScene(sceneSession, {}, {text: "The lights flickered."}, null);
assert.equal(plain.children[0].children[0].attrs.cover, true);
assert.equal(plain.children.length, 2);
console.log("PASS: cinematic framing, captions, speaker portraits and background precedence.");
