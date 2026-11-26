"""Phase 1 browser tests: drives the real app in Chromium with stand-in model replies.
Run: python tests/memory_phase1_browser.py      (prints "ERRORS: []" and exits 0 when everything passes)"""
import json, os, sys, subprocess, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.normpath(os.path.join(HERE, "..", "site"))
PORT = 8811
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
state = {"n": 0, "fail": False}; calls = []; results = []; errs = []
def check(name, cond, info=""):
    results.append((name, bool(cond))); print(("ok  " if cond else "FAIL"), name, "" if cond else info)
def model(route):
    b = json.loads(route.request.post_data); calls.append(b)
    if not b.get("stream"):
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- note"}, "finish_reason": "stop"}]}))
    if state["fail"]:
        return route.fulfill(status=500, content_type="application/json", body=json.dumps({"error": {"message": "provider down"}}))
    state["n"] += 1; n = state["n"]
    meta = f"\n\n[[META]]\nCAST: Kevin | swordsman | - | calm | wary\nEVENTS: 3 | action | Kevin | hall {n} | Kevin performs deed number {n} | Mira"
    meta += (f"\nLEARNED: Mira: hidden truth number {n} (she overheard)" if n % 2 == 0 else "\nLEARNED: none")
    meta += f"\nSCENE: hall {n} | Kevin, Mira | night {n}"
    txt = f"Reply number {n}. Kevin moves." + meta
    body = "data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5, "completion_tokens": 5}}) + "\n\ndata: [DONE]\n\n"
    route.fulfill(status=200, content_type="text/event-stream", body=body)
SEED = lambda flag: "()=>{localStorage.clear();localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,memRecallDefault:false,%smodes:[{n:'Swift',id:'a/b',d:''}],mode:0,stories:[{id:'s1',kind:'story',title:'Ledger Test',setting:'A hall.',entries:[],stats:[],endings:[],starts:[]}]}))}" % ("memv2:true," if flag else "")
DEEDS = "s=>s.mem?s.mem.events.filter(e=>e.src==='meta').map(e=>+e.text.match(/\\d+/)[0]):null"
def sess(pg, i=0): return pg.evaluate(f"JSON.parse(localStorage.getItem('story-forge-v2')).sessions[{i}]")
def deeds(pg, i=0): return pg.evaluate(f"({DEEDS})(JSON.parse(localStorage.getItem('story-forge-v2')).sessions[{i}])")
def ai_count(pg): return pg.evaluate("document.querySelectorAll('.turn.ai').length")
def wait_reply(pg, n): pg.wait_for_selector(f"text=Reply number {n}")
def send(pg, text, n): pg.fill("#input", text); pg.click("button[aria-label='Send']"); wait_reply(pg, n)
def start(pg, flag):
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta"); pg.evaluate(SEED(flag)); pg.reload(); pg.wait_for_selector(".cta")
    pg.click(".card:has-text('Ledger Test')"); pg.fill("input[placeholder='Your character’s name']", "Anna"); pg.click("button:text-is('Start story')")
