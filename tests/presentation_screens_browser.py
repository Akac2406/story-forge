"""ChatGPT's Cinematic / Visual Novel and Appearance Studio screens: menu entries, open without errors, controls go through cv*/ap*, v48 stays in sync, story untouched. No network.
Run: python tests/presentation_screens_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8901
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
SEED = {"key": "sk-or-test", "ocKey": "dummy-oc-key-123456", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "cast": {"Rae": {"pic": PNG}}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"
def selects(pg): return pg.evaluate("[...document.querySelectorAll('select')].map((s,i)=>({i,opts:[...s.options].map(o=>o.value).slice(0,40),v:s.value}))")
def set_select(pg, want):
    for s in selects(pg):
        if want in s["opts"] and s["v"] != want:
            pg.evaluate("([i,v])=>{const s=document.querySelectorAll('select')[i];s.value=v;s.dispatchEvent(new Event('change',{bubbles:true}));s.dispatchEvent(new Event('input',{bubbles:true}))}", [s["i"], want]); pg.wait_for_timeout(250); return True
    return False
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 900}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept())
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    before = pg.evaluate(f"JSON.stringify([{S}.turns,{S}.cast])")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log"); pg.evaluate(f"menuSheet({S},DB.stories[0])"); pg.wait_for_timeout(300)
    m = pg.evaluate("[...document.querySelectorAll('details.story-tools')].map(d=>d.textContent).join('|')")
    ok("Cinematic / Visual Novel" in m and "Appearance Studio" in m, "menu lists both screens")
    for k, t in [("cinema", "Cinematic"), ("appearance", "Appearance")]:
        n0 = len(errs); pg.evaluate(f"window.SFFanUI.{k}({S})"); pg.wait_for_timeout(300)
        ok(len(errs) == n0 and t in pg.evaluate("document.body.innerText"), f"{t} screen opens without errors")
    pg.evaluate(f"window.SFFanUI.cinema({S})"); pg.wait_for_timeout(300)
    ok(set_select(pg, "visual-novel") and pg.evaluate(f"cvState({S}).settings.layout") == "visual-novel", "Cinematic layout control goes through cvSet")
    n0 = len(errs); pg.evaluate(f"window.SFFanUI.cinema({S})"); pg.wait_for_timeout(300); ok(len(errs) == n0, "Cinematic reopens with saved settings")
    ok(pg.evaluate(f"JSON.stringify([{S}.turns,{S}.cast])") == before, "story text and cast untouched")
    pg.evaluate(f"window.SFFanUI.appearance({S})"); pg.wait_for_timeout(300)
    th = pg.locator("button", has_text="Oceanic"); ok(th.count() >= 1, "Appearance theme buttons listed")
    th.first.click(); pg.wait_for_timeout(300)
    store = pg.evaluate("JSON.parse(localStorage.getItem('sf.visual.v48')||'null')") or {}
    ok((store.get("stories", {}).get("s1") or {}).get("theme") == "Oceanic", "theme saved to this story's scope through apSet")
    ok(pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg').trim().toLowerCase()") == pg.evaluate("SFVisualV48.palette('Oceanic')[0]").lower(), "v48 applied it live")
    pg.locator("button", has_text="Pixel").first.click(); pg.wait_for_timeout(250)
    ok(pg.evaluate(f"apState({S}).icons") == "pixel", "icon family chosen through apSet")
    ok("dummy-oc-key" not in json.dumps(store), "no credentials in appearance storage")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
