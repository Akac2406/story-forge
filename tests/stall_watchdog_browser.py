"""A reply stream that stops sending is cancelled by the stall watchdog; the story is not left busy, nothing is lost. No network.
Run: python tests/stall_watchdog_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8893
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
MODE = {"hang": True}; HELD = []
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"): return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    if MODE["hang"]: HELD.append(route); return  # never answer: simulates a stalled connection
    txt = "The tide came in.\n\n[[META]]\nENDING: none"
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: [DONE]\n\n")
SEED = {"key": "sk-or-test", "migrated": True, "stallWait": 3, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    pg.fill("#input", "Wait for the tide."); pg.click("button[aria-label='Send']"); pg.wait_for_timeout(1000)
    ok(pg.evaluate("busy") is True, "stalled request leaves the story busy at first")
    pg.wait_for_function("!busy", timeout=12000)
    ok(pg.evaluate("DB.sessions[0].turns.length") == 2, "watchdog cancelled the stalled reply; no empty turn left behind")
    ok("stopped arriving" in pg.evaluate("document.body.innerText"), "player is told the reply stalled")
    ok(pg.evaluate("document.querySelector('#input').value") == "Wait for the tide.", "the player's message is back in the box")
    for r in HELD:
        try: r.abort()
        except Exception: pass
    MODE["hang"] = False; pg.click("button[aria-label='Send']"); pg.wait_for_function("!busy&&DB.sessions[0].turns.length===4", timeout=10000)
    ok("tide came in" in pg.evaluate("DB.sessions[0].turns[3].text"), "the next send works normally")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
