"""v89: memory notes taken in a separate quick step after each reply (per-story switch).
Simulated replies, throwaway story, no network. Run: python tests/memory_extract_v89.py"""
import json, os, re, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8898
fails = []; errs = []; calls = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
N = {"story": 0}
def model(route):
    b = json.loads(route.request.post_data); calls.append(b)
    first = b["messages"][0]["content"] if isinstance(b["messages"][0]["content"], str) else ""
    if not b.get("stream"):
        if "Read this one story reply and write its metadata" in first:
            n = re.search(r"Reply number (\d+)", first); n = n.group(1) if n else "?"
            blk = ("[[META]]\nEVENTS: 3 | reveal | Rae | harbor office | Rae reads entry %s of the ledger | Dale\n"
                   "LEARNED: Rae: ledger entry %s is forged (she read it)\nSCENE: harbor office | Rae, Dale | night") % (n, n)
            return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": blk}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 300, "completion_tokens": 80}}))
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    N["story"] += 1
    txt = 'Rae | "Reply number %d."\n\n[[META]]\nCAST: none\nENDING: none' % N["story"]
    route.fulfill(status=200, content_type="text/event-stream",
                  body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\ndata: [DONE]\n\n")
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "A harbor town.", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "memv2": True, "metaRepair": True,
                      "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog over the harbor."}],
                      "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
stream = lambda: [c for c in calls if c.get("stream")]
extracts = lambda: [c for c in calls if not c.get("stream") and isinstance(c["messages"][0]["content"], str) and "Read this one story reply" in c["messages"][0]["content"]]
def facts(pg): return pg.evaluate("(DB.sessions[0].mem&&DB.sessions[0].mem.facts||[]).map(f=>f.text)")
def send(pg, text, n):
    pg.fill("#input", text); pg.click("button[aria-label='Send']"); pg.wait_for_selector(f"text=Reply number {n}")
with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    # switch off (default): narrator is asked for the memory lines; a reply without them is filled in once (old behaviour)
    send(pg, "I open the ledger.", 1); pg.wait_for_timeout(800)
    sm = stream()[-1]["messages"][0]["content"]
    ok("EVENTS:" in sm[sm.find("[[META]]"):] and "LEARNED:" in sm[sm.find("[[META]]"):], "switch off: narrator still asked for memory lines")
    ok(len(extracts()) == 0, "switch off: a reply that has a META block gets no extra request, as before")
    ok(pg.evaluate("!DB.sessions[0].memExtract"), "switch is off by default")
    # turn the switch on through the Story memory sheet
    pg.click("button[aria-label='Menu']"); pg.click("button.drow:has-text('Story memory (beta)')"); pg.wait_for_timeout(300)
    box = pg.locator("label:has-text('Memory notes') select")
    ok(box.count() == 1 and box.input_value() == "off", "Story memory sheet shows the Memory notes choice, set to the narrator")
    box.select_option("step"); pg.evaluate("closeSheet(true)")
    ok(pg.evaluate("DB.sessions[0].memExtract") is True, "choosing the separate step turns it on")
    n0 = len(extracts())
    send(pg, "I read on.", 2)
    pg.wait_for_function("RPQ.size===0"); pg.wait_for_timeout(300)
    sm = stream()[-1]["messages"][0]["content"]; meta = sm[sm.find("[[META]]"):]
    ok("EVENTS:" not in meta and "LEARNED:" not in meta and "SCENE:" not in meta, "switch on: narrator no longer asked for memory lines")
    ok(len(extracts()) == n0 + 1, "switch on: one separate memory step after the reply")
    ok(any("entry 2 is forged" in f for f in facts(pg)), "memory recorded from the separate step")
    x = extracts()[-1]
    ok("Reply number 2" in x["messages"][0]["content"] and x.get("max_tokens", 0) <= 3000, "the step reads only that reply and is short")
    # back-to-back replies: every one gets its step, in order
    send(pg, "I keep reading.", 3); send(pg, "And again.", 4)
    pg.wait_for_function("RPQ.size===0"); pg.wait_for_timeout(300)
    fs = facts(pg)
    ok(any("entry 3" in f for f in fs) and any("entry 4" in f for f in fs), "back-to-back replies are both recorded (queued, not skipped)")
    ev_turns = pg.evaluate("DB.sessions[0].mem.events.map(e=>e.t)")
    ok(ev_turns == sorted(ev_turns), f"events stay in story order: {ev_turns}")
    # regenerate: the new version gets its own notes; switching back restores the old ones
    pg.click("button[aria-label='Regenerate']"); pg.wait_for_selector("text=Reply number 5")
    pg.wait_for_function("RPQ.size===0"); pg.wait_for_timeout(300)
    ok(any("entry 5" in f for f in facts(pg)) and not any("entry 4" in f for f in facts(pg)), "regenerated reply: memory switched to the new version")
    pg.click("button[aria-label='Previous version']"); pg.wait_for_timeout(500)
    ok(any("entry 4" in f for f in facts(pg)) and not any("entry 5" in f for f in facts(pg)), "previous version: its own memory restored")
    # the next prompt waits for a pending step, so memory is current
    pg.evaluate("DB.sessions[0].memPrompt=true;save()")
    send(pg, "I look at Dale.", 6); pg.wait_for_function("RPQ.size===0")
    send(pg, "I speak.", 7)
    sm = stream()[-1]["messages"][0]["content"]
    ok("entry 6 is forged" in sm, "with Phase 2 on, the next prompt already includes the previous reply's notes")
    # turning the switch off restores the old behaviour
    pg.evaluate("DB.sessions[0].memExtract=false;save()")
    send(pg, "Done.", 8); pg.wait_for_timeout(800)
    sm = stream()[-1]["messages"][0]["content"]
    ok("EVENTS:" in sm[sm.find("[[META]]"):], "switch off again: narrator asked for memory lines again")
    br.close()
srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
