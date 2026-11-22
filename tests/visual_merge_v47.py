"""v47 merge check: the Visual Suite and Studio must not disturb story data, and regenerate,
reply switching, branching, story memory and offline loading must still work with them in place.
Simulated replies only (no real model). Run: python tests/visual_merge_v47.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8847
fails = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
N = [0]
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"):
        return route.fulfill(status=200, content_type="application/json",
            body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    N[0] += 1
    txt = ('Dale wipes his hands. "Reply number %d," he says.\n\n[[META]]\nSCENE: where=hangar 2; when=night; present=Dale, Rae\n'
           'EVENTS: Dale answered Rae | Dale, Rae\nLEARNED: none\nENDING: none' % N[0])
    body = "".join("data: " + json.dumps({"choices": [{"delta": {"content": txt[i:i+40]}}]}) + "\n\n" for i in range(0, len(txt), 40))
    body += "data: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\ndata: [DONE]\n\n"
    route.fulfill(status=200, content_type="text/event-stream", body=body)
SEED = {"key": "sk-or-test", "modes": [{"n": "Swift", "id": "deepseek/deepseek-v4.1-flash", "d": ""}], "mode": 0, "fs": 17,
        "globalNote": "", "chars": [], "stories": [{"id": "s1", "kind": "story", "title": "Night Shift", "setting": "A mountain airport hangar in winter.", "entries": [{"k": "Dale Ortega, Dale", "t": "Lead mechanic", "a": True}], "stats": [], "endings": [], "starts": []}], "found": {}, "migrated": True,
        "sessions": [{"id": "t1", "storyId": "s1", "title": "Night Shift", "start": "start", "follow": "loose",
                      "char": {"name": "Rae Holloway", "desc": "new mechanic", "trait": ""},
                      "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Dale looks up from the cowling."},
                                {"role": "user", "text": "I ask about N42RL."}, {"role": "ai", "text": "\"Inspection's signed off,\" Dale says."}],
                      "temp": "", "mems": [], "note": "", "stats": {}, "upto": 0, "len": "300", "sugg": [], "ending": None, "ended": [],
                      "updated": 1, "memv2": True, "metaRepair": False}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
errs = []
def db(pg): return pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2'))")
def strip(s): return {k: v for k, v in s.items() if k not in ("updated",)}
with sync_playwright() as p:
    for name, vp in (("phone", {"width": 390, "height": 844}), ("desktop", {"width": 1280, "height": 860})):
        N[0] = 0
        br = p.chromium.launch(); ctx = br.new_context(viewport=vp); pg = ctx.new_page(); pg.set_default_timeout(15000)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route("https://openrouter.ai/**", model)
        pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
        pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED))
        pg.reload(); pg.wait_for_selector(".cta")
        ok(pg.evaluate("document.documentElement.scrollWidth") <= vp["width"], f"{name}: home fits the screen width")
        pg.click("nav.tabs button:has-text('Studio')"); pg.wait_for_timeout(300)
        ok(pg.evaluate("document.documentElement.scrollWidth") <= vp["width"], f"{name}: Studio tab fits the screen width")
        pg.evaluate("go({n:'chat',id:'t1'})"); pg.wait_for_selector("#log")
        before = strip(db(pg)["sessions"][0])
        pg.click("button.pill:has-text('Visuals')"); pg.wait_for_timeout(300)
        for t in ["Character RPG", "Relationships", "World Atlas", "Timeline", "Visual Novel", "Themes", "Art Studio"]:
            pg.click(f".sf-v46-tabs button:has-text('{t}')", timeout=3000); pg.wait_for_timeout(150)
        pg.evaluate("closeSheet(true)"); pg.wait_for_timeout(200)
        ok(strip(db(pg)["sessions"][0]) == before, f"{name}: browsing the Visual Suite leaves the story untouched")
        # send
        pg.fill("#input", "Show me the logbook."); pg.click("button[aria-label='Send']"); pg.wait_for_selector("text=Reply number 1")
        se = db(pg)["sessions"][0]; last = se["turns"][-1]
        ok(len(se["turns"]) == 6 and "[[META" not in last["text"], f"{name}: reply sent, metadata kept out of the story text")
        ok(bool(last.get("mt")), f"{name}: reply metadata stored for memory")
        # regenerate + switch
        pg.click("button[aria-label='Regenerate']"); pg.wait_for_selector("text=Reply number 2")
        se = db(pg)["sessions"][0]
        ok(len(se["turns"]) == 6 and N[0] == 2 and "Reply number 2" in se["turns"][-1]["text"],
           f"{name}: regenerate replaces the reply in place")
        pg.click("button[aria-label='Previous version']"); pg.wait_for_selector("text=Reply number 1")
        ok(pg.locator("text=Reply number 2").count() == 0, f"{name}: previous version shows reply 1")
        pg.click("button[aria-label='Next version']"); pg.wait_for_selector("text=Reply number 2")
        ok(True, f"{name}: next version shows reply 2")
        # visuals again mid-story
        pg.click("button.pill:has-text('Visuals')"); pg.wait_for_timeout(200); pg.evaluate("closeSheet(true)"); pg.wait_for_timeout(200)
        # branch
        pg.locator("button[aria-label='Message options']").first.click(); pg.click("text=Branch from here")
        pg.wait_for_selector("text=New branch started")
        ss = db(pg)["sessions"]
        ok(len(ss) == 2 and len(ss[0]["turns"]) == 6, f"{name}: branch created, original story kept whole")
        # memory controls on the branch
        pg.click("button[aria-label='Menu']"); pg.click("button.drow:has-text('Story memory (beta)')"); pg.wait_for_timeout(300)
        ok(pg.locator("text=Fill in memory").count() + pg.locator("text=Try it on a copy").count() > 0, f"{name}: Story memory (beta) sheet opens")
        pg.evaluate("closeSheet(true)"); pg.wait_for_timeout(200)
        ok(not db(pg).get("memv2"), f"{name}: memory not switched on globally")
        # offline
        if name == "desktop":
            pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
            pg.evaluate("navigator.serviceWorker.ready"); pg.wait_for_timeout(1500); pg.reload(); pg.wait_for_selector(".cta")
            ctx.set_offline(True); pg.reload()
            try: pg.wait_for_selector(".cta", timeout=8000); off = True
            except Exception: off = False
            ok(off, "app opens offline after one visit")
            if off:
                pg.click("nav.tabs button:has-text('Studio')"); pg.wait_for_timeout(300)
                ok(pg.locator("text=Visual Suite").count() > 0, "Studio works offline")
        br.close()
srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
