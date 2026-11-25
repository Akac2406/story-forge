"""v91: hybrid memory. The narrator writes its own memory lines; a quick check after each reply fills scene, cast and
anything missing, never replacing the narrator's events or knowledge. Simulated replies, no network.
Run: python tests/memory_hybrid_v91.py"""
import json, os, re, subprocess, sys, time
from playwright.sync_api import sync_playwright
import menu_helper  # opens collapsible novel-menu categories for older tests (UI overhaul)
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8899
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
            blk = ("[[META]]\nEVENTS: 3 | reveal | Rae | harbor office | STEP event %s about the ledger | Dale\n"
                   "LEARNED: Rae: STEP fact %s about the ledger (she read it); Dale: STEP fact %s seen by Dale (he watched)\nSCENE: harbor office | Rae, Dale | night") % (n, n, n)
            return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": blk}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 300, "completion_tokens": 80}}))
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    N["story"] += 1; n = N["story"]
    if n % 2:   # odd: narrator writes full notes, but places the scene in the wrong room
        meta = ("[[META]]\nEVENTS: 3 | reveal | Rae | kitchen | NARR event %d about the ledger | none\n"
                "LEARNED: Rae: NARR fact %d about the ledger (she read it)\nSCENE: kitchen | Rae | night\nENDING: none") % (n, n)
    else:       # even: narrator writes a block with no memory lines at all
        meta = "[[META]]\nCAST: none\nENDING: none"
    txt = 'Rae | "Reply number %d." Dale watches from the doorway of the harbor office.\n\n%s' % (n, meta)
    route.fulfill(status=200, content_type="text/event-stream",
                  body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\ndata: [DONE]\n\n")
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "A harbor town.", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "memv2": True,
                      "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog over the harbor."}],
                      "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
