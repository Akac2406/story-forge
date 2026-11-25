"""Gameplay adapters (phase 9) in the app: off by default, opt-in prompt section, career/quests/rules, undo, persistence. No network.
Run: python tests/gameplay_app_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8895
fails = []; errs = []; LAST = {"sys": ""}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"): return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    LAST["sys"] = b["messages"][0]["content"]
    txt = "The studio lights hummed.\n\n[[META]]\nENDING: none"
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: [DONE]\n\n")
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Debut", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Mina"}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Day one."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"
def send(pg, t):
    n = pg.evaluate(f"{S}.turns.length"); pg.fill("#input", t); pg.click("button[aria-label='Send']"); pg.wait_for_function(f"!busy&&{S}.turns.length==={n+2}", timeout=10000)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    ok(pg.evaluate("typeof SFGame==='object'&&gmCareers().length>=3"), "engine loaded; careers listed")
    ok(pg.evaluate(f"gmState({S}).enabled") is False and pg.evaluate(f"{S}.game") is None, "off by default and nothing stored until used")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log"); send(pg, "Practice.")
    ok("GAMEPLAY STATE" not in LAST["sys"], "off: no gameplay section in the prompt")
    ok(pg.evaluate(f"gmStartCareer({S},'idol').applied") and pg.evaluate(f"{S}.game.career.rank") == "trainee", "idol career started")
    r = pg.evaluate(f"gmActivity({S},'vocal_lesson')"); ok(r["applied"] and 2 <= r["result"]["got"]["vocal"] <= 5, "activity applies bounded gains")
    ok(pg.evaluate(f"gmActivity({S},'variety_show').reason") == "needs rank Rookie", "rank-gated activity refused")
    ok(pg.evaluate(f"gmAddQuest({S},{{id:'q1',title:'Pass the monthly evaluation',steps:['Rehearse','Perform']}}).applied") and pg.evaluate(f"gmAdvanceQuest({S},'q1').applied"), "quest added and advanced")
    ok(pg.evaluate(f"gmAddRule({S},{{id:'burnout',when:{{stat:'stress',op:'>=',value:60}},effect:{{fail:'q1'}},note:'Burnout: the evaluation is missed'}}).applied"), "consequence rule added")
    r = pg.evaluate(f"gmChange({S},'stress',70,'scandal')"); ok("burnout" in r["fired"] and pg.evaluate(f"{S}.game.quests[0].status") == "failed", "consequence fires through the adapter")
    ok(pg.evaluate(f"gmUndo({S}).applied") and pg.evaluate(f"{S}.game.quests[0].status") == "active", "undo reverts the change and its consequence")
    ok(pg.evaluate(f"gmEnable({S},true).applied") and pg.evaluate(f"gmEnable({S},true).reason") == "unchanged", "enable once")
    send(pg, "Go to practice.")
    ok("GAMEPLAY STATE" in LAST["sys"] and "Career: Idol" in LAST["sys"] and "Pass the monthly evaluation (1/2)" in LAST["sys"], "on: prompt carries career, stats and quests")
    pg.reload(); pg.wait_for_selector(".cta")
    ok(pg.evaluate(f"{S}.game.enabled") is True and pg.evaluate(f"{S}.game.career.week") == 1, "state persists across reload")
    pg.evaluate(f"gmEnable({S},false)"); pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log"); send(pg, "Rest.")
    ok("GAMEPLAY STATE" not in LAST["sys"] and pg.evaluate(f"{S}.game.career.id") == "idol", "disabling removes the section but keeps the game")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
