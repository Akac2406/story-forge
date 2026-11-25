"""ChatGPT's Universe, Gameplay and Creator studios: open without errors, appear in the menu, and drive the engines through adapters. No network.
Run: python tests/studios_browser.py"""
import copy, json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8898
FX = json.load(open(os.path.join(HERE, "fixtures", "fanfic-ember.json")))
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
U = copy.deepcopy(FX["universe"]); U["rev"] = 2
U["records"].append({"id": "fact:ember:twin", "layer": "universe", "kind": "fact", "text": "The Warden has a twin", "who": [], "canon": "source", "rev": 2, "spoilerAt": {"ch": 45}})
ff = dict(FX["session"]); ff.update({"id": "f1", "storyId": "ffs", "char": {"name": "Kael"}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Gates."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 2})
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "universes": {"ember": U},
        "stories": [{"id": "s1", "kind": "story", "title": "Debut", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []},
                    {"id": "ffs", "kind": "story", "title": "Ember", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Mina"}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Day one."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}, ff]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"; F = "DB.sessions[1]"
def body(pg): return pg.evaluate("document.body.innerText")
def click(pg, name):
    b = pg.get_by_role("button", name=name)
    if b.count() == 0: return False
    b.last.click(); pg.wait_for_timeout(250); return True
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept())
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    ok(pg.evaluate("['universe','gameplay','creator'].every(k=>typeof window.SFFanUI[k]==='function')"), "three studios exported")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log"); pg.evaluate(f"menuSheet({S},DB.stories[0])"); pg.wait_for_timeout(300)
    m = pg.evaluate("[...document.querySelectorAll('details.story-tools')].map(d=>d.textContent).join('|')"); ok("Gameplay Studio" in m and "Creator Studio" in m and "Universe Studio" not in m, "original story menu: gameplay + creator, no universe studio")
    pg.evaluate("go({n:'chat',id:'f1'})"); pg.wait_for_selector("#log"); pg.evaluate(f"menuSheet({F},DB.stories[1])"); pg.wait_for_timeout(300)
    ok("Universe Studio" in pg.evaluate("[...document.querySelectorAll('details.story-tools')].map(d=>d.textContent).join('|')"), "fanfiction story menu has Universe Studio")
    for k, sess, title in [("universe", F, "Universe"), ("gameplay", S, "Gameplay"), ("creator", S, "Creator")]:
        n0 = len(errs); pg.evaluate(f"window.SFFanUI.{k}({sess})"); pg.wait_for_timeout(300)
        ok(len(errs) == n0 and title in body(pg), f"{title} Studio opens without errors")
    # Universe: upgrade via the screen
    pg.evaluate(f"window.SFFanUI.universe({F})"); pg.wait_for_timeout(300)
    up = [b for b in pg.evaluate("[...document.querySelectorAll('button')].map(b=>b.textContent)") if "pgrade" in b]
    if up: pg.get_by_role("button", name=up[-1]).last.click(); pg.wait_for_timeout(300)
    ok(bool(up) and pg.evaluate(f"{F}.canon.rev") == 2, "Universe Studio upgrade button goes through ffUpgrade " + str(up[:2]))
    # Gameplay: enable + start idol career via the screen
    pg.evaluate(f"window.SFFanUI.gameplay({S})"); pg.wait_for_timeout(300)
    labels = pg.evaluate("[...document.querySelectorAll('button')].map(b=>b.textContent)")
    st = [b for b in labels if "areer" in b and ("Start" in b or "start" in b)]
    if st: pg.get_by_role("button", name=st[0]).last.click(); pg.wait_for_timeout(300)
    ok(bool(st) and pg.evaluate(f"!!{S}.game&&!!{S}.game.career"), "Gameplay Studio starts a career through gmStartCareer " + str(st[:2]))
    n0 = len(errs); pg.evaluate(f"window.SFFanUI.gameplay({S})"); pg.wait_for_timeout(300); ok(len(errs) == n0, "Gameplay Studio reopens with a running career")
    # Creator: export uses crBuild (download), no page errors
    pg.evaluate(f"window.SFFanUI.creator({S})"); pg.wait_for_timeout(300)
    labels = pg.evaluate("[...document.querySelectorAll('button')].map(b=>b.textContent)")
    ex = [b for b in labels if "Download package" in b]
    if ex:
        with pg.expect_download(timeout=5000) as d: pg.get_by_role("button", name=ex[0]).last.click()
        data = json.loads(open(d.value.path()).read())
        ok(data.get("format") == "story-forge-creator" and "sk-or-test" not in json.dumps(data), "Creator Studio export downloads a clean package " + ex[0])
    else: ok(False, "Creator Studio has an export button " + str(labels[:12]))
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