stream = lambda: [c for c in calls if c.get("stream")]
steps = lambda: [c for c in calls if not c.get("stream") and isinstance(c["messages"][0]["content"], str) and "Read this one story reply" in c["messages"][0]["content"]]
M = "(()=>{const m=DB.sessions[0].mem||{};return {ev:(m.events||[]).map(e=>e.text),facts:(m.facts||[]).map(f=>f.text),scene:m.scene||{}}})()"
def send(pg, text, n):
    pg.fill("#input", text); pg.click("button[aria-label='Send']"); pg.wait_for_selector(f"text=Reply number {n}")
    pg.wait_for_function("RPQ.size===0"); pg.wait_for_timeout(300)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    # --- pure reconcile rules
    r = pg.evaluate("""(()=>{const nat={events:[{text:'n1'}],learned:[{who:'Rae',text:'a'}],scene:{where:'kitchen',who:['Rae']}},
      step={events:[{text:'s1'}],learned:[{who:'Rae',text:'b'},{who:'Dale',text:'c'}],scene:{where:'harbor office',who:['Rae','Dale']}};
      const a=memReconcile(nat,step),b=memReconcile({events:[],learned:[],scene:null},step),c=memReconcile(nat,{events:[],learned:[],scene:{valid:false}});
      return {a:[a.rec.events.map(e=>e.text),a.rec.learned.map(l=>l.text),a.rec.scene.where,a.src,a.conflicts.length],b:[b.rec.events.map(e=>e.text),b.src],c:[c.rec.scene.where,c.src.scene]}})()""")
    ok(r["a"][0] == ["n1"] and r["a"][1] == ["a"], "reconcile: the narrator's events and knowledge are kept, the step's are not added on top")
    ok(r["a"][2] == "harbor office" and r["a"][3]["scene"] == "step", "reconcile: scene comes from the step when it names a place")
    ok(r["a"][4] == 2, "reconcile: the different place and the extra Dale fact are both flagged as conflicts")
    ok(r["b"][0] == ["s1"] and r["b"][1]["events"] == "step" and r["b"][1]["learned"] == "step", "reconcile: when the narrator wrote nothing, the step fills everything")
    ok(r["c"] == ["kitchen", "narrator"], "reconcile: with no usable step scene, the narrator's scene is kept")
    # --- choose hybrid in the Story memory sheet
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    pg.click("button[aria-label='Menu']"); pg.click("button.drow:has-text('Story memory (beta)')"); pg.wait_for_timeout(300)
    sel = pg.locator("label:has-text('Memory notes') select")
    ok(sel.count() == 1 and sel.input_value() == "off", "sheet offers the Memory notes choice, default narrator only")
    sel.select_option("hybrid"); pg.evaluate("closeSheet(true)")
    ok(pg.evaluate("DB.sessions[0].memExtract") == "hybrid", "hybrid stored on the story")
    # --- reply 1: narrator wrote full notes with the wrong room
    send(pg, "I open the ledger.", 1)
    sm = stream()[-1]["messages"][0]["content"]; meta = sm[sm.find("[[META]]"):]
    ok("EVENTS:" in meta and "LEARNED:" in meta, "hybrid: the narrator is still asked for its memory lines")
    ok(len(steps()) == 1, "hybrid: one quick check after the reply")
    m = pg.evaluate(M)
    ok(any("NARR event 1" in e for e in m["ev"]) and not any("STEP event 1" in e for e in m["ev"]), "narrator's event kept; the step's event not added (no duplicates)")
    ok(any("NARR fact 1" in f for f in m["facts"]) and not any("STEP fact 1" in f for f in m["facts"]), "narrator's knowledge kept; the step does not override it")
    ok("harbor" in (m["scene"].get("where") or "").lower() and "Dale" in " ".join(m["scene"].get("who") or []), "scene and cast taken from the step (harbor office, Dale present)")
    pg.wait_for_function("(DB.sessions[0].memDiag||[]).slice(-1)[0]&&DB.sessions[0].memDiag.slice(-1)[0].rp", timeout=5000); d = pg.evaluate("DB.sessions[0].memDiag.slice(-1)[0].rp")
    ok(d and d.get("src", {}).get("events") == "narrator" and d.get("src", {}).get("scene") == "step", f"where each part came from is recorded: {d and d.get('src')}")
    ok(d and any("kitchen" in c for c in d.get("conflicts", [])), "the narrator/step disagreement about the room is flagged")
    pg.wait_for_function("(DB.sessions[0].turns.filter(t=>t.role==='ai').pop().msrc||{}).events", timeout=5000); ok(pg.evaluate("DB.sessions[0].turns.filter(t=>t.role==='ai').pop().msrc.events") == "narrator", "the reply itself remembers its sources")
    # --- reply 2: narrator left memory out entirely -> step fills it
    send(pg, "I read on.", 2)
    m = pg.evaluate(M)
    ok(any("STEP event 2" in e for e in m["ev"]) and any("STEP fact 2" in f for f in m["facts"]), "narrator wrote nothing: the step fills events and knowledge")
    # --- regenerate: new version gets its own reconciled notes; going back restores the old ones
    pg.click("button[aria-label='Regenerate']"); pg.wait_for_selector("text=Reply number 3"); pg.wait_for_function("RPQ.size===0"); pg.wait_for_timeout(300)
    m = pg.evaluate(M)
    ok(any("NARR event 3" in e for e in m["ev"]) and not any("STEP event 2" in e for e in m["ev"]), "regenerated reply: memory switched to the new version")
    pg.click("button[aria-label='Previous version']"); pg.wait_for_timeout(500)
    m = pg.evaluate(M)
    ok(any("STEP event 2" in e for e in m["ev"]) and not any("NARR event 3" in e for e in m["ev"]), "previous version: its own memory restored")
    ok(pg.evaluate("(DB.sessions[0].turns.filter(t=>t.role==='ai').pop().msrc||{}).events") == "step", "previous version: its sources restored too")
    n_ev = len(pg.evaluate(M)["ev"])
    ok(n_ev == 2, f"no abandoned or duplicate events after regenerate and back ({n_ev})")
    # --- status and retry helpers for the UI
    stt = pg.evaluate("memStatus(DB.sessions[0])")
    ok(stt["mode"] == "hybrid" and stt["pending"] is False and stt["checked"] >= 3 and stt["ok"] == stt["checked"] and stt["last"]["src"], f"memStatus summarises mode, checks and sources: {dict((k, stt[k]) for k in ('mode','checked','ok'))}")
    ok(any(c["items"] for c in stt["conflicts"]), "memStatus lists flagged conflicts")
    n0 = len(steps()); t = pg.evaluate("DB.sessions[0].turns.length-1")
    r = pg.evaluate(f"memRetry(DB.sessions[0],{t})")
    ok(r["ok"] and len(steps()) == n0 + 1 and len(pg.evaluate(M)["ev"]) == n_ev, "memRetry re-checks one reply without duplicating events")
    # --- full separate mode still skips the narrator's lines; off asks no checks
    pg.evaluate("DB.sessions[0].memExtract=true;save()"); n0 = len(steps())
    send(pg, "Next.", 4)
    sm = stream()[-1]["messages"][0]["content"]
    ok("EVENTS:" not in sm[sm.find("[[META]]"):] and len(steps()) == n0 + 1, "separate-step mode unchanged")
    pg.evaluate("DB.sessions[0].memExtract=false;save()"); n0 = len(steps())
    send(pg, "Done.", 5)
    ok(len(steps()) == n0, "off: no extra request when the narrator wrote its notes")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
