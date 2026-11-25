"""Rendering of appearance and cinematic settings through the existing v48/v49 hooks: computed styles and data attributes change, story text never does. No network.
Run: python tests/presentation_render_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8906
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "cast": {}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog rolled in."}, {"role": "user", "text": "I wait."}, {"role": "ai", "text": "The lamps lit."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"
def ds(pg, k): return pg.evaluate(f"document.documentElement.dataset['{k}']||null")
def chat(pg): pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log"); pg.wait_for_timeout(300)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1000, "height": 800}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("([s,sc])=>{localStorage.clear();localStorage.setItem('story-forge-v2',s);localStorage.setItem('sf-v54-scene-presets',sc)}", [json.dumps(SEED), json.dumps({"e1": {"background": PNG}})]); pg.reload(); pg.wait_for_selector(".cta")
    text0 = pg.evaluate(f"JSON.stringify({S}.turns)")
    # appearance tokens
    pg.evaluate(f"apSet({S},{{spacing:'compact',radius:20,icons:'pixel',borders:'bold',accent:'#ff00aa',fontScale:1.2}},'global')"); pg.wait_for_timeout(150)
    ok(ds(pg, "sfSpacing") == "compact" and ds(pg, "sfIcons") == "pixel" and ds(pg, "sfBorders") == "bold", "appearance settings set data-sf-* attributes")
    ok(pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--sf-radius').trim()") == "20px" and pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent').trim().toLowerCase()") == "#ff00aa", "radius and custom accent reach CSS variables")
    pad = pg.evaluate("(()=>{const p=document.querySelector('.page');return p?getComputedStyle(p).paddingTop:null})()"); ok(pad == "8px", f"compact spacing changes real layout (page padding {pad})")
    pg.evaluate(f"apSet({S},{{contrast:'high',transparency:0.4}},'global')"); pg.wait_for_timeout(100)
    ok(pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--sf-transparency').trim()") == "0", "high contrast removes transparency")
    pg.evaluate(f"apSet({S},{{reducedMotion:true}},'global')"); pg.wait_for_timeout(100)
    ok(ds(pg, "sfReducedMotion") == "true" and ds(pg, "sfMotion") == "off", "reduced motion is exposed to CSS")
    pg.evaluate(f"apReset({S},'global')"); pg.wait_for_timeout(100)
    ok(ds(pg, "sfSpacing") is None and ds(pg, "sfIcons") is None and pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--sf-radius').trim()") == "", "reset removes the tokens")
    # cinematic
    pg.evaluate(f"cvSet({S},{{layout:'chat',narration:'italic'}})"); chat(pg)
    ok(ds(pg, "sfCvLayout") == "chat" and ds(pg, "sfCvNarration") == "italic", "cinematic state reaches the reader (data-sf-cv-*)")
    ml = pg.evaluate("(()=>{const t=document.querySelector('#log .turn.user');return t?getComputedStyle(t).marginLeft:null})()"); ok(ml not in (None, "0px"), f"chat layout moves the player's bubbles (margin-left {ml})")
    fs = pg.evaluate("(()=>{const b=document.querySelector('#log .turn.ai .body');return b?getComputedStyle(b).fontStyle:null})()"); ok(fs == "italic", f"italic narration applied ({fs})")
    pg.evaluate(f"cvSet({S},{{layout:'visual-novel',transition:'fade',textReveal:'typewriter'}})"); chat(pg)
    bg = pg.evaluate("getComputedStyle(document.querySelector('#log')).backgroundImage"); ok("url(" in bg, "visual-novel layout shows the scene artwork by reference")
    pg.evaluate(f"cvSet({S},{{reducedMotion:true}})"); chat(pg)
    ok(ds(pg, "sfCvReduced") == "true" and ds(pg, "sfCvTransition") == "none" and ds(pg, "sfCvReveal") == "fade-in", "cinematic reduced motion removes transitions and typewriter")
    pg.evaluate(f"cvSet({S},{{layout:'novel'}})"); chat(pg)
    ok(pg.evaluate("getComputedStyle(document.querySelector('#log')).backgroundImage") == "none", "classic novel layout shows no background")
    pg.evaluate("go({n:'home'})"); pg.wait_for_timeout(300)
    ok(ds(pg, "sfCvLayout") is None, "leaving the story clears cinematic attributes")
    ok(pg.evaluate(f"JSON.stringify({S}.turns)") == text0, "story text never changes")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
