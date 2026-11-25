"""Creator packages in the app: build (no keys, no images by default, no progress), open, new playthroughs start from the blueprint. No network.
Run: python tests/creator_app_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8896
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"): return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": "Day one.\n\n[[META]]\nENDING: none"}}]}) + "\n\ndata: [DONE]\n\n")
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
SEED = {"key": "sk-or-test-key-123456789", "ocKey": "dummy-oc-key-123456", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Debut", "setting": "Seoul trainee dorm", "coverT": PNG, "cast0": [{"n": "Mina", "role": "trainee", "th": PNG}], "starts": [], "stats": [], "endings": [], "entries": []},
                    {"id": "s2", "kind": "story", "title": "From OOC", "setting": "x", "ooc": True, "coverT": PNG, "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Mina"}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Day one."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pg.evaluate(f"gmStartCareer({S},'idol');gmActivity({S},'vocal_lesson');gmAddQuest({S},{{id:'q1',title:'Evaluation',steps:['Rehearse','Perform']}});gmAdvanceQuest({S},'q1');gmEnable({S},true);dirEnable({S},true)")
    pg.evaluate("DB.charTemplates=DB.charTemplates||[]")
    r = pg.evaluate("crBuild('s1',{sessionId:'e1',creator:{name:'Anna'}})"); js = json.dumps(r.get("package"))
    ok(r["ok"] and "sk-or-test" not in js and "dummy-oc-key" not in js and "ocKey" not in js, "package has no keys")
    ok("data:image" not in js, "no images by default")
    ok(r["package"]["gameplay"]["career"]["week"] == 0 and r["package"]["gameplay"]["quests"][0]["done"] == [] and r["package"]["gameplay"]["stats"]["stamina"]["value"] == 80, "gameplay exported as setup without progress")
    ok("turns" not in js and r["package"]["director"]["enabled"] is True, "no playthrough text; director setup included")
    ok("data:image" in json.dumps(pg.evaluate("crBuild('s1',{art:true}).package")), "images included when allowed")
    ok("data:image" not in json.dumps(pg.evaluate("crBuild('s2',{art:true}).package")) and pg.evaluate("crBuild('s2',{art:true}).artBlocked"), "OOC-imported story never exports images")
    pv = pg.evaluate("p=>crPreview(p)", r["package"]); ok(pv["ok"] and pv["gameplay"]["career"] == "Idol", "preview works")
    o = pg.evaluate("p=>crOpen(p)", r["package"]); ok(o["applied"] and pg.evaluate("DB.stories.length") == 3, "opening adds a new story")
    nid = o["storyId"]; ok(pg.evaluate(f"!!getStory('{nid}').blueprint.game && !getStory('{nid}').coverT"), "blueprint stored on the new story; no cover image (package had none)")
    pg.evaluate(f"play(getStory('{nid}'),{{name:'Jun'}})"); pg.wait_for_function("!busy&&DB.sessions.length===2", timeout=10000)
    ns = "DB.sessions[1]"
    ok(pg.evaluate(f"{ns}.game.career.id") == "idol" and pg.evaluate(f"{ns}.game.career.week") == 0 and pg.evaluate(f"{ns}.director.enabled") is True, "new playthrough starts from the blueprint")
    ok(pg.evaluate(f"{S}.game.career.week") == 1, "original playthrough untouched")
    ok(not pg.evaluate("crOpen({format:'nope'}).applied"), "invalid package refused")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
