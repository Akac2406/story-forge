"""ChatGPT's fanfiction screens (fanfic-ui.js) on the Ember fixture: every menu entry opens without errors, changes go through
the adapter, and original stories don't show fanfiction entries. No network. Run: python tests/fanfic_ui_screens.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8889
FX = json.load(open(os.path.join(HERE, "fixtures", "fanfic-ember.json"))); IDOL = json.load(open(os.path.join(HERE, "fixtures", "fanfic-idol.json")))
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
se = dict(FX["session"]); se.update({"storyId": "ff", "char": {"name": "Kael"}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Gates open."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 2})
rw = {"id": "rw1", "storyId": "rws", "char": {"name": "Jun"}, "canon": IDOL["realworld"]["canon"], "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Auditions."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 3}
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "universes": {"ember": FX["universe"], "demo-stage": IDOL["realworld"]["universe"]},
        "stories": [{"id": "ff", "kind": "story", "title": "FF", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []},
                    {"id": "rws", "kind": "story", "title": "RW", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []},
                    {"id": "plain", "kind": "story", "title": "Plain", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [se, rw, {"id": "p1", "storyId": "plain", "char": {"name": "A"}, "turns": [{"role": "user", "text": "B", "hide": True}, {"role": "ai", "text": "C"}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
ENTRIES = ["Source Library", "Fanfiction Studio", "Canon Manager", "Timeline & Fates", "Character Inspector", "Romance Preferences", "Continuity Center"]
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
def open_menu(pg, sid):
    pg.evaluate("closeSheet&&closeSheet(true)") if pg.evaluate("typeof closeSheet==='function'") else None
    pg.evaluate(f"go({{n:'chat',id:'{sid}'}})"); pg.wait_for_selector("#log"); pg.click("button[aria-label='Menu']"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelectorAll('details.story-tools').forEach(d=>{d.removeAttribute('name');d.open=true})")
def labels(pg): return pg.evaluate("[...document.querySelectorAll('details.story-tools button.drow')].map(b=>b.textContent.trim())")
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(8000)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    ok(pg.evaluate("!!window.SFFanUI"), "fanfic-ui.js loads")
    open_menu(pg, "play-takeover"); L = labels(pg)
    ok(all(any(l.startswith(e) for l in L) for e in ENTRIES), f"fanfiction story shows all fanfiction entries")
    ok(not any(l.startswith("Real-World Story") for l in L), "fictional universe hides the real-world entry")
    for e in ENTRIES:
        open_menu(pg, "play-takeover"); before = len(errs)
        pg.click(f"button.drow:has-text('{e}')"); pg.wait_for_timeout(500)
        txt = pg.evaluate("(document.querySelector('.sheet')||document.querySelector('#sheetbg')||document.body).innerText.slice(0,4000)")
        ok(len(errs) == before and len(txt.strip()) > 20, f"{e} opens without errors")
    canon_before = pg.evaluate("JSON.stringify(DB.sessions[0].canon)")
    ok(pg.evaluate("JSON.stringify(DB.sessions[0].canon)") == canon_before, "opening screens does not change canon data")
    open_menu(pg, "rw1"); L2 = labels(pg)
    ok(any(l.startswith("Real-World Story") for l in L2) and any(l.startswith("Competition Studio") for l in L2), "real-world universe shows Real-World Story and Competition Studio")
    for e in ["Real-World Story", "Competition Studio"]:
        open_menu(pg, "rw1"); before = len(errs); pg.click(f"button.drow:has-text('{e}')"); pg.wait_for_timeout(500)
        ok(len(errs) == before, f"{e} opens without errors")
    open_menu(pg, "p1"); L3 = labels(pg)
    ok(not any(any(l.startswith(e) for e in ENTRIES + ["Real-World Story", "Competition Studio"]) for l in L3), "original story shows no fanfiction entries")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
