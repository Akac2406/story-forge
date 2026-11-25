"""Final stabilization: one 300-turn fanfiction playthrough with every feature on (memory v2 + recall + hybrid step, director, gameplay career,
cinematic, appearance, canon). Measures load time, prompt size, storage size, a send round trip and every screen on a phone viewport. No network.
Run: python tests/stress_all_on_browser.py"""
import json, os, subprocess, sys, time, copy
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8902
FX = json.load(open(os.path.join(HERE, "fixtures", "fanfic-ember.json")))
fails = []; errs = []; LAST = {"sys": "", "n": 0, "chars": 0}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"):
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "[[META]]\nEVENTS: 2 | action | Kael Ashveil | courtyard | Kael trains | none\nLEARNED: none\nSCENE: courtyard | Kael Ashveil, Mira Vale | dusk"}, "finish_reason": "stop"}]}))
    LAST["sys"] = b["messages"][0]["content"]; LAST["n"] = len(b["messages"]); LAST["chars"] = sum(len(m["content"]) if isinstance(m["content"], str) else 0 for m in b["messages"])
    txt = 'Kael Ashveil drew his blade in the courtyard. "Again," Mira Vale said.\n\n[[META]]\nEVENTS: 2 | action | Kael Ashveil | courtyard | Kael spars with Mira | Mira Vale\nLEARNED: none\nSCENE: courtyard | Kael Ashveil, Mira Vale | dusk\nENDING: none'
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: [DONE]\n\n")
turns = [{"role": "user", "text": "Begin", "hide": True}]
for i in range(300):
    turns.append({"role": "user", "text": f"I train with Mira, day {i}."})
    turns.append({"role": "ai", "text": f"Kael Ashveil and Mira Vale spar in the courtyard on day {i}. " * 6,
                  "mt": f"[[META]]\nEVENTS: 2 | action | Kael Ashveil | courtyard | Kael and Mira spar on day {i} | Mira Vale\nLEARNED: none\nSCENE: courtyard | Kael Ashveil, Mira Vale | day {i}"})
se = copy.deepcopy(FX["session"]); se.update({"storyId": "ff", "char": {"name": "Kael Ashveil"}, "turns": turns, "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 2,
    "memv2": True, "memRecall": True, "memExtract": "hybrid", "memPrompt": True, "cast": {"Mira Vale": {"u": 5}}})
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "universes": {"ember": FX["universe"]},
        "stories": [{"id": "ff", "kind": "story", "title": "Ember", "setting": "The Ember Academy.", "starts": [], "stats": [], "endings": [], "entries": []}], "sessions": [se]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True); pg.set_default_timeout(30000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept()); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED))
    # switch everything on through the adapters, then reload and time it
    pg.reload(); pg.wait_for_selector(".cta")
    pg.evaluate(f"dirEnable({S},true);gmStartCareer({S},'idol');gmEnable({S},true);gmAddQuest({S},{{id:'q1',title:'Win the spar',steps:['Train','Fight']}});cvApplyPreset({S},'classic-vn');apSet({S},{{theme:'Oceanic',icons:'pixel'}},'story')")
    t0 = time.time(); pg.reload(); pg.wait_for_selector(".cta"); load = time.time() - t0
    ok(load < 5, f"app loads in {load:.2f}s with a 300-turn, all-features story")
    size = pg.evaluate("(localStorage.getItem('story-forge-v2')||'').length"); ok(size < 4_500_000, f"saved data {size/1e6:.2f} MB (browser limit ~5 MB)")
    t0 = time.time(); pg.evaluate("go({n:'chat',id:DB.sessions[0].id})"); pg.wait_for_selector("#log"); open_t = time.time() - t0
    ok(open_t < 4, f"opening the story takes {open_t:.2f}s")
    t0 = time.time(); n = pg.evaluate(f"{S}.turns.length"); pg.fill("#input", "I spar with Mira again."); pg.click("button[aria-label='Send']")
    pg.wait_for_function(f"!busy&&{S}.turns.length==={n+2}", timeout=30000); send_t = time.time() - t0
    ok(send_t < 6, f"send round trip (prompt build + reply + memory) {send_t:.2f}s")
    for sec in ["GAMEPLAY STATE", "STORY DIRECTOR"]: ok(sec in LAST["sys"], f"prompt has {sec}")
    ok(LAST["chars"] < 200_000, f"prompt size {LAST['chars']:,} characters in {LAST['n']} messages (stays under the caps)")
    ok(pg.evaluate(f"{S}.turns[{S}.turns.length-1].text").startswith("Kael Ashveil drew"), "reply saved")
    screens = ["inspector", "continuity", "timeline", "romance", "web", "journal", "agenda", "memory", "director", "universe", "gameplay", "creator", "cinema", "appearance"]
    slow = []
    for k in screens:
        if not pg.evaluate(f"typeof window.SFFanUI.{k}==='function'"): continue
        n0 = len(errs); t0 = time.time(); pg.evaluate(f"window.SFFanUI.{k}({S})"); pg.wait_for_timeout(150); dt = time.time() - t0
        if len(errs) != n0: ok(False, f"{k} screen error: {errs[-1][:120]}")
        if dt > 2: slow.append(f"{k} {dt:.1f}s")
        wide = pg.evaluate("Math.max(...[...document.querySelectorAll('.sheet, [role=dialog]')].map(e=>e.scrollWidth-e.clientWidth),0)")
        if wide > 8: ok(False, f"{k} overflows the phone width by {wide}px")
    ok(not slow, "every screen opens in under 2 s on a 300-turn story " + ", ".join(slow))
    t0 = time.time(); r = pg.evaluate(f"memQuery({S},{{text:'Mira',limit:50}}).length"); q = time.time() - t0
    ok(r > 0 and q < 1.5, f"memory search over the long story {q:.2f}s ({r} hits)")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
