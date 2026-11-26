"""Rewind restores the exact story state of the chosen reply (v116, Anna: "make sure everything resets during a rewind or deleting").
Plays five simulated replies that each change the status window, quests, goal, cast and bonds; records the state after each reply;
rewinds to reply 2 and compares; then deletes every message and checks the story is back to a fresh start. No network.
Run: python tests/rewind_exact_state_browser.py"""
import json, os, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site")
with socket.socket() as s:
    s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
N = {"n": 0}
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"):
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    N["n"] += 1; n = N["n"]
    txt = (f"Reply {n}. The snow keeps falling.\n\n[[META]]\nSTATUS: Age={n}; Curse={9 - n} strands\nQUESTS: +Quest number {n}\nGOAL: goal number {n}\n"
           f"CAST: Person{n} | helper | tall | calm, kind, brave | likes the player {n}\nBONDS: Person1={n * 10}\nENDING: none")
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: [DONE]\n\n")
STORY = {"id": "s1", "kind": "story", "title": "Twins", "setting": "A cold house.", "starts": [], "stats": [], "endings": [], "entries": []}
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "stories": [STORY], "sessions": []}
KEYS = "['status','quests','goal','cast','dead','relationships','stats']"
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(service_workers="block"); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    J = lambda e: pg.evaluate(e)
    J("play(getStory('s1'),{name:'Ann'})"); pg.wait_for_function("!busy&&DB.sessions.length===1&&DB.sessions[0].turns.length>=2")
    J("(()=>{const se=DB.sessions[0];se.statusOn=true;save();go({n:'chat',id:se.id});return null})()")
    snap = lambda: J(f"(()=>{{const se=DB.sessions[0],o={{}};{KEYS}.forEach(k=>{{o[k]=se[k]===undefined?null:JSON.parse(JSON.stringify(se[k],(key,x)=>key==='u'?undefined:x))}});return o}})()")
    states = {}
    for n in range(2, 6):
        J(f"send('Action {n}');null"); pg.wait_for_function(f"!busy&&DB.sessions[0].turns.filter(t=>t.role==='ai').length==={n}"); pg.wait_for_timeout(150)
        states[n] = snap()
    ok(states[5]["status"].get("Age") == "5" and len(states[5]["quests"]) >= 4 and states[5]["goal"] == "goal number 5", "five replies changed status, quests, goal and cast")
    ok(J("DB.sessions[0].turns.filter(t=>t.svBase).length") == 1, "one full snapshot, then only changes")
    # rewind to the second reply
    idx = J("DB.sessions[0].turns.map((t,i)=>t.role==='ai'?i:-1).filter(i=>i>=0)[1]")
    J(f"turnMenu(DB.sessions[0],{idx})"); pg.locator("button:has-text('Rewind to here')").click(); pg.locator("button:has-text('Tap again to confirm')").click(); pg.wait_for_timeout(200)
    after = snap()
    diff = {k: (after[k], states[2][k]) for k in after if after[k] != states[2][k]}
    ok(not diff, "after Rewind every tracked field equals the state right after reply 2" + ("" if not diff else ": " + json.dumps(diff)[:600]))
    # deleting only the last chapter undoes only that chapter's progress
    J("DB.sessions[0].chapN=0;null")
    for n in range(3, 6):
        J(f"send('More {n}');null"); pg.wait_for_function(f"!busy&&DB.sessions[0].turns.filter(t=>t.role==='ai').length==={n}"); pg.wait_for_timeout(150)
        if n == 3: before_ch2 = snap()
        if n == 4: J("(()=>{const se=DB.sessions[0];se.chaps=chapsOf(se).concat([{i:se.turns.length-2,t:''}]);fixCh(se);save();return null})()")
    ok(J("chapsOf(DB.sessions[0]).length") == 2, "the story now has two chapters")
    start = J("chapsOf(DB.sessions[0])[1].i")
    while J("DB.sessions[0].turns.length") > start:
        J("turnMenu(DB.sessions[0],DB.sessions[0].turns.length-1)"); pg.locator("button:has-text('Delete message')").click(); pg.locator("button:has-text('Tap again to confirm')").click(); pg.wait_for_timeout(60)
    after = snap(); diff = {k: (after[k], before_ch2[k]) for k in after if after[k] != before_ch2[k]}
    ok(not diff, "deleting chapter 2 brings back exactly the end of chapter 1 (status, quests, goal, cast, stats)" + ("" if not diff else ": " + json.dumps(diff)[:600]))
    ok(len(after["quests"]) >= 3 and after["status"], "chapter 1's progress is kept, not wiped")
    # delete every message from the end
    for _ in range(40):
        if not J("DB.sessions[0].turns.length"): break
        J("turnMenu(DB.sessions[0],DB.sessions[0].turns.length-1)"); pg.locator("button:has-text('Delete message')").click(); pg.locator("button:has-text('Tap again to confirm')").click(); pg.wait_for_timeout(60)
    se = J("DB.sessions[0]")
    ok(se["turns"] == [] and se["status"] == {} and se["quests"] == [] and not se.get("goal") and se["cast"] == {} and se["stats"] == {} and not (se.get("relationships") or {}), "deleting every message leaves a fresh start: " + json.dumps({k: se.get(k) for k in ("status", "quests", "goal", "cast", "relationships")})[:400])
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
