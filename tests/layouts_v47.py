"""v47: every UI layout, with and without cinematic reading, at phone and desktop size:
no page errors, no sideways scrolling, story text and the main controls stay visible.
Run: python tests/layouts_v47.py"""
import json, os, re, subprocess, sys, time
from playwright.sync_api import sync_playwright
import menu_helper  # opens collapsible novel-menu categories for older tests (UI overhaul)
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8849
html = open(os.path.join(APP, "index.html")).read()
LAYOUTS = sorted(set(re.findall(r'data-ui-layout="([a-z]+)"', html)))
fails = []
def ok(c, m):
    if not c: print("FAIL " + m); fails.append(m)
SEED = {"key": "k", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Night Shift", "setting": "A hangar in winter.",
                     "entries": [{"k": "Dale Ortega, Dale", "t": "Lead mechanic", "a": True}], "stats": [], "endings": [], "starts": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Rae Holloway"}, "memv2": True,
                      "turns": [{"role": "user", "text": "I clock in.", "hide": True}, {"role": "ai", "text": "Dale looks up from the cowling."},
                                {"role": "user", "text": "I ask about N42RL."}, {"role": "ai", "text": "\"Inspection's signed off,\" Dale says, too quickly."}],
                      "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
errs = []; n = 0
with sync_playwright() as p:
    br = p.chromium.launch()
    for name, vp in (("phone", {"width": 390, "height": 844}), ("desktop", {"width": 1280, "height": 860})):
        pg = br.new_page(viewport=vp); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
        for lay in LAYOUTS:
            for cine in (False, True):
                d = dict(SEED, uiLayout=lay, visualNovelMode=cine)
                pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(d))
                pg.reload(); pg.wait_for_selector(".cta")
                tag = f"{name} {lay}{' cinematic' if cine else ''}"
                ok(pg.evaluate("document.body.dataset.uiLayout") == lay, tag + ": layout applied")
                ok(pg.evaluate("document.documentElement.scrollWidth") <= vp["width"], tag + ": home fits width")
                pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
                ok(pg.evaluate("document.documentElement.scrollWidth") <= vp["width"], tag + ": chat fits width")
                ok(pg.locator("text=too quickly").first.is_visible(), tag + ": story text visible")
                for lab in ("Send", "Regenerate", "Menu"):
                    ok(pg.locator(f"button[aria-label='{lab}']").first.is_visible(), f"{tag}: {lab} button visible")
                pg.get_by_role("button", name="Menu", exact=True).click()
                pass  # categories are opened by menu_helper (UI overhaul renamed this group)
                pg.get_by_role("button", name="Visual Suite", exact=True).click()
                pg.locator(".sheet").get_by_text("Visual Suite", exact=True).wait_for()
                n += 1
        pg.close()
    br.close()
srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print(f"checked {n} layout/mode combinations ({len(LAYOUTS)} layouts)")
print("ERRORS:", fails[:20], "..." if len(fails) > 20 else ""); sys.exit(1 if fails else 0)
