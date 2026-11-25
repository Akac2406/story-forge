"""Saved-reply playback stops when leaving the story or hiding the tab; appearance scopes resolve independently. No network.
Run: python tests/playback_lifecycle_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8914
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
turns = [{"role": "user", "text": "Begin", "hide": True}] + sum([[{"role": "user", "text": f"Step {i}."}, {"role": "ai", "text": ("Reply %d. " % i) * 40}] for i in range(10)], [])
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "turns": turns, "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 900, "height": 600}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pg.evaluate(f"cvSet({S},{{layout:'visual-novel',autoAdvance:true,autoDelay:1}});null"); pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log"); pg.wait_for_timeout(200)
    pg.evaluate("document.querySelector('#log').scrollTop=0")
    pg.get_by_role("button", name="Play saved replies").click(); pg.wait_for_timeout(2300)
    ok(pg.evaluate("document.querySelector('#log').scrollTop") > 0, "playback scrolls through saved replies")
    # hide the tab: playback stops at the next step
    pg.evaluate("Object.defineProperty(document,'hidden',{get:()=>true,configurable:true});document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(1300)
    ok(pg.get_by_role("button", name="Play saved replies").get_attribute("aria-pressed") == "false", "hiding the tab stops playback")
    pg.evaluate("Object.defineProperty(document,'hidden',{get:()=>false,configurable:true})")
    pg.get_by_role("button", name="Play saved replies").click(); pg.wait_for_timeout(300)
    pg.evaluate("go({n:'home'})"); pg.wait_for_timeout(1500)
    before = pg.evaluate("window.scrollY"); pg.wait_for_timeout(1300)
    ok(pg.evaluate("window.scrollY") == before and len(errs) == 0, "leaving the story stops playback without errors")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log"); pg.wait_for_timeout(200)
    ok(pg.get_by_role("button", name="Play saved replies").get_attribute("aria-pressed") == "false", "returning shows playback stopped")
    # appearance scopes resolve independently
    pg.evaluate(f"apSet({S},{{theme:'Oceanic'}},'global');apSet({S},{{theme:'Royal Fantasy'}},'story');apSet({S},{{spacing:'compact'}},'mobile');apSet({S},{{spacing:'roomy'}},'desktop');null")
    st = pg.evaluate(f"[apState({S},'mobile'),apState({S},'desktop'),apState(null,'desktop')]")
    ok(st[0]["theme"] == "Royal Fantasy" and st[0]["spacing"] == "compact" and st[1]["spacing"] == "roomy" and st[2]["theme"] == "Oceanic", "global, story, mobile and desktop settings resolve independently")
    pg.evaluate(f"apReset({S},'story');null"); ok(pg.evaluate(f"apState({S},'desktop').theme") == "Oceanic" and pg.evaluate(f"apState({S},'mobile').spacing") == "compact", "resetting the story scope leaves device and global settings")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
