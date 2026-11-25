"""ChatGPT's Relationship Web, Character Journal, NPC Agenda, Memory Studio and Story Director screens. No network.
Run: python tests/character_screens_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8891
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "cast": {"June": {"u": 5}, "Rae": {"u": 9}},
                      "rel2": [{"a": "player", "b": "June", "trust": 20, "affection": 10, "respect": 5, "familiarity": 30, "rivalry": 0, "events": []}],
                      "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "June smiled at Avery on the pier. \"Morning,\" she said."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"
def sheet_text(pg): return pg.evaluate("[...document.querySelectorAll('.sheet,.sheet-body,[role=dialog]')].map(e=>e.innerText).join('\\n')")
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    ok(pg.evaluate("['web','journal','agenda','memory','director'].every(k=>typeof window.SFFanUI[k]==='function')"), "all five screens exported")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    pg.evaluate(f"menuSheet({S},DB.stories[0])"); pg.wait_for_timeout(300)
    menu = pg.evaluate("document.body.textContent")
    ok(all(x in menu for x in ["Relationship Web", "Character Journal", "NPC Agenda", "Memory Studio", "Story Director", "Story formats"]), "original story menu lists all five screens and keeps Story formats")
    for k, title in [("web", "Relationship Web"), ("journal", "Character Journal"), ("agenda", "NPC Agenda"), ("memory", "Memory Studio"), ("director", "Story Director")]:
        n0 = len(errs); pg.evaluate(f"window.SFFanUI.{k}({S})"); pg.wait_for_timeout(250)
        ok(len(errs) == n0 and title in pg.evaluate("document.body.innerText"), f"{title} opens without errors")
    pg.evaluate(f"window.SFFanUI.web({S})"); pg.wait_for_timeout(200)
    ok(pg.evaluate("!!document.querySelector('svg[aria-label=\"Directional relationship graph\"]')"), "relationship web draws the graph")
    pg.evaluate(f"window.SFFanUI.director({S})"); pg.wait_for_timeout(200)
    pg.locator("label.chk input").last.check(); pg.wait_for_timeout(200)
    ok(pg.evaluate(f"dirSettings({S}).enabled") is True, "director toggle goes through dirEnable")
    pg.evaluate(f"window.SFFanUI.memory({S})"); pg.wait_for_timeout(200)
    n = pg.evaluate(f"memView({S}).records.length")
    ta = pg.locator("textarea").last; ta.fill("Avery owes June a favor"); pg.get_by_role("button", name="Save memory").click(); pg.wait_for_timeout(200)
    ok(pg.evaluate(f"memQuery({S},{{text:'favor'}}).length") >= 1 and pg.evaluate(f"memView({S}).records.length") == n + 1, "Memory Studio add goes through memAdd")
    pg.get_by_role("button", name="Undo last memory edit").first.click(); pg.wait_for_timeout(200)
    ok(pg.evaluate(f"memView({S}).records.length") == n, "Memory Studio undo")
    ok(pg.evaluate(f"chStoryDay({S})") == pg.evaluate(f"(window.SFFanUI.agenda({S}),chStoryDay({S}))"), "opening NPC Agenda does not advance story time")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
