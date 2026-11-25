"""ChatGPT's Studio > Fanfiction creation wizard: walk all steps as a user, create a takeover story, and check a new playthrough inherits the canon. No network.
Run: python tests/fanfic_wizard_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8905
FX = json.load(open(os.path.join(HERE, "fixtures", "fanfic-ember.json")))
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"): return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": "The gates open.\n\n[[META]]\nENDING: none"}}]}) + "\n\ndata: [DONE]\n\n")
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "universes": {"ember": FX["universe"]}, "stories": [], "sessions": []}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
def status(pg): return pg.evaluate("(document.querySelector('#wz [role=status]')||{}).textContent||''")
def nxt(pg): pg.locator("#wz button", has_text="Next").last.click(); pg.wait_for_timeout(150)
def step(pg): return pg.evaluate("(document.querySelector('#wz h2')||{}).textContent||''")
def pick(pg, label_contains, value):
    return pg.evaluate("([l,v])=>{const f=[...document.querySelectorAll('#wz label.fld')].filter(f=>f.querySelector('span')&&f.querySelector('span').textContent.includes(l)).map(f=>f.querySelector('select')).find(Boolean);if(!f)return false;f.value=v;f.dispatchEvent(new Event('change',{bubbles:true}));return true}", [label_contains, value])
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept()); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pg.evaluate("(()=>{const d=document.createElement('div');d.id='wz';document.body.prepend(d);window.SFFanUI.createFanfiction(d)})()"); pg.wait_for_timeout(200)
    ok(step(pg) == "Universe", "wizard opens on the Universe step")
    nxt(pg); ok("universe first" in status(pg) and step(pg) == "Universe", "can't continue without a universe")
    ok(pick(pg, "Source universe", "ember"), "universe chosen"); nxt(pg); ok(step(pg) == "Scenario", "Scenario step")
    pg.evaluate("(()=>{const c=[...document.querySelectorAll('#wz .ff-mode-card, #wz label.chk')].find(x=>/takeover/i.test(x.textContent));(c.querySelector('input')||c).click()})()"); pg.wait_for_timeout(150)
    ok(pg.evaluate("[...document.querySelectorAll('#wz .ff-mode-card')].some(c=>/takeover/i.test(c.textContent)&&c.getAttribute('aria-pressed')==='true')"), "scenario card toggles on")
    nxt(pg); ok(step(pg) == "Character", "Character step")
    nxt(pg); ok("character identity" in status(pg), "takeover without a canon character is refused")
    ok(pick(pg, "Canon character", "char:ember:kael"), "canon character chosen"); nxt(pg); ok(step(pg).startswith("Timeline"), "Timeline step")
    nxt(pg); ok(step(pg) == "Canon rules", "Canon rules step"); nxt(pg); ok(step(pg) == "Crossover", "Crossover step"); nxt(pg); ok(step(pg) == "Review", "Review step")
    rev = pg.evaluate("document.querySelector('#wz').innerText"); ok("Kael" in rev and "Locked rules" in rev, "review shows the player and locked rules")
    pg.locator("#wz button", has_text="Create fanfiction").click(); pg.wait_for_timeout(400)
    ok(pg.evaluate("DB.stories.length") == 1 and pg.evaluate("DB.stories[0].fanfic.canon.mode.takeover") == "char:ember:kael", "story created through ffCreateStory")
    ok(pg.evaluate("view.n") == "story", "wizard opens the new story")
    pg.evaluate("play(DB.stories[0],{})"); pg.wait_for_function("!busy&&DB.sessions.length===1&&DB.sessions[0].turns.length>=2", timeout=10000)
    ok(pg.evaluate("DB.sessions[0].canon&&DB.sessions[0].canon.universe") == "ember", "new playthrough inherits the canon")
    pg.evaluate("go({n:'home',tab:'studio'})"); pg.wait_for_timeout(300)
    tabs = pg.evaluate("[...document.querySelectorAll('[aria-label=\"Studio sections\"] button')].map(b=>b.textContent)")
    ok("Fanfiction" in tabs, "Studio shows a Fanfiction tab " + str(tabs))
    # drafts from inside the wizard
    pg.evaluate("(()=>{const o=document.getElementById('wz');if(o)o.remove();const d=document.createElement('div');d.id='wz';document.body.prepend(d);window.SFFanUI.createFanfiction(d)})()"); pg.wait_for_timeout(200)
    pick(pg, "Source universe", "ember"); pg.evaluate("document.querySelectorAll('#wz details').forEach(d=>d.open=true)")
    dn = pg.evaluate("(()=>{const i=[...document.querySelectorAll('#wz label.fld')].filter(f=>f.querySelector('span')&&f.querySelector('span').textContent.includes('Draft name')).map(f=>f.querySelector('input')).find(Boolean);if(!i)return false;i.value='Wizard draft';i.dispatchEvent(new Event('input',{bubbles:true}));return true})()")
    if dn: pg.locator("#wz button", has_text="Save draft").first.click(); pg.wait_for_timeout(200)
    ok(dn and pg.evaluate("ffDrafts().some(d=>d.name==='Wizard draft'&&d.universe==='ember')"), "wizard saves a draft through ffSaveDraft")
    pg.evaluate("(()=>{const o=document.getElementById('wz');o.remove();const d=document.createElement('div');d.id='wz';document.body.prepend(d);window.SFFanUI.createFanfiction(d);document.querySelectorAll('#wz details').forEach(x=>x.open=true)})()"); pg.wait_for_timeout(200)
    did = pg.evaluate("ffDrafts()[0].id")
    pg.evaluate("id=>{const s=[...document.querySelectorAll('#wz details select')][0];s.value=id;s.dispatchEvent(new Event('change',{bubbles:true}))}", did)
    n0 = len(errs); pg.locator("#wz button", has_text="Resume draft").first.click(); pg.wait_for_timeout(300)
    ok(len(errs) == n0 and pg.evaluate("[...document.querySelectorAll('#wz label.fld')].some(f=>f.querySelector('select')&&f.querySelector('select').value==='ember')"), "wizard resumes a draft (universe restored)")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
