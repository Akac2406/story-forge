"""Story Director + NPC/development adapters in the app. Off by default; when on, guidance is in the prompt. No network.
Run: python tests/director_app_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8886
fails = []; errs = []; LAST = {"sys": ""}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"): return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    LAST["sys"] = b["messages"][0]["content"] if isinstance(b["messages"][0]["content"], str) else ""
    txt = 'The fog rolled over the harbor. Lamps flickered along the pier.\n\n[[META]]\nENDING: none'
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\ndata: [DONE]\n\n")
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "cast": {"June": {"u": 5}, "Rae": {"u": 9}},
                      "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    st = pg.evaluate(f"dirSettings({S})"); ok(st["enabled"] is False and st["focus"]["mainPlot"] == "high", "director off by default, settings include enabled + defaults")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    pg.fill("#input", "Wait."); pg.click("button[aria-label='Send']"); pg.wait_for_timeout(1200)
    ok("STORY DIRECTOR" not in LAST["sys"], "off: no director guidance in the prompt")
    ok(pg.evaluate(f"dirEnable({S},true).applied") and not pg.evaluate(f"dirEnable({S},true).applied"), "enable applies once, then reports unchanged")
    ok(pg.evaluate(f"dirSet({S},{{dialogue:'high'}}).applied") and pg.evaluate(f"dirSet({S},{{dialogue:'loud'}}).reason") == "bad value for dialogue", "settings validated")
    pg.fill("#input", "Wait more."); pg.click("button[aria-label='Send']"); pg.wait_for_timeout(1200)
    ok("STORY DIRECTOR" in LAST["sys"] and "more spoken dialogue" in LAST["sys"] and "Never skip time unless the player asks" in LAST["sys"], "on: guidance reflects settings and what happened (no dialogue so far)")
    an = pg.evaluate(f"dirAnalyze({S})"); ok(an["dialogueShare"] == 0 and an["replies"] >= 2, "analysis available to the UI")
    pg.evaluate(f"dirEnable({S},false)"); pg.fill("#input", "Go."); pg.click("button[aria-label='Send']"); pg.wait_for_timeout(1200)
    ok("STORY DIRECTOR" not in LAST["sys"] and pg.evaluate(f"dirSettings({S}).dialogue") == "high", "disabling removes guidance but keeps settings")
    r = pg.evaluate(f"chSetNpc({S},'Dale',{{goals:[{{text:'Hide the debt',priority:5}}],schedule:[{{day:2,where:'cove',doing:'pays'}}]}})")
    ok(r["applied"] and pg.evaluate(f"chAgenda({S},'Dale',0,3).where") == "cove", "NPC plan set through the adapter and used by the agenda")
    ok(pg.evaluate(f"chSetNpc({S},'Dale',{{schedule:[{{day:-1}}]}}).reason") == "schedule days must be 0 or more" and pg.evaluate(f"chSetNpc({S},'',{{}}).reason") == "needs a name", "invalid NPC plans rejected")
    ok(pg.evaluate(f"chAddDevelopment({S},'June','June has opened up to the crew').applied") and pg.evaluate(f"chDevelopments({S},'June').developments.length") == 1, "development note recorded")
    ok(pg.evaluate(f"chRemoveDevelopment({S},'June',0).applied") and pg.evaluate(f"chRemoveDevelopment({S},'June',5).reason") == "not found", "development note removed; bad index rejected")
    ok(pg.evaluate(f"chRemoveNpc({S},'Dale').applied"), "NPC plan removed")
    ok(pg.evaluate("MEM_RESOLVE_CHOICES.join()") == "keep-narrator,keep-step,edited,dismissed", "memResolve choice list exposed")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
