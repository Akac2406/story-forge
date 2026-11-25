"""Fanfiction story creation in the app: ffNewCanonPreview / ffCreateStory, and new playthroughs start with the canon and get the canon prompt block. No network.
Run: python tests/fanfic_create_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8904
FX = json.load(open(os.path.join(HERE, "fixtures", "fanfic-ember.json")))
fails = []; errs = []; LAST = {"sys": ""}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"): return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    LAST["sys"] = b["messages"][0]["content"]
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": "The academy gates open.\n\n[[META]]\nENDING: none"}}]}) + "\n\ndata: [DONE]\n\n")
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "universes": {"ember": FX["universe"]}, "stories": [], "sessions": []}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pv = pg.evaluate("ffNewCanonPreview('ember',{modes:['takeover','fixit'],takeover:'char:ember:kael',start:{ch:2}})"); ok(pv["ok"] and pv["summary"]["takeover"], "preview validates the choices")
    ok(pg.evaluate("ffNewCanonPreview('nope',{modes:['oc']}).reason") == "universe missing" and pg.evaluate("ffNewCanonPreview('ember',{modes:['oc'],player:{name:'S'},crossover:{with:['void']}}).reason") == "crossover universe missing", "missing universes reported")
    r = pg.evaluate("ffCreateStory('ember',{modes:['takeover','fixit'],takeover:'char:ember:kael',start:{ch:2},title:'Kael again'})")
    ok(r["applied"] and pg.evaluate("DB.stories.length") == 1 and pg.evaluate("DB.stories[0].fanfic.universe") == "ember", "story created with its fanfiction setup")
    ok(not pg.evaluate("ffCreateStory('ember',{modes:['takeover']}).applied") and pg.evaluate("DB.stories.length") == 1, "invalid setup creates nothing")
    pg.evaluate("play(DB.stories[0],{})"); pg.wait_for_function("!busy&&DB.sessions.length===1&&DB.sessions[0].turns.length>=2", timeout=10000)
    ok(pg.evaluate("DB.sessions[0].canon.universe") == "ember" and pg.evaluate("DB.sessions[0].canon.mode.takeover") == "char:ember:kael", "new playthrough starts with the canon")
    ok(pg.evaluate("DB.sessions[0].char.name") == FX["universe"]["chars"]["char:ember:kael"]["name"], "player named after the taken-over character when no name is given")
    ok("FANFICTION CANON" in LAST["sys"], "the opening prompt carries the fanfiction canon block")
    pg.evaluate("play(DB.stories[0],{name:'Kae'})"); pg.wait_for_function("!busy&&DB.sessions.length===2", timeout=10000)
    ok(pg.evaluate("DB.sessions[1].char.name") == "Kae" and pg.evaluate("DB.sessions[1].canon!==DB.sessions[0].canon"), "a second playthrough gets its own copy and keeps a chosen name")
    ok(pg.evaluate("ffSetRule(DB.sessions[1],'history','free').applied") and pg.evaluate("DB.sessions[0].canon.rules.history") == "locked" and pg.evaluate("DB.stories[0].fanfic.canon.rules.history") == "locked", "changing one playthrough's rules leaves the story and other playthroughs alone")
    d = pg.evaluate("ffSaveDraft({name:'Kael draft',universe:'ember',options:{modes:['takeover'],takeover:'char:ember:kael',start:{ch:1}}})")
    ok(d["applied"] and pg.evaluate("ffDrafts().length") == 1, "draft saved")
    ok(pg.evaluate(f"ffSaveDraft({{id:'{d['id']}',name:'Kael draft 2',universe:'ember',options:{{modes:['takeover'],takeover:'char:ember:kael',start:{{ch:3}}}}}}).id") == d["id"] and pg.evaluate("ffDrafts()[0].options.start.ch") == 3, "draft updated in place")
    ok(pg.evaluate("ffSaveDraft({name:'x',options:{sparkles:1}}).reason") == "unsupported option sparkles" and pg.evaluate("ffSaveDraft({name:'',options:{}}).reason") == "needs a name", "bad drafts refused")
    pg.reload(); pg.wait_for_selector(".cta")
    dr = pg.evaluate(f"ffLoadDraft('{d['id']}')"); ok(dr and dr["name"] == "Kael draft 2", "draft survives reload")
    ok(pg.evaluate("d=>ffCreateStory(d.universe,d.options).applied", dr) and pg.evaluate("ffCreateStory('ember',ffLoadDraft('" + d["id"] + "').options).applied"), "one draft can create several stories (reusable blueprint)")
    ok(pg.evaluate(f"ffDeleteDraft('{d['id']}').applied") and pg.evaluate("ffDrafts().length") == 0, "draft deleted")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
