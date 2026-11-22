"""v35 reliability tests: snapshot before the first memory migration, and regenerate that is
all-or-nothing (the original reply and its memory survive a regenerate that stops before the request).
Run: python tests/reliability_v35_browser.py   (prints "ERRORS: []" and exits 0 when everything passes)"""
import json, os, sys, subprocess, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.normpath(os.path.join(HERE, "..", "site"))
PORT = 8812
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
state = {"n": 0}; calls = []; results = []; errs = []
def check(name, cond, info=""):
    results.append((name, bool(cond))); print(("ok  " if cond else "FAIL"), name, "" if cond else info)
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"):
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- note"}, "finish_reason": "stop"}]}))
    calls.append(b); state["n"] += 1; n = state["n"]
    txt = (f"Reply number {n}. Kevin moves.\n\n[[META]]\nSTATS: Grit={10+n}\nCAST: Kevin | swordsman | - | calm | wary\nGOAL: goal {n}\n"
           f"EVENTS: 3 | action | Kevin | hall {n} | Kevin performs deed number {n} | Mira\nLEARNED: Mira: hidden truth number {n} (she overheard)\nSCENE: hall {n} | Kevin, Mira | night {n}")
    body = "data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5, "completion_tokens": 5, "cost": 0.5}}) + "\n\ndata: [DONE]\n\n"
    route.fulfill(status=200, content_type="text/event-stream", body=body)
OLD = """{key:'k',migrated:true,%s modes:[{n:'Swift',id:'a/b',d:''}],mode:0,
 stories:[{id:'s1',kind:'story',title:'Old Save',setting:'x',entries:[],stats:[{n:'Grit',v:10,min:0,max:100}],endings:[],starts:[]}],
 sessions:[{id:'old1',storyId:'s1',char:{name:'Anna'},turns:[{role:'user',text:'hi',hide:true},{role:'ai',text:'Old reply one.'},{role:'user',text:'I look.'},{role:'ai',text:'Old reply two.',ps:{Grit:10},st2:{Grit:12}}],
   chaps:[{i:0,t:'Arrival',sum:'Anna arrived.'}],facts:['Anna is a duchess.'],temp:'',mems:[{t:'Start',x:'She came home.'}],note:'',stats:{Grit:12},len:'300',sugg:['a','b'],ended:[],
   cast:{Lenox:{r:'duke',t:['proud']}},relationships:{Lenox:{type:'Rival',trust:40}},updated:1}]}"""
def sess(pg, i=0):
    live = pg.evaluate(f"JSON.parse(JSON.stringify(DB.sessions[{i}]))")
    stored = pg.evaluate(f"JSON.parse(localStorage.getItem('story-forge-v2')).sessions[{i}]")
    if json.dumps(live, sort_keys=True) != json.dumps(stored, sort_keys=True): STORE_MISMATCH.append(len(results))
    return live
STORE_MISMATCH = []
def load(pg, flag, extra=""):
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("async()=>{localStorage.clear();try{await new Promise(r=>{const q=indexedDB.deleteDatabase('story-forge');q.onsuccess=q.onerror=q.onblocked=()=>r()})}catch(e){}}")
    pg.evaluate("d=>localStorage.setItem('story-forge-v2',JSON.stringify(eval('('+d+')')))", OLD % (("memv2:true," if flag else "") + extra))
    pg.reload(); pg.wait_for_selector(".cta"); pg.evaluate("go({n:'chat',id:'old1'})"); pg.wait_for_selector("text=Old reply two.")
def send(pg, text, n): pg.fill("#input", text); pg.click("button[aria-label='Send']"); pg.wait_for_selector(f"text=Reply number {n}")
def regen_and_settle(pg):
    pg.click("button[aria-label='Regenerate']"); pg.wait_for_timeout(700)
