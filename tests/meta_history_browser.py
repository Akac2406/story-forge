"""History examples of the notes block: narrator block (mt) first, else the repaired/hybrid block (rmt). Keeps recent turns showing the format. No network.
Run: python tests/meta_history_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8894
fails = []; errs = []; LAST = {"msgs": []}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"): return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "[[META]]\nEVENTS: none\nLEARNED: none\nSCENE: pier | Avery | morning"}, "finish_reason": "stop"}]}))
    LAST["msgs"] = b["messages"]
    txt = "The gulls cried.\n\n[[META]]\nEVENTS: none\nLEARNED: none\nSCENE: pier | Avery | morning\nENDING: none"
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: [DONE]\n\n")
T = [{"role": "user", "text": "Begin", "hide": True},
     {"role": "ai", "text": "Old reply A.", "mt": "[[META]]\nEVENTS: none\nLEARNED: none\nSCENE: dock | Avery | dawn\nNARRATOR-A"},
     {"role": "user", "text": "Go on."}, {"role": "ai", "text": "Reply B.", "rmt": "[[META]]\nEVENTS: 1 | action | Avery | pier | Avery walked | none\nSTEP-B"},
     {"role": "user", "text": "And?"}, {"role": "ai", "text": "Reply C.", "rmt": "garbage without header STEP-C"},
     {"role": "user", "text": "More."}, {"role": "ai", "text": "Reply D.", "mt": "[[META]]\nEVENTS: none\nLEARNED: none\nSCENE: pier | Avery | noon\nNARRATOR-D", "rmt": "[[META]]\nSTEP-D"}]
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "turns": T, "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    pg.fill("#input", "Look around."); pg.click("button[aria-label='Send']"); pg.wait_for_function("!busy&&DB.sessions[0].turns.length===10", timeout=10000)
    hist = "\n".join(m["content"] for m in LAST["msgs"][1:] if m["role"] == "assistant")
    ok("NARRATOR-A" in hist and "NARRATOR-D" in hist, "narrator blocks shown as examples")
    ok("STEP-B" in hist, "reply without a narrator block shows the repaired block instead")
    ok("STEP-C" not in hist, "a repaired block without the [[META]] header is not shown")
    ok("STEP-D" not in hist, "the narrator's own block wins over the repaired one")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
