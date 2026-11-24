/* Story Forge memory trial (development tool, runs on a phone).
 * Loads a COPY of the app inside an iframe with its storage renamed (localStorage "sf-trial-db",
 * IndexedDB "sf-trial", no service worker), so the real stories ("story-forge-v2" / "story-forge")
 * are never opened for writing. It only READS the real settings to borrow the OpenCode key and
 * connector address, and checks at the end that the real data is byte-for-byte unchanged.
 * Memory is switched on for the test playthrough only; the global memv2 flag stays off.
 */
(async function () {
'use strict';
const $ = s => document.querySelector(s), sleep = ms => new Promise(r => setTimeout(r, ms));
const REAL = "story-forge-v2", TKEY = "sf-trial-db", TIDB = "sf-trial", PROG = "sf-trial-progress";
const h = (tag, attrs, ...kids) => { const e = document.createElement(tag); Object.entries(attrs || {}).forEach(([k, v]) => { if (k === "text") e.textContent = v; else if (k.startsWith("on")) e[k] = v; else if (v != null && v !== false) e.setAttribute(k, v === true ? "" : v) }); kids.flat().forEach(c => c != null && e.append(c)); return e };
const realBefore = localStorage.getItem(REAL);
let real = {}; try { real = JSON.parse(realBefore) || {} } catch (e) {}
const OC = { key: String(real.ocKey || ""), proxy: String(real.ocProxy || ""), mon: real.ocMon, day: real.ocDay, scale: real.ocScale };
const SCENS = [["trial/scenario.json", "The Glass Orchard — period mystery, 40 turns"], ["trial/scenario2.json", "Night Shift at Cedar Ridge — modern airport hangar, 30 turns"]];
let prog = null; try { prog = JSON.parse(localStorage.getItem(PROG)) } catch (e) {}
let scen, curSc = (prog && prog.opts && prog.opts.sc) || SCENS[0][0];
async function loadScen(f) { scen = await (await fetch(f, { cache: "no-store" })).json(); curSc = f }
try { await loadScen(curSc) } catch (e) { $("#setup").textContent = "Couldn’t load " + curSc + ". Upload the whole app folder, including the trial folder."; return }
let W = null, E = null, stop = false, wake = null;
const log = t => { const l = $("#log"); l.textContent += t + "\n"; l.scrollTop = l.scrollHeight };
const status = t => { $("#status").textContent = t };
const saveProg = () => { try { localStorage.setItem(PROG, JSON.stringify(prog)) } catch (e) {} };
const redact = s => { s = String(s); if (OC.key) s = s.split(OC.key).join("[REDACTED]"); if (OC.proxy) s = s.split(OC.proxy.replace(/\/+$/, "")).join("[CONNECTOR]"); return s.replace(/sk-[A-Za-z0-9_-]{12,}/g, "[REDACTED]") };

/* ---------- setup screen ---------- */
function drawSetup() {
  const box = $("#setup"); box.textContent = "";
  const have = !!(OC.key && OC.proxy), opt = { turns: String(scen.turns.length), len: "250", cap: "10", dry: !have };
  box.append(
    h("p", { class: have ? "ok" : "bad", text: have ? "✓ OpenCode key and connector found in your app’s Settings." : "✗ No OpenCode key or connector found. Set up OpenCode in the app’s Settings first. You can still do a free dry run." }),
    h("p", { class: "sub", text: "Uses DeepSeek V4.1 Flash through your OpenCode Go connector only. Nothing is sent to OpenRouter." }),
    h("label", { text: "Test story" }), h("select", { id: "sc", onchange: async e => { try { await loadScen(e.target.value); drawSetup() } catch (x) { alertBox("Couldn’t load that story.") } } }, SCENS.map(([f, n]) => h("option", { value: f, text: n, selected: f === curSc }))),
    h("label", { text: "Turns to play" }), h("input", { type: "number", min: "5", max: String(scen.turns.length), value: opt.turns, oninput: e => opt.turns = e.target.value }),
    h("label", { text: "Reply length (words)" }), h("select", { onchange: e => opt.len = e.target.value }, ["150", "250", "300"].map(v => h("option", { value: v, text: v, selected: v === opt.len }))),
    h("label", { text: "Stop if this trial’s estimated share of your 5-hour Go limit reaches (%)" }), h("input", { type: "number", min: "1", max: "50", value: opt.cap, oninput: e => opt.cap = e.target.value }),
    h("label", { class: "chk" }, h("input", { id: "rp", type: "checkbox", autocomplete: "off" }), "Repair missing metadata (trial setting, one extra request per missed reply)"),
    h("label", { class: "chk" }, h("input", { id: "p2", type: "checkbox", autocomplete: "off" }), "Memory Phase 2: the narrator uses story memory (who knows what)"),
    h("label", { class: "chk" }, h("input", { id: "dry", type: "checkbox", autocomplete: "off", checked: opt.dry, onchange: e => { opt.dry = e.target.checked; conf.hidden = opt.dry } }), "Dry run (no requests, free, checks the page works)"),
  );
  const conf = h("div", { hidden: opt.dry }, h("label", { text: "Type opencode to confirm real requests (uses your Go allowance, about 0.5–1% of the 5-hour window)" }), h("input", { id: "confirm", autocapitalize: "off", autocomplete: "off", spellcheck: "false" }));
  box.append(conf, h("p", { class: "sub", text: "Keep this page open and the screen on for about 15–25 minutes. If it gets interrupted, come back and tap Continue." }));
  const start = h("button", { class: "primary", text: "Start trial", onclick: async () => {
    opt.dry = $("#dry").checked;
    if (!opt.dry) { if (!have) { alertBox("Set up OpenCode in the app first."); return } if ($("#confirm").value.trim().toLowerCase() !== "opencode") { alertBox("Type opencode to confirm."); return } }
    window.__trialReport = null; localStorage.removeItem(PROG); start.disabled = true;
    await resetTrial(); prog = { v: 1, k: -1, rows: [], ops: {}, hosts: {}, opts: { turns: Math.max(5, Math.min(scen.turns.length, +opt.turns || 40)), len: opt.len, cap: Math.max(1, +opt.cap || 10), dry: opt.dry, rp: $("#rp").checked, p2: !!($("#p2") && $("#p2").checked), sc: curSc }, started: new Date().toISOString() }; saveProg(); run(true) } });
  box.append(start);
  if (prog && !prog.done) box.append(h("button", { text: "Continue the unfinished trial (turn " + (Math.max(0, prog.k) + 1) + ")", onclick: () => run(false) }));
  if (prog && prog.done && !opt.dry) box.append(h("button", { text: "Replay repair on missed replies (paid, needs the opencode box)", onclick: () => { if ($("#confirm").value.trim().toLowerCase() !== "opencode") { alertBox("Type opencode to confirm."); return } replay() } }));
  if (prog) box.append(h("button", { text: "Delete trial data", onclick: async () => { await resetTrial(); localStorage.removeItem(PROG); prog = null; drawSetup(); $("#reportbox").hidden = true } }));
  if (prog && prog.done) showReport();
}
function alertBox(t) { const p = h("p", { class: "bad", text: t }); $("#setup").append(p); setTimeout(() => p.remove(), 4000) }
async function resetTrial() {
  const f = $("#app"); if (W) { f.removeAttribute("srcdoc"); await new Promise(r => { f.onload = r; f.src = "about:blank"; setTimeout(r, 1500) }); W = null }
  localStorage.removeItem(TKEY);
  await new Promise(r => { try { const q = indexedDB.deleteDatabase(TIDB); q.onsuccess = q.onerror = q.onblocked = () => r() } catch (e) { r() } });
}

/* ---------- isolated copy of the app ---------- */
async function loadApp(seed) {
  let html = await (await fetch("index.html", { cache: "no-store" })).text();
  for (const [a, b] of [['const KEY="story-forge-v2"', 'const KEY="' + TKEY + '"'], ['indexedDB.open("story-forge",1)', 'indexedDB.open("' + TIDB + '",1)'], ['if("serviceWorker"in navigator)', 'if(false)']]) {
    if (html.split(a).length !== 2) throw new Error("This trial page doesn’t match this version of the app. Upload both from the same build.");
    html = html.replace(a, b);
  }
  html = html.replace("<head>", '<head><base href="' + location.href.replace(/[#?].*$/, "").replace(/[^/]*$/, "") + '">');
  if (seed) localStorage.setItem(TKEY, JSON.stringify(seed));
  const f = $("#app"); await new Promise(r => { f.onload = r; f.srcdoc = html });
  W = f.contentWindow; E = c => W.eval(c);
  for (let i = 0; i < 60; i++) { try { if (E("typeof DB!=='undefined'&&DB&&typeof send==='function'&&DB.sessions.some(s=>s.id==='trial')")) break } catch (e) {} await sleep(250) }
  await sleep(600);
  const realFetch = W.fetch.bind(W);
  W.fetch = (url, o) => {
    try { const u = new URL(String(url), location.href); if (u.origin !== location.origin) { const k = u.hostname.endsWith("openrouter.ai") ? "openrouter.ai" : (u.hostname === "dry-run.invalid" || OC.proxy.includes(u.hostname)) ? "connector" : u.hostname; prog.hosts[k] = (prog.hosts[k] || 0) + 1 } } catch (e) {}
    if (String(url).includes("dry-run.invalid")) return dryFetch(o);
    return realFetch(url, o);
  };
}
function seedDB() {
  const st = scen.story, o = prog.opts;
  return { migrated: true, memv2: false, metaRepair: !!o.rp, ocLite: o.rp ? "effort" : null, prov: "opencode", ocKey: o.dry ? "dry-run" : OC.key, ocProxy: o.dry ? "dry-run.invalid" : OC.proxy, ocMon: OC.mon, ocDay: OC.day, ocScale: OC.scale,
    modes: [{ n: "Trial", id: "deepseek/deepseek-v4.1-flash", d: "", p: "", t: 0.8 }], mode: 0, saver: 0, sugg: true, syncAuto: false,
    stories: [{ id: "trial-story", kind: "story", title: scen.title, setting: st.setting, style: st.style, lore: st.lore, entries: st.entries, stats: [], endings: [], starts: [], follow: "strict" }],
    sessions: [{ id: "trial", storyId: "trial-story", memv2: true, memDev: true, memPrompt: !!o.p2, start: "", follow: "strict", char: { name: scen.player.name, desc: scen.player.desc, trait: "" }, turns: [], temp: "", mems: [], note: "", stats: {}, upto: 0, len: o.len, sugg: [], ending: null, ended: [], people: {}, think: 0, wstyle: "default", wcustom: "", goal: "", updated: Date.now() }] };
}

/* ---------- dry-run stand-in model ---------- */
const SIM = { k: -1, v: 0, last: null };
function kindOf(kws, a) { const t = (kws.join(" ") + " " + a).toLowerCase(); for (const [k, w] of [["death", "die"], ["promise", "promise"], ["betrayal", "betray"], ["threat", "warn"], ["reveal", "confess"], ["secret", "secret"], ["item", "copy"], ["travel", "ride"]]) if (t.includes(w)) return k; return "action" }
function simReply() {
  const k = SIM.k, v = SIM.v, T = k >= 0 ? scen.turns[k] : { a: "The story opens.", loc: scen.turns[0].loc, present: scen.turns[0].present };
  const P = scen.player.name.split(" ")[0], C0 = scen.story.entries[0].k.split(",")[0].split(" ")[0];
  const loc = (T.loc || SIM.last || scen.turns[0].loc)[0]; SIM.last = [loc]; const pres = T.present || [C0];
  let ev = "none"; if (T.event || k % 3 === 0) { const kws = T.event || ["moment"]; ev = [T.event ? 4 : 2, kindOf(kws, T.a), [P].concat(pres.slice(0, 1)).join(", "), loc, P + " " + T.a.slice(2).replace(/\.$/, "").toLowerCase() + " (" + kws[0] + (v ? " v" + v : "") + ")", pres.slice(1).join(", ") || "none"].join(" | ") }
  const learned = (T.learn || []).map(l => l.who + ": the " + l.kw + " — " + T.a.replace(/^I /, P + " ").replace(/\.$/, "") + " (shown directly)").join("; ") || "none";
  return "Turn " + k + " reply" + (v ? " v" + v : "") + ". " + T.a + " The scene moves on.\n\n[[META]]\nCAST: none\nEVENTS: " + ev + "\nLEARNED: " + learned + "\nSCENE: " + loc + " | " + pres.join(", ") + " | " + (k % 2 ? "night" : "day") + " " + (k + 2) + "\nNEXT: I wait. | I look around. | I speak up.";
}
async function dryFetch(o) {
  await sleep(150); const b = JSON.parse(o.body);
  if (!b.stream) return new W.Response(JSON.stringify({ choices: [{ message: { content: "- noted" }, finish_reason: "stop" }], usage: { prompt_tokens: 50, completion_tokens: 5 } }), { status: 200, headers: { "content-type": "application/json" } });
  const sse = "data: " + JSON.stringify({ choices: [{ delta: { content: simReply() } }] }) + "\n\ndata: " + JSON.stringify({ choices: [{ delta: {}, finish_reason: "stop" }], usage: { prompt_tokens: 5000, completion_tokens: 400 } }) + "\n\ndata: [DONE]\n\n";
  return new W.Response(sse, { status: 200, headers: { "content-type": "text/event-stream" } });
}

/* ---------- helpers ---------- */
const SE = 'DB.sessions.find(s=>s.id==="trial")';
const S = () => JSON.parse(E("JSON.stringify(" + SE + ")"));
const low = x => String(x || "").toLowerCase(), first = n => low(n).split(/\s+/)[0] || "";
const hasKw = (t, kws) => kws.some(k => low(t).includes(low(k)));
const NEG = /\b(doesn['’]t know|does not know|did not know|didn['’]t know|not aware|unaware|no idea|has not learned|hasn['’]t learned)\b/i;
/* Narrator-text secrets check (heuristic): a character who doesn't yet know a secret should not say it or react to it.
   Window: from the first turn the scenario lists them in mustNotKnow until the turn they are scripted to learn it. */
function SECRETS() {
  const out = [];
  scen.turns.forEach((T, i) => (T.mustNotKnow || []).forEach(L => { const o = out.find(x => x.who === L.who && x.kw === L.kw); if (!o) out.push({ who: L.who, kw: L.kw, from: i, until: scen.turns.length }) }));
  out.forEach(o => { const j = scen.turns.findIndex((T, i) => i > o.from && (T.learn || []).some(L => first(L.who) === first(o.who))); if (j >= 0) o.until = j });
  return out;
}
function proseLeak(text, who, kw) {
  const f = first(who), k = String(kw).toLowerCase(), paras = String(text || "").split(/\n+/);
  for (const p of paras) {
    const pl = p.toLowerCase();
    if (pl.startsWith(f + " |") && pl.includes(k)) return p.trim().slice(0, 200);
    for (const sen of p.split(/(?<=[.!?"”])\s+/)) { const sl = sen.toLowerCase(); if (sl.includes(k) && new RegExp("\\b" + f + "\\b").test(sl) && !/\b(doesn'?t|does not|didn'?t|did not|never) (know|learn|hear|realize|suspect)/.test(sl)) return sen.trim().slice(0, 200) }
  }
  return "";
}
function knowsAlt(mem, who, L) { const ch = Object.entries(mem.chars || {}).find(([n]) => first(n) === first(who)); if (!ch) return false; const pool = {}; (mem.facts || []).concat(mem.secrets || []).forEach(f => pool[f.id] = f.text); return (ch[1].knows || []).some(i => { const t = low(pool[i]); return !NEG.test(t) && [L.kw].concat(L.alt || []).some(k => t.includes(low(k))) }) }
function knows(mem, who, kw) { const ch = Object.entries(mem.chars || {}).find(([n]) => first(n) === first(who)); if (!ch) return false; const pool = {}; (mem.facts || []).concat(mem.secrets || []).forEach(f => pool[f.id] = f.text); return (ch[1].knows || []).some(i => low(pool[i]).includes(low(kw))) }
function overlap(a, b) { const t = x => new Set(low(x).replace(/[^a-z0-9 ]/g, " ").split(/\s+/).filter(w => w.length > 2)); const A = t(a), B = t(b); if (!A.size || !B.size) return 0; let n = 0; A.forEach(w => { if (B.has(w)) n++ }); return n / Math.min(A.size, B.size) }
const goPct = () => { const g = E("ocPct()"); return { h: +(+g.h).toFixed(2), w: +(+g.w).toFixed(2), m: +(+g.m).toFixed(2) } };
async function waitDone(nMin, ms) {
  let waited = 0; while (waited < (ms || 240000)) { await sleep(500); if (document.hidden) continue; waited += 500;
    try { const r = E("[busy," + SE + ".turns.length]"); if (!r[0] && r[1] >= nMin) { await sleep(300); return true } } catch (e) {} }
  return false;
}
const lastAi = s => { let m = -1; s.turns.forEach((t, i) => { if (t.role === "ai") m = i }); return m };
const click = sel => { const b = W.document.querySelector(sel); if (b) b.click(); return !!b };
async function keepAwake() { try { if ("wakeLock" in navigator) wake = await navigator.wakeLock.request("screen") } catch (e) {} }
document.addEventListener("visibilitychange", () => { if (!document.hidden && W && prog && !prog.done) keepAwake() });

/* ---------- the trial ---------- */
async function run(fresh) {
  stop = false; window.__trialReport = null; $("#runbox").hidden = false; $("#reportbox").hidden = true; $("#setup").hidden = true; $("#log").textContent = ""; keepAwake();
  try {
    status("Loading a separate test copy of the app…"); await loadApp(fresh ? seedDB() : null);
    E('go({n:"chat",id:"trial"})'); await sleep(400);
    if (prog.k < 0) { SIM.k = -1; SIM.v = 0; status("Opening the story…"); await W.begin(E(SE), E('getStory("trial-story")')); if (!await waitDone(2)) throw new Error("The opening reply didn’t arrive. Check your connector in the app’s Settings."); prog.k = 0; saveProg(); log("opening: ok") }
    const N = prog.opts.turns;
    for (let k = prog.k; k < N; k++) {
      if (!prog.opts.dry && goPct().h >= prog.opts.cap) { prog.stopped = "estimated 5-hour Go use reached " + prog.opts.cap + "% before turn " + (k + 1); log(prog.stopped); break }
      const T = scen.turns[k]; SIM.k = k; SIM.v = 0; status("Turn " + (k + 1) + " of " + N + "…");
      const nb = S().turns.length; E('go({n:"chat",id:"trial"})');
      try { await W.send(T.a) } catch (e) {}
      if (!await waitDone(nb + 2)) { prog.fail = (prog.fail || 0) + 1; prog.rows.push({ turn: k + 1, action: T.a, failed: true, checks: {} }); prog.k = k + 1; saveProg(); log("turn " + (k + 1) + ": no reply (counted as a failure)"); continue }
      for (let w = 0; w < 200 && E("RPQ.size") > 0; w++) await sleep(500);
      const s = S(), ai = lastAi(s), mem = s.mem || {}, diag = (s.memDiag || []).slice(-1)[0] || {}, scene = mem.scene || {};
      const evs = (mem.events || []).filter(e => e.src === "meta" && e.t === ai);
      const row = { turn: k + 1, action: T.a, diag: { block: diag.block, keys: diag.keys, ev: diag.ev, ln: diag.ln, sc: diag.sc, multi: diag.multi, issues: diag.issues, err: diag.err, hm: diag.hm, rp: diag.rp }, meta: redact(diag.meta || "").slice(0, 900), scene, events: evs.map(e => e.text), kinds: evs.map(e => e.kind), checks: {} };
      if (!s.turns[ai].text.trim()) prog.fail = (prog.fail || 0) + 1;
      if (T.loc) row.checks.scene_location = hasKw(scene.where || "", T.loc);
      if (T.present) row.checks.scene_present = T.present.every(x => (scene.who || []).some(w => first(w) === first(x)));
      if (T.event) row.checks.event_recorded = evs.some(e => hasKw(e.text + " " + e.kind, T.event));
      (T.learn || []).forEach(L => { row.checks["learned:" + L.who] = knows(mem, L.who, L.kw); row.checks["paraphrase:" + L.who] = knowsAlt(mem, L.who, L) });
      (T.mustNotKnow || []).forEach(L => row.checks["no_leak:" + L.who] = !knows(mem, L.who, L.kw));
      SECRETS().forEach(L => { if (k < L.from || k >= L.until) return; const hit = proseLeak(s.turns[ai].text, L.who, L.kw); row.checks["prose_ok:" + L.who] = !hit; if (hit) (row.proseLeaks = row.proseLeaks || []).push(L.who + ": " + hit) });
      if (T.op === "regen") {
        const pick = m => JSON.stringify(["events", "facts", "chars", "scene"].map(x => m[x]));
        const base = pick(mem);
        for (const v of [1, 2]) { SIM.v = v; await W.regen(); await waitDone(nb + 2) }
        for (let i = 0; i < 2; i++) { click("button[aria-label='Previous version']"); await sleep(400) }
        const s2 = S(); prog.ops.regen_then_back_to_v1_restores_memory = pick(s2.mem || {}) === base; prog.ops.regen_versions = (s2.turns[lastAi(s2)].vs || []).length;
        log("regenerate ×2 then back to version 1: " + (prog.ops.regen_then_back_to_v1_restores_memory ? "memory restored" : "MISMATCH"));
      }
      if (T.op === "branch") {
        const s1 = S(), ais = s1.turns.map((t, i) => t.role === "ai" ? i : -1).filter(i => i >= 0), cut = ais[ais.length - 3], orig = JSON.stringify(s1.mem);
        W.branchAt(E(SE), cut); await sleep(500);
        const b = JSON.parse(E("JSON.stringify(DB.sessions[DB.sessions.length-1])"));
        const keep = (s1.mem.events || []).filter(e => e.src !== "meta" || e.t <= cut).map(e => e.id).sort().join(), got = (b.mem.events || []).map(e => e.id).sort().join();
        prog.ops.branch_keeps_only_earlier_memory = keep === got; prog.ops.branch_original_untouched = JSON.stringify(S().mem) === orig;
        E('go({n:"chat",id:"trial"})'); await sleep(400); log("branch: " + (prog.ops.branch_keeps_only_earlier_memory && prog.ops.branch_original_untouched ? "ok" : "MISMATCH"));
      }
      if (T.op === "cancel") {
        const core = s => JSON.stringify(["turns", "mem", "stats", "facts"].map(x => s[x])), b0 = core(S()), calls = JSON.stringify(prog.hosts);
        E("(()=>{window.__k=DB.ocKey;DB.ocKey='';save()})()"); await W.regen(); await sleep(800); E("(()=>{DB.ocKey=window.__k;delete window.__k;save()})()");
        prog.ops.cancel_keeps_reply_and_memory = core(S()) === b0 && JSON.stringify(prog.hosts) === calls; log("cancel before sending: " + (prog.ops.cancel_keeps_reply_and_memory ? "reply and memory kept" : "CHANGED"));
      }
      if (!prog.opts.dry) row.go = goPct();
      prog.rows.push(row); prog.k = k + 1; saveProg();
      log("turn " + (k + 1) + ": " + Object.entries(row.checks).map(([c, v]) => c + "=" + (v ? "ok" : "MISS")).join(" ") + ((row.diag.issues || []).length ? "  issues: " + row.diag.issues.join("; ") : ""));
    }
    const s = S(), mem = s.mem || {}, evs = (mem.events || []).filter(e => e.src === "meta"), dups = [];
    for (let i = 0; i < evs.length; i++) for (let j = i + 1; j < evs.length; j++) if (Math.abs(evs[i].t - evs[j].t) <= 6 && overlap(evs[i].text, evs[j].text) >= 0.6) dups.push([evs[i].text.slice(0, 80), evs[j].text.slice(0, 80)]);
    prog.dups = dups; prog.integrity = E("SFMemory.integrity(" + SE + ".mem)"); prog.globalOff = E("DB.memv2") === false; if (!prog.opts.dry) prog.go = goPct();
    prog.realUnchanged = localStorage.getItem(REAL) === realBefore; prog.done = true; prog.finished = new Date().toISOString(); saveProg();
    status("Finished."); drawSetup();
  } catch (e) { status("Stopped: " + (e && e.message || e) + " Tap Continue to resume."); log("stopped: " + (e && e.message || e)); $("#setup").hidden = false; drawSetup() }
  try { if (wake) await wake.release() } catch (e) {}
  unloadApp();
}
/* Free the test copy of the app once a run or replay ends, so a finished trial page holds almost no memory. */
function unloadApp() { const f = $("#app"); if (!f || !W) return; try { f.removeAttribute("srcdoc"); f.src = "about:blank" } catch (e) {} W = null; E = null }

async function replay() {
  $("#runbox").hidden = false; $("#setup").hidden = true; status("Loading the finished test story…");
  try { await loadApp(null); const out = await W.metaRepairReplay(E(SE)); prog.replay = { at: new Date().toISOString(), n: out.length, ok: out.filter(x => x.ok).length, items: out.map(x => ({ t: x.t, ok: x.ok, why: x.why, ms: x.ms, tok: x.tok, block: redact(x.block || "").slice(0, 900) })) }; saveProg();
    status("Replay finished: " + prog.replay.ok + " of " + prog.replay.n + " missed replies repaired."); log(JSON.stringify(prog.replay.items.map(x => [x.t, x.ok, x.why || "", x.ms]))) }
  catch (e) { status("Replay stopped: " + (e && e.message || e)) }
  unloadApp(); $("#setup").hidden = false; drawSetup() }

/* ---------- report ---------- */
function summarize() {
  const R = prog.rows.filter(r => !r.failed), rate = f => { const xs = R.map(f).filter(x => x != null); return [xs.filter(Boolean).length, xs.length] };
  const chk = p => { const xs = R.flatMap(r => Object.entries(r.checks).filter(([c]) => c.startsWith(p)).map(([, v]) => v)); return [xs.filter(Boolean).length, xs.length] };
  const sum = (k, f) => R.reduce((a, r) => a + (((r.diag || {})[k] || {})[f] || 0), 0);
  return [["META block present", rate(r => r.diag.block)], ["EVENTS key present", rate(r => (r.diag.keys || {}).EVENTS)], ["LEARNED key present", rate(r => (r.diag.keys || {}).LEARNED)], ["SCENE key present", rate(r => (r.diag.keys || {}).SCENE)],
    ["SCENE well-formed", rate(r => r.diag.sc)], ["EVENT entries well-formed", [sum("ev", "valid"), sum("ev", "total")]], ["LEARNED entries well-formed", [sum("ln", "valid"), sum("ln", "total")]],
    ["Lists split over several lines (recovered)", rate(r => r.diag.multi)], ["Missing blocks repaired (extra request)", [R.filter(r => r.diag.rp && r.diag.rp.ok).length, R.filter(r => r.diag.rp).length]], ["Scene location correct", chk("scene_location")], ["Expected characters present", chk("scene_present")],
    ["Expected event recorded", chk("event_recorded")], ["Expected knowledge recorded (exact keyword)", chk("learned:")], ["Expected knowledge recorded (accepted paraphrases)", chk("paraphrase:")], ["No knowledge leaks", chk("no_leak:")], ["Narrator kept secrets (text check)", chk("prose_ok:")]];
}
function reportMd() {
  const live = !prog.opts.dry, S2 = summarize(), pct = ([a, b]) => b ? `${a}/${b} (${Math.round(100 * a / b)}%)` : "—";
  const L = ["# Memory trial — " + (live ? "LIVE" : "DRY RUN"), "", "Test story: " + scen.title, "",
    live ? "**LIVE RUN — real calls through OpenCode Go** (DeepSeek V4.1 Flash via your connector), run on a phone. Estimated Go limit used by this trial: " + JSON.stringify(prog.go) + "."
         : "**DRY RUN — no requests were sent.** Replies came from a built-in stand-in. This only checks that the trial page works.",
    "", "Started " + prog.started + " · finished " + prog.finished + " · turns played: " + prog.rows.length + " of " + prog.opts.turns + (prog.stopped ? " · stopped early: " + prog.stopped : ""),
    "Requests by destination: " + JSON.stringify(prog.hosts) + (prog.hosts["openrouter.ai"] ? "" : " — no OpenRouter requests"),
    "Your real stories unchanged: " + (prog.realUnchanged ? "yes (verified)" : "NO — check your app") + " · memory stayed off globally: " + (prog.globalOff ? "yes" : "NO"), "",
    "| Check | Result |", "|---|---|", ...S2.map(([k, v]) => `| ${k} | ${pct(v)} |`), "", "| Operation | Result |", "|---|---|", ...Object.entries(prog.ops).map(([k, v]) => `| ${k} | ${v} |`), "",
    `Possible duplicate events (same 6 turns, ≥60% word overlap): **${(prog.dups || []).length}** · replies that failed: **${prog.fail || 0}** · parser exceptions: **${prog.rows.filter(r => r.diag && r.diag.err).length}** · memory integrity: **${prog.integrity && prog.integrity.ok}**`, ""];
  const pl = prog.rows.flatMap(r => (r.proseLeaks || []).map(x => `- turn ${r.turn}: ${x}`)); L.push("Memory Phase 2: " + (prog.opts.p2 ? "**ON**" : "off"), ""); if (pl.length) L.push("## Possible secret leaks in the narrator's text (heuristic; check by hand)", "", ...pl, "");
  const iss = prog.rows.flatMap(r => ((r.diag || {}).issues || []).map(i => `- turn ${r.turn}: ${i}`)); if (iss.length) L.push("## Malformed or missing metadata (first 20)", "", ...iss.slice(0, 20), "");
  const miss = prog.rows.flatMap(r => Object.entries(r.checks || {}).filter(([, v]) => !v).map(([c]) => `- turn ${r.turn}: ${c}`)); if (miss.length) L.push("## Missed expectations (first 25)", "", ...miss.slice(0, 25), "");
  const samples = prog.rows.filter(r => r.meta).slice(0, 3).map(r => "Turn " + r.turn + ":\n```\n" + r.meta + "\n```"); if (samples.length) L.push("## Sample META (first 3 turns)", "", ...samples, "");
  return redact(L.join("\n"));
}
function showReport() {
  const md = reportMd(), box = $("#report"); box.textContent = ""; $("#reportbox").hidden = false; $("#setup").hidden = false;
  const t = h("table"); summarize().forEach(([k, [a, b]]) => t.append(h("tr", null, h("td", { text: k }), h("td", { class: !b || /split/.test(k) ? "sub" : a === b ? "ok" : "bad", text: b ? a + "/" + b : "—" }))));
  box.append(h("p", { class: prog.opts.dry ? "sub" : "", text: prog.opts.dry ? "Dry run: no requests were sent." : "Live run through OpenCode Go." }), h("p", { class: prog.realUnchanged ? "ok" : "bad", text: prog.realUnchanged ? "✓ Your real stories were not changed." : "✗ Your real data changed during the trial. Please tell me." }), t);
  const json = redact(JSON.stringify(prog, null, 1)), name = "memory-trial-" + (prog.opts.dry ? "dry-run" : "opencode-deepseek") + "-" + (prog.finished || "").slice(0, 16).replace(/[:T]/g, "-");
  $("#share").onclick = async () => { try { const files = [new File([md], name + ".md", { type: "text/markdown" }), new File([json], name + ".json", { type: "application/json" })]; if (navigator.canShare && navigator.canShare({ files })) { await navigator.share({ files, title: "Memory trial report" }); return } } catch (e) { if (e && e.name === "AbortError") return } $("#dl").click() };
  $("#copy").onclick = async () => { try { await navigator.clipboard.writeText(md); $("#copy").textContent = "Copied" } catch (e) {} };
  $("#dl").onclick = () => { for (const [txt, ext, ty] of [[md, ".md", "text/markdown"], [json, ".json", "application/json"]]) { const a = h("a", { href: URL.createObjectURL(new Blob([txt], { type: ty })), download: name + ext }); document.body.append(a); a.click(); a.remove() } };
  window.__trialReport = md;
}
drawSetup();
})();