KEYS = ("turns", "stats", "facts", "chaps", "sugg", "mem", "cast", "relationships", "ending")
def core(s): return json.dumps({k: s.get(k) for k in KEYS}, sort_keys=True)
with sync_playwright() as p:
    br = p.chromium.launch(args=["--no-sandbox"]); ctx = br.new_context(viewport={"width": 390, "height": 844}); pg = ctx.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)

    # ---------- 1. Snapshot before the first migration ----------
    state["n"] = 0; load(pg, True); before = sess(pg)
    send(pg, "Hello.", 1); s = sess(pg)
    snap = pg.evaluate("async()=>{const v=await idbGet('snap:old1:pre-mem');return v?JSON.parse(v):null}")
    check("snapshot: written before memory was added", snap is not None and s.get("memSnap", {}).get("ok") is True)
    check("snapshot: holds the playthrough exactly as it was before migration", snap and json.dumps(snap["session"], sort_keys=True) == json.dumps(before, sort_keys=True))
    check("snapshot: memory created only after the snapshot", "mem" in s and s["memSnap"]["at"] <= s["memAt"])
    send(pg, "Again.", 2)
    snap2 = pg.evaluate("async()=>JSON.parse(await idbGet('snap:old1:pre-mem'))")
    check("snapshot: never overwritten by later turns", json.dumps(snap2, sort_keys=True) == json.dumps(snap, sort_keys=True))
    ok = pg.evaluate("async()=>await memRestoreSnapshot('old1')"); r = sess(pg)
    check("snapshot: memRestoreSnapshot puts the original playthrough back", ok and json.dumps(r, sort_keys=True) == json.dumps(before, sort_keys=True))
    # snapshot failure keeps memory off, story still plays
    state["n"] = 0; load(pg, True)
    pg.evaluate("()=>{window.__realSet=idbSet;idbSet=()=>Promise.reject(new Error('disk full'))}")
    send(pg, "Hello.", 1); s = sess(pg)
    check("snapshot failure: memory is NOT added (no unprotected migration)", "mem" not in s and not s.get("memSnap"))
    check("snapshot failure: the story still plays normally", s["turns"][-1]["text"].startswith("Reply number 1"))
    pg.evaluate("()=>{idbSet=window.__realSet}")
    # flag off: no snapshot, no memory
    state["n"] = 0; load(pg, False); send(pg, "Hello.", 1)
    check("flag off: no snapshot and no memory", pg.evaluate("async()=>!(await idbGet('snap:old1:pre-mem'))") and "mem" not in sess(pg))

    # ---------- 2. Regenerate stopped before the request ----------
    for flag in (False, True):
        tag = "on" if flag else "off"
        state["n"] = 0; load(pg, flag, "budget:1,budgetStop:true,")
        send(pg, "Hello.", 1)           # the reply we will try to regenerate (cost 0.5, under budget)
        send(pg, "More.", 2)            # spend reaches $1.00, so the next request pauses
        before = sess(pg); n_calls = len(calls)
        regen_and_settle(pg); after = sess(pg)
        check(f"[{tag}] budget pause: no request was sent", len(calls) == n_calls)
        check(f"[{tag}] budget pause: original reply, stats, facts, chapters and memory unchanged", core(after) == core(before), "diff")
        check(f"[{tag}] budget pause: reply still shown", pg.locator("text=Reply number 2").count() == 1)
        regen_and_settle(pg); pg.wait_for_selector("text=Reply number 3")      # second tap goes over the budget on purpose
        s = sess(pg); last = s["turns"][-1]
        check(f"[{tag}] after a pause, regenerating works and keeps both versions", last["text"].startswith("Reply number 3") and len(last.get("vs", [])) == 2)
        if flag:
            ev = [e["text"] for e in s["mem"]["events"] if e["src"] == "meta"]
            check("[on] memory holds the new version only", any("number 3" in x for x in ev) and not any("number 2" in x for x in ev), ev)
            pg.click("button[aria-label='Previous version']"); pg.wait_for_selector("text=Reply number 2")
            ev = [e["text"] for e in sess(pg)["mem"]["events"] if e["src"] == "meta"]
            check("[on] switching back restores the original version's memory", any("number 2" in x for x in ev) and not any("number 3" in x for x in ev), ev)
        # missing key
        before = sess(pg); n_calls = len(calls)
        pg.evaluate("()=>{DB.key='';save()}"); regen_and_settle(pg); after = sess(pg)
        check(f"[{tag}] no API key: original reply and memory unchanged", len(calls) == n_calls and core(after) == core(before))
        pg.evaluate("()=>{DB.key='k';save()}")
        # Stop pressed during the pre-request steps (reference lookup)
        before = sess(pg); n_calls = len(calls)
        pg.evaluate("()=>{DB.refs=(DB.refs||[]).concat([{id:'rtest',name:'R',for:['old1'],n:1,w:1}]);window.__rp=refPick;refPick=async()=>{PRE.cancel=true;return''}}"); before = sess(pg)
        regen_and_settle(pg); after = sess(pg)
        pg.evaluate("()=>{refPick=window.__rp;DB.refs=DB.refs.filter(r=>r.id!=='rtest');save()}")
        check(f"[{tag}] Stop before the request: original reply and memory unchanged", len(calls) == n_calls and core(after) == core(before))
        # an error thrown while preparing the request
        before = sess(pg)
        pg.evaluate("()=>{window.__bm=buildMsgs;buildMsgs=()=>{buildMsgs=window.__bm;throw new Error('boom')}}")
        pg.click("button[aria-label='Regenerate']"); pg.wait_for_timeout(700); after = sess(pg)
        check(f"[{tag}] error before the request: original reply and memory unchanged", core(after) == core(before)); check(f"[{tag}] error before the request: the person is told", "earlier reply is kept" in pg.inner_text("#toast"))
        errs[:] = [e for e in errs if "boom" not in e]
        # /impersonation that is paused must not leak its correction into the next turn
        pg.evaluate("()=>{DB.budget=0.01;save()}"); view_ok = pg.evaluate("()=>{view.overOK=0;return 1}")
        pg.fill("#input", "/impersonation stop moving me"); pg.click("button[aria-label='Send']"); pg.wait_for_timeout(700)
        s = sess(pg)
        check(f"[{tag}] paused /impersonation: reply kept and no leftover correction", "imp" not in s and core(s) == core(after))
        pg.evaluate("()=>{DB.budget=0;save()}")
        nxt = state["n"] + 1; send(pg, "Next.", nxt)
        check(f"[{tag}] next normal turn has no stray correction", "CORRECTION" not in calls[-1]["messages"][0]["content"])
        if flag: check("[on] memory integrity after all of the above", pg.evaluate("SFMemory.integrity(DB.sessions[0].mem).ok"))
    br.close()
srv.terminate()
check("live data and saved copy always matched", not STORE_MISMATCH, STORE_MISMATCH)
failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
print("ERRORS:", errs + failed); sys.exit(1 if failed or errs else 0)