with sync_playwright() as p:
    br = p.chromium.launch(args=["--no-sandbox"]); ctx = br.new_context(viewport={"width": 390, "height": 844}); pg = ctx.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)

    # A. Flag off (default): nothing changes
    state["n"] = 0; start(pg, False); wait_reply(pg, 1); send(pg, "I wait.", 2)
    sp = calls[-1]["messages"][0]["content"]; s0 = sess(pg)
    check("off: memv2 defaults to false", pg.evaluate("DB.memv2") is False)
    check("off: prompt does not ask for EVENTS/LEARNED/SCENE", "EVENTS:" not in sp and "LEARNED:" not in sp and "SCENE:" not in sp)
    check("off: no memory object and no deltas saved", "mem" not in s0 and not any("mx" in t for t in s0["turns"]))

    # B. Flag on
    state["n"] = 0; start(pg, True); wait_reply(pg, 1)
    sp = calls[-1]["messages"][0]["content"]
    check("on: prompt asks for EVENTS, LEARNED and SCENE", "EVENTS:" in sp and "LEARNED:" in sp and "SCENE:" in sp)
    send(pg, "I wait.", 2); send(pg, "I wait again.", 3)
    s = sess(pg); after3 = s["mem"]
    check("on: one event per reply recorded in order", deeds(pg) == [1, 2, 3], deeds(pg))
    check("on: every AI turn has a delta", all("mx" in t for t in s["turns"] if t["role"] == "ai"))
    check("on: event anchored to its AI turn index", [e["t"] for e in after3["events"] if e["src"] == "meta"] == [i for i, t in enumerate(s["turns"]) if t["role"] == "ai"])
    check("on: LEARNED adds knowledge", any(f["text"].startswith("hidden truth number 2") for f in after3["facts"]) and len(after3["chars"]["Mira"]["knows"]) == 1)
    check("on: SCENE updates scene and character location", after3["scene"]["where"] == "hall 3" and after3["chars"]["Kevin"]["state"]["where"] == "hall 3")
    check("on: existing CAST handling still works", "Kevin" in s["cast"])
    # regenerate twice -> versions 3, 4, 5 of the last turn
    pg.click("button[aria-label='Regenerate']"); wait_reply(pg, 4); pg.click("button[aria-label='Regenerate']"); wait_reply(pg, 5)
    check("regen: only the newest version's event is in memory", deeds(pg) == [1, 2, 5], deeds(pg))
    check("regen: version switcher shows 3 versions", pg.inner_text(".vsw").replace("\n", "") == "‹3/3›", pg.inner_text(".vsw"))
    pg.click("button[aria-label='Previous version']"); pg.wait_for_selector("text=Reply number 4")
    check("switch: version 2 restores its event", deeds(pg) == [1, 2, 4], deeds(pg))
    check("switch: version 2 restores its knowledge (deed 4 taught Mira)", any(f["text"].startswith("hidden truth number 4") for f in sess(pg)["mem"]["facts"]))
    pg.click("button[aria-label='Previous version']"); pg.wait_for_selector("text=Reply number 3")
    m = sess(pg)["mem"]
    check("switch: version 1 restores memory exactly as it was before regenerating",
          json.dumps({k: m[k] for k in ("events", "facts", "chars", "scene")}, sort_keys=True) == json.dumps({k: after3[k] for k in ("events", "facts", "chars", "scene")}, sort_keys=True))
    pg.click("button[aria-label='Next version']"); pg.wait_for_selector("text=Reply number 4"); pg.click("button[aria-label='Next version']"); pg.wait_for_selector("text=Reply number 5")
    check("switch: back to version 3", deeds(pg) == [1, 2, 5], deeds(pg))
    # failed regeneration keeps the old version and its memory
    state["fail"] = True; pg.click("button[aria-label='Regenerate']"); pg.wait_for_selector("text=Reply number 5"); pg.wait_for_timeout(500); state["fail"] = False
    check("failed regen: memory of the kept version is restored", deeds(pg) == [1, 2, 5], deeds(pg))
    # persistence across reload
    pg.reload(); pg.wait_for_selector(".cta"); pg.evaluate("go({n:'chat',id:DB.sessions[0].id})"); pg.wait_for_selector("text=Reply number 5")
    pg.click("button[aria-label='Previous version']"); pg.wait_for_selector("text=Reply number 4")
    check("reload: deltas persist and version switching still works", deeds(pg) == [1, 2, 4], deeds(pg))
    pg.click("button[aria-label='Next version']"); pg.wait_for_selector("text=Reply number 5")
    send(pg, "I go on.", 6); send(pg, "And on.", 7)
    check("more turns", deeds(pg) == [1, 2, 5, 6, 7], deeds(pg))
    # branch from the first AI reply (turn index 1)
    s = sess(pg); before_branch = json.dumps(s["mem"], sort_keys=True)
    pg.evaluate("branchAt(DB.sessions[0],1)"); pg.wait_for_timeout(300)
    check("branch: new branch keeps only memory up to the cut", deeds(pg, 1) == [1], deeds(pg, 1))
    check("branch: original playthrough memory untouched", json.dumps(sess(pg, 0)["mem"], sort_keys=True) == before_branch)
    check("branch: knowledge learned after the cut is gone", not sess(pg, 1)["mem"]["facts"] or all(not f["text"].startswith("hidden truth") for f in sess(pg, 1)["mem"]["facts"]))
    # delete a middle AI message (reply 5, the 3rd AI turn) in the original
    pg.evaluate("go({n:'chat',id:DB.sessions[0].id})"); pg.wait_for_selector("text=Reply number 7")
    s = sess(pg); ai_idx = [i for i, t in enumerate(s["turns"]) if t["role"] == "ai"]; i5 = ai_idx[2]
    old_t7 = [e["t"] for e in s["mem"]["events"] if "number 7" in e["text"]][0]
    pg.evaluate(f"turnMenu(DB.sessions[0],{i5})"); pg.click("button:text-is('Delete message')"); pg.click("text=Tap again to confirm"); pg.wait_for_timeout(300)
    s = sess(pg); new_t7 = [e["t"] for e in s["mem"]["events"] if "number 7" in e["text"]][0]
    check("delete: removed message's event is gone", deeds(pg) == [1, 2, 6, 7], deeds(pg))
    check("delete: later events shift to their new turn index", new_t7 == old_t7 - 1 and s["turns"][new_t7]["text"].startswith("Reply number 7"), (old_t7, new_t7))
    # rewind to the first AI reply
    pg.evaluate("turnMenu(DB.sessions[0],1)"); pg.click("button:text-is('Rewind to here')"); pg.click("text=Tap again to confirm"); pg.wait_for_timeout(300)
    s = sess(pg)
    check("rewind: only the first reply's memory remains", deeds(pg) == [1], deeds(pg))
    check("rewind: knowledge and scene roll back", not any(f["text"].startswith("hidden truth") for f in s["mem"]["facts"]) and s["mem"]["scene"]["where"] == "hall 1", s["mem"].get("scene"))
    check("integrity check passes", pg.evaluate("SFMemory.integrity(DB.sessions[0].mem).ok") and pg.evaluate("SFMemory.integrity(DB.sessions[1].mem).ok"))

    # C. An older save (v30 shape, no memv2 key) loads, plays, and is not migrated unless the flag is on
    state["n"] = 0; pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("()=>{localStorage.clear();localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,memRecallDefault:false,modes:[{n:'Swift',id:'a/b',d:''}],mode:0,stories:[{id:'s1',kind:'story',title:'Old',setting:'x',entries:[],stats:[],endings:[],starts:[]}],sessions:[{id:'old1',storyId:'s1',char:{name:'Anna'},turns:[{role:'user',text:'hi',hide:true},{role:'ai',text:'Old reply.'}],chaps:[{i:0,t:'',sum:'Anna arrived.'}],facts:['Anna is a duchess.'],temp:'',mems:[],note:'',stats:{},len:'300',sugg:[],ended:[],cast:{Lenox:{r:'duke',t:['proud']}},updated:1}]}))}")
    pg.reload(); pg.wait_for_selector(".cta"); pg.evaluate("go({n:'chat',id:'old1'})"); pg.wait_for_selector("text=Old reply.")
    send(pg, "Hello.", 1); s = sess(pg)
    check("old save: plays with the engine off and is left unmigrated", "mem" not in s and s["facts"] == ["Anna is a duchess."])
    pg.evaluate("()=>{DB.memv2=true;save()}"); send(pg, "Again.", 2); s = sess(pg)
    check("old save + flag on: migrated on next reply, old fields untouched", "mem" in s and s["facts"] == ["Anna is a duchess."] and s["chaps"][0]["sum"] == "Anna arrived." and s["cast"]["Lenox"]["r"] == "duke")
    check("old save + flag on: legacy memory imported, new event added", any(f.get("legacy") for f in s["mem"]["facts"]) and deeds(pg) == [2], deeds(pg))
    br.close()
srv.terminate()
failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
print("ERRORS:", errs + failed); sys.exit(1 if failed or errs else 0)
