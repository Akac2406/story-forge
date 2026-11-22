"""Checks the phone memory-trial page (memtrial.html) on an iPhone-sized screen. No real requests.
1. Dry run (built-in stand-in): full 40 turns, all operations, report shows DRY RUN.
2. "Live" path against a stand-in connector (page.route), confirm gate, OpenCode-only traffic.
3. Interrupt + resume, then Delete trial data.
Throughout: the real "story-forge-v2" localStorage and the real "story-forge" IndexedDB must be byte-identical.
"""
import json, os, re, subprocess, sys, time, socket
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "story-forge-pwa")
SCEN = json.load(open(os.path.join(APP, "trial", "scenario.json")))
PORT = 8791; BASE = f"http://127.0.0.1:{PORT}/"
CONN = "https://fake-connector.example"; FAKEKEY = "sk-test-NOTAREALKEY-1234567890abcdef"
REAL = {"migrated": True, "prov": "opencode", "ocKey": FAKEKEY, "ocProxy": CONN, "memv2": False,
        "stories": [{"id": "mine", "title": "My precious story", "kind": "story"}],
        "sessions": [{"id": "s-mine", "storyId": "mine", "turns": [{"role": "user", "text": "hello"}, {"role": "ai", "text": "my real reply"}]}]}
fails = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)

srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(50):
    try: socket.create_connection(("127.0.0.1", PORT), 0.2).close(); break
    except OSError: time.sleep(0.1)

CORS = {"access-control-allow-origin": "*", "access-control-allow-headers": "authorization, content-type, x-opencode-session", "access-control-allow-methods": "POST, OPTIONS"}
STATE = {"calls": 0, "seen": {}, "auth_ok": True, "models": set()}
def conn_reply(msgs):
    last = next((m["content"] for m in reversed(msgs) if m["role"] == "user" and isinstance(m["content"], str)), "")
    k = next((i for i, t in enumerate(SCEN["turns"]) if t["a"] in last), -1)
    v = STATE["seen"].get(k, 0); STATE["seen"][k] = v + 1
    T = SCEN["turns"][k] if k >= 0 else {"a": "The story opens.", "loc": ["hall"], "present": ["Corwin"]}
    loc = (T.get("loc") or ["hall"])[0]; pres = T.get("present") or ["Corwin"]
    ev = "none"
    if T.get("event"): ev = f"4 | action | Ilse, {pres[0]} | {loc} | Ilse {T['a'][2:].rstrip('.').lower()} ({T['event'][0]}{' v'+str(v) if v else ''}) | none"
    ln = "; ".join(f"{l['who']}: the deed shows Corwin sold the {l['kw']} rights to Vey (shown the copy)" for l in T.get("learn", [])) or "none"
    return f"Turn {k} reply. {T['a']} The scene moves on.\n\n[[META]]\nEVENTS: {ev}\nLEARNED: {ln}\nSCENE: {loc} | {', '.join(pres)} | day {k+2}\nNEXT: I wait. | I look. | I speak."
