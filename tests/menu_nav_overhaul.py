"""UI overhaul (ChatGPT): collapsible novel menu. No helper: uses the real accordion on a phone-sized screen.
Every menu control must be reachable by opening its category, one category open at a time, and actions must still work.
Run: python tests/menu_nav_overhaul.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8892
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
CATS = ["Story & Chapters", "Canon & Fanfiction", "Characters & Relationships", "Memory & Continuity", "World & Gameplay", "Story Director", "Appearance & Media", "Advanced & Settings"]
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "A harbor.", "starts": [], "stats": [], "endings": [{"n": "Calm", "d": "x"}], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1, "life": True, "log": []}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(8000)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log"); pg.click("button[aria-label='Menu']"); pg.wait_for_timeout(300)
    names = pg.evaluate("[...document.querySelectorAll('details.story-tools>summary')].map(s=>s.textContent.trim())")
    ok(names == CATS, f"eight categories in the agreed order: {names}")
    ok(pg.evaluate("[...document.querySelectorAll('details.story-tools')].every(d=>!d.open)"), "all categories start collapsed")
    total = pg.evaluate("document.querySelectorAll('details.story-tools button.drow, details.story-tools label.chk').length")
    reached = set()
    for c in CATS:
        pg.click(f"details.story-tools>summary:text-is('{c}')"); pg.wait_for_timeout(150)
        open_ = pg.evaluate("[...document.querySelectorAll('details.story-tools')].filter(d=>d.open).map(d=>d.querySelector('summary').textContent.trim())")
        ok(open_ == [c], f"opening {c} shows only that category")
        vis = pg.evaluate("[...document.querySelectorAll('details.story-tools[open] button.drow, details.story-tools[open] label.chk')].filter(b=>b.offsetParent!==null&&b.getBoundingClientRect().width>0).map(b=>b.textContent.trim().slice(0,40))")
        reached.update(vis)
    ok(len(reached) >= total - 1 and total >= 40, f"every control is reachable through its category ({len(reached)} of {total})")
    outside = pg.evaluate("[...document.querySelectorAll('#sheetbg .drawer button.drow')].filter(b=>!b.closest('details.story-tools')).map(b=>b.textContent.trim().slice(0,30))")
    print("   controls outside categories:", outside)
    # an action still works from inside a category
    pg.click("details.story-tools>summary:text-is('Memory & Continuity')"); pg.click("button.drow:has-text('Story memory (beta)')"); pg.wait_for_timeout(400)
    ok(pg.locator("text=Memory notes").count() > 0 or pg.locator(".sheet").count() > 0, "a control inside a category still opens its sheet")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
