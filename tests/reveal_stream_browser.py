"""Typewriter text reveal while streaming (display only): the saved reply is always complete, the screen ends with the full text,
Stop keeps what arrived, regenerate works, reduced motion shows text immediately. No network.
Run: python tests/reveal_stream_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8908
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
LONG = "The lighthouse keeper climbed the stairs one at a time, counting each worn step aloud. " * 6
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"): return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    txt = LONG.strip() + "\n\n[[META]]\nENDING: none"
    body = "".join("data: " + json.dumps({"choices": [{"delta": {"content": txt[i:i+40]}}]}) + "\n\n" for i in range(0, len(txt), 40)) + "data: [DONE]\n\n"
    route.fulfill(status=200, content_type="text/event-stream", body=body)
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Light", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"
def last_shown(pg): return pg.evaluate("(()=>{const b=[...document.querySelectorAll('#log .turn.ai .body')].pop();return b?b.textContent:''})()")
def send(pg, t):
    n = pg.evaluate(f"{S}.turns.length"); pg.fill("#input", t); pg.click("button[aria-label='Send']"); pg.wait_for_function(f"!busy&&{S}.turns.length==={n+2}", timeout=15000); pg.wait_for_timeout(400)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pg.evaluate(f"cvSet({S},{{layout:'visual-novel',textReveal:'typewriter',revealSpeed:5}})")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    send(pg, "I climb.")
    ok(pg.evaluate(f"{S}.turns[{S}.turns.length-1].text").startswith("The lighthouse keeper") and len(pg.evaluate(f"{S}.turns[{S}.turns.length-1].text")) >= len(LONG.strip()) - 2, "saved reply is complete even with a slow typewriter")
    ok(LONG.strip()[-40:] in last_shown(pg), "screen shows the full reply once streaming ends")
    pg.evaluate("regen()"); pg.wait_for_function("!busy", timeout=15000); pg.wait_for_timeout(400)
    ok(LONG.strip()[-40:] in last_shown(pg) and pg.evaluate(f"{S}.turns.length") == 4, "regenerate with typewriter ends with the full text")
    pg.evaluate("go({n:'home'})"); pg.wait_for_timeout(200); pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log"); pg.wait_for_timeout(200)
    ok(LONG.strip()[-40:] in last_shown(pg), "navigating away and back shows the full reply")
    pg.evaluate(f"apSet({S},{{reducedMotion:true}},'global')"); pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    send(pg, "Again.")
    ok(LONG.strip()[-40:] in last_shown(pg), "reduced motion: text shown immediately and complete")
    ok(pg.evaluate("busy") is False, "busy cleared")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
