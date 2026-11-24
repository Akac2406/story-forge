"""Memory Phase 2: with "Let the narrator use story memory" on, the narrator is told who knows what.
Simulated replies, throwaway story, no network. Run: python tests/memory_phase2_v87.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8896
fails = []; errs = []; calls = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
META = ["SCENE: harbor office | Rae, Dale | night\nEVENTS: 4 | reveal | Rae | harbor office | Rae finds the ledger is forged | none\nLEARNED: Rae: the ledger is forged (she read it)",
        "SCENE: harbor office | Rae, Dale | night\nEVENTS: none\nLEARNED: none"]
def model(route):
    b = json.loads(route.request.post_data); calls.append(b)
    if not b.get("stream"):
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    n = len([c for c in calls if c.get("stream")])
    txt = 'Rae | "Reply number %d."\n\n[[META]]\n%s\nENDING: none' % (n, META[min(n - 1, 1)])
    route.fulfill(status=200, content_type="text/event-stream",
                  body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\ndata: [DONE]\n\n")
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "A harbor town.", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "memv2": True,
                      "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog over the harbor."}],
                      "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
def sysmsg(): return [c for c in calls if c.get("stream")][-1]["messages"][0]["content"]
def send(pg, text, n):
    pg.fill("#input", text); pg.click("button[aria-label='Send']"); pg.wait_for_selector(f"text=Reply number {n}"); pg.wait_for_timeout(600)
with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    send(pg, "I open the ledger.", 1)
    m = pg.evaluate("DB.sessions[0].mem")
    ok(m and any("ledger is forged" in f["text"] for f in m["facts"]) and m["scene"]["who"] == ["Rae", "Dale"], "memory recorded the secret and the scene")
    send(pg, "I close the ledger.", 2)
    ok("Who knows what" not in sysmsg(), "switch off (default): narrator gets no memory section")
    ok(pg.evaluate("!DB.sessions[0].memPrompt"), "switch is off by default")
    pg.click("button[aria-label='Menu']"); pg.click("button.drow:has-text('Story memory (beta)')"); pg.wait_for_timeout(300)
    box = pg.locator("label.chk:has-text('Let the narrator use story memory') input")
    ok(box.count() == 1 and not box.is_checked(), "Story memory sheet shows the new switch, unticked")
    box.check(); pg.wait_for_timeout(200); pg.evaluate("closeSheet(true)")
    ok(pg.evaluate("DB.sessions[0].memPrompt") is True, "switch turns Phase 2 on for this story")
    send(pg, "I look at Dale.", 3)
    S = sysmsg(); k = S.find("Who knows what")
    ok(k > 0, "switch on: narrator gets the memory section")
    sec = S[k:k + 1500]
    ok("Current scene: harbor office, night; present: Rae, Dale" in sec, "current scene and who is present")
    ok("Rae knows: the ledger is forged" in sec, "Rae knows the secret")
    ok("Dale does NOT know: the ledger is forged" in sec, "Dale is marked as not knowing it")
    ok("Rae finds the ledger is forged" in sec, "recent key event listed")
    ok("must not mention it or react to it" in sec, "instruction to keep secrets from those who don't know")
    R = pg.evaluate("promptReport(DB.sessions[0])")
    ok(any(s["name"] == "who knows what" and s["sent"] for s in R["sections"]), "inspector report lists the memory section as sent")
    # other stories are unaffected
    pg.evaluate("DB.sessions.push(Object.assign(JSON.parse(JSON.stringify(DB.sessions[0])),{id:'e2',memPrompt:false}));save()")
    pg.evaluate("go({n:'chat',id:'e2'})"); pg.wait_for_selector("#log")
    send(pg, "Elsewhere.", 4)
    ok("Who knows what" not in sysmsg(), "a story with the switch off still gets no memory section")
    # the setting survives a reload and a backup round trip
    pg.reload(); pg.wait_for_selector(".cta")
    ok(pg.evaluate("DB.sessions[0].memPrompt") is True, "switch survives reload")
    br.close()
srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
