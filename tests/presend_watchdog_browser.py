"""Pre-send steps (memory tidy-up, story check, references) can hang or fail without blocking the send. No network.
Run: python tests/presend_watchdog_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8910
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"): return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": "The tide turned.\n\n[[META]]\nENDING: none"}}]}) + "\n\ndata: [DONE]\n\n")
SEED = {"key": "sk-or-test", "migrated": True, "prepWait": 2, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"
def send(pg, t, n):
    pg.fill("#input", t); pg.click("button[aria-label='Send']"); pg.wait_for_function(f"!busy&&{S}.turns.length==={n}", timeout=15000)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    pg.evaluate("window.__sum=summarize;window.__need=needSum;needSum=()=>true;summarize=()=>new Promise(()=>{});null")
    t0 = time.time(); send(pg, "I wait for the tide.", 4); dt = time.time() - t0
    ok(dt < 8 and pg.evaluate(f"{S}.turns[3].text").startswith("The tide turned"), f"a memory tidy-up that never finishes no longer blocks the send ({dt:.1f}s)")
    ok("taking too long" in pg.evaluate("document.body.innerText"), "the player is told the step was skipped")
    pg.evaluate("summarize=()=>Promise.reject(new Error('boom'));null")
    send(pg, "Again.", 6)
    ok(pg.evaluate(f"{S}.turns[5].text").startswith("The tide turned") and pg.evaluate("document.querySelector('#input').value") == "", "a tidy-up that fails no longer drops the send")
    pg.evaluate("summarize=window.__sum;needSum=window.__need;null")
    send(pg, "Once more.", 8); ok(pg.evaluate("busy") is False, "normal sends unaffected")
    br.close()
finally:
    srv.terminate()
ok(not [e for e in errs if "boom" not in e], "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