def conn_route(route):
    r = route.request
    if r.method == "OPTIONS": return route.fulfill(status=204, headers=CORS)
    STATE["calls"] += 1
    if r.headers.get("authorization") != "Bearer " + FAKEKEY: STATE["auth_ok"] = False
    b = json.loads(r.post_data); STATE["models"].add(b.get("model"))
    if not b.get("stream"):
        return route.fulfill(status=200, content_type="application/json", headers=CORS, body=json.dumps({"choices": [{"message": {"content": "- noted"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 50, "completion_tokens": 5}}))
    body = "data: " + json.dumps({"choices": [{"delta": {"content": conn_reply(b["messages"])}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5000, "completion_tokens": 400}}) + "\n\ndata: [DONE]\n\n"
    route.fulfill(status=200, content_type="text/event-stream", headers=CORS, body=body)

SNAP_JS = """async()=>{const ls=localStorage.getItem('story-forge-v2');
 const idb=await new Promise(r=>{const q=indexedDB.open('story-forge',1);q.onupgradeneeded=()=>q.result.createObjectStore('kv');
  q.onsuccess=()=>{const db=q.result,out={},tx=db.transaction('kv','readonly'),st=tx.objectStore('kv'),c=st.openCursor();
   c.onsuccess=()=>{const x=c.result;if(x){out[x.key]=JSON.stringify(x.value);x.continue()}else{db.close();r(JSON.stringify(out))}}}});
 return [ls,idb]}"""
SEED_JS = """async(d)=>{localStorage.setItem('story-forge-v2',JSON.stringify(d));
 await new Promise(r=>{const q=indexedDB.open('story-forge',1);q.onupgradeneeded=()=>q.result.createObjectStore('kv');
  q.onsuccess=()=>{const db=q.result,tx=db.transaction('kv','readwrite');tx.objectStore('kv').put('precious image bytes','img:abc');tx.objectStore('kv').put(d,'db');tx.oncomplete=()=>{db.close();r()}}})}"""

def wait_report(pg, secs):
    for _ in range(secs * 2):
        if pg.evaluate("!!window.__trialReport"): return True
        if "Stopped:" in (pg.text_content("#status") or ""): return False
        pg.wait_for_timeout(500)
    return False

with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pg = ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    hosts = []
    ctx.on("request", lambda r: hosts.append(re.sub(r"^https?://([^/]+).*", r"\1", r.url)))
    ctx.route("https://openrouter.ai/**", lambda r: (fails.append("OpenRouter request!"), r.abort()))
    ctx.route(CONN + "/**", conn_route)
    pg.goto(BASE + "index.html"); pg.wait_for_timeout(500)
    pg.evaluate(SEED_JS, REAL); pg.wait_for_timeout(200)
    before = pg.evaluate(SNAP_JS)

    # ---- 1. dry run ----
    pg.goto(BASE + "memtrial.html"); pg.wait_for_selector("text=OpenCode key and connector found")
    ok(pg.is_visible("#confirm"), "confirm box visible by default when a key is found")
    pg.click("text=Start trial"); pg.wait_for_timeout(300)
    ok(pg.is_visible("text=Type opencode to confirm.") and STATE["calls"] == 0, "Start without typing opencode is refused, nothing sent")
    pg.check("#dry"); pg.click("text=Start trial")
    done = wait_report(pg, 400)
    ok(done, "dry run finishes 40 turns")
    pr = pg.evaluate("JSON.parse(localStorage.getItem('sf-trial-progress'))")
    md = pg.evaluate("window.__trialReport||''")
    print(md[:1600])
    ok(STATE["calls"] == 0, "dry run sent nothing to the connector")
    ok(md.startswith("# Memory trial — DRY RUN") and "no requests were sent" in md, "dry-run report clearly labelled")
    ok(len(pr["rows"]) == 40 and not pr.get("fail"), "40 rows, no failed replies")
    ok(pr["ops"].get("regen_then_back_to_v1_restores_memory") is True and pr["ops"].get("regen_versions") == 3, "regen ×2 then back to v1 restores memory (3 versions)")
    ok(pr["ops"].get("branch_keeps_only_earlier_memory") is True and pr["ops"].get("branch_original_untouched") is True, "branch ops pass")
    ok(pr["ops"].get("cancel_keeps_reply_and_memory") is True, "cancel op passes")
    allc = [v for r in pr["rows"] for v in r["checks"].values()]
    ok(len(allc) > 60 and all(allc), f"all {len(allc)} per-turn checks pass with the clean stand-in")
    ok(pr["realUnchanged"] and pr["globalOff"], "page reports real data unchanged and memory off globally")
    ok(FAKEKEY not in md and FAKEKEY not in json.dumps(pr), "fake key absent from report")
    ok(not errs, "no page errors: " + "; ".join(errs[:3]))

    # ---- 2. live path against a stand-in connector ----
    pg.reload(); pg.wait_for_selector("text=Start trial")
    pg.fill("input[type=number] >> nth=0", "20"); pg.uncheck("#dry"); pg.fill("#confirm", "OpenCode")
    pg.click("text=Start trial")
    done = wait_report(pg, 400); ok(done, "connector run finishes 20 turns")
    pr = pg.evaluate("JSON.parse(localStorage.getItem('sf-trial-progress'))"); md = pg.evaluate("window.__trialReport||''")
    ok(md.startswith("# Memory trial — LIVE"), "connector report labelled LIVE (it would be real on the phone)")
    ok(STATE["calls"] >= 21 and STATE["auth_ok"], f"connector got {STATE['calls']} calls with the borrowed key")
    ok(STATE["models"] <= {"deepseek-v4.1-flash"}, "only deepseek-v4.1-flash requested: " + str(STATE["models"]))
    ok(set(pr["hosts"]) == {"connector"}, "requests by destination: connector only " + str(pr["hosts"]))
    ok(not any("openrouter" in h for h in hosts), "no request to openrouter.ai at network level")
    ok(FAKEKEY not in md and "fake-connector" not in md and FAKEKEY not in json.dumps(pr) and "fake-connector" not in json.dumps(pr), "key and connector redacted")
    ok(pr["ops"].get("regen_then_back_to_v1_restores_memory") is True, "regen op passes through the connector path")
    ok("go" in pr and isinstance(pr["go"].get("h"), (int, float)), "Go-limit estimate recorded " + str(pr.get("go")))

    # ---- 3. interrupt + resume ----
    pg.reload(); pg.wait_for_selector("text=Start trial")
    pg.fill("input[type=number] >> nth=0", "8"); pg.check("#dry"); pg.click("text=Start trial")
    for _ in range(120):
        pr = pg.evaluate("JSON.parse(localStorage.getItem('sf-trial-progress'))")
        if pr and pr["k"] >= 3: break
        pg.wait_for_timeout(250)
    pg.reload(); pg.wait_for_selector("text=Continue the unfinished trial")
    k0 = pg.evaluate("JSON.parse(localStorage.getItem('sf-trial-progress')).k")
    pg.click("text=Continue the unfinished trial"); done = wait_report(pg, 200)
    pr = pg.evaluate("JSON.parse(localStorage.getItem('sf-trial-progress'))")
    ok(done and len(pr["rows"]) == 8 and k0 >= 3, f"resumed from turn {k0 + 1} and finished all 8")
    pg.click("text=Delete trial data"); pg.wait_for_timeout(500)
    left = pg.evaluate("""async()=>[localStorage.getItem('sf-trial-db'),localStorage.getItem('sf-trial-progress'),(await indexedDB.databases()).map(d=>d.name)]""")
    ok(left[0] is None and left[1] is None and "sf-trial" not in left[2], "Delete trial data removes the trial copy " + str(left[2]))

    after = pg.evaluate(SNAP_JS)
    ok(after[0] == before[0], "real story-forge-v2 localStorage byte-identical")
    ok(after[1] == before[1] and "precious image bytes" in after[1], "real story-forge IndexedDB byte-identical")
    pg.goto(BASE + "index.html"); pg.wait_for_timeout(800)
    ok(pg.evaluate("DB.sessions.some(s=>s.id==='s-mine')&&!DB.sessions.some(s=>s.id==='trial')&&DB.memv2===false"), "real app still shows only the real story, memory off")
    br.close()
srv.terminate()
print("\n%d failure(s)" % len(fails)); print("ERRORS:", fails); sys.exit(1 if fails else 0)
