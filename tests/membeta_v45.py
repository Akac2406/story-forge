"""v45 Story memory (beta) switch: drives the real app in Chromium with stand-in model replies.
Run: python tests/memory_phase1_browser.py      (prints "ERRORS: []" and exits 0 when everything passes)"""
import json, os, sys, subprocess, time
from playwright.sync_api import sync_playwright
import menu_helper  # opens collapsible novel-menu categories for older tests (UI overhaul)
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.normpath(os.path.join(HERE, "..", "site"))
PORT = 8843
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
SEED = lambda flag: "()=>{localStorage.clear();localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,%smodes:[{n:'Swift',id:'a/b',d:''}],mode:0,stories:[{id:'s1',kind:'story',title:'Ledger Test',setting:'A hall.',entries:[],stats:[],endings:[],starts:[]}]}))}" % ("memv2:true," if flag else "")
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
    state["n"] = 0; start(pg, False); wait_reply(pg, 1); send(pg, "I wait.", 2)
    pg.click("button[aria-label='Menu']"); pg.wait_for_selector("text=Story memory (beta)")
    check("menu shows Story memory (beta) as Off by default", "Off" in pg.inner_text("button.drow:has-text('Story memory (beta)')"))
    pg.click("button.drow:has-text('Story memory (beta)')"); pg.wait_for_selector("text=Try it on a copy")
    before = pg.evaluate("JSON.stringify(DB.sessions[0])")
    pg.click("button:text-is('Try it on a copy')"); pg.wait_for_timeout(500)
    ss = pg.evaluate("DB.sessions.map(s=>({id:s.id,memv2:!!s.memv2,rp:!!s.metaRepair,b:s.bname||'',n:s.turns.length,mem:!!s.mem}))")
    check("a copy is made with memory and fill-in on, named 'Memory test copy'", len(ss) == 2 and ss[1]["memv2"] and ss[1]["rp"] and ss[1]["b"] == "Memory test copy" and ss[1]["n"] == ss[0]["n"], ss)
    check("the original playthrough is byte-identical and memory stays off there", pg.evaluate("JSON.stringify(DB.sessions[0])") == before and not ss[0]["memv2"])
    check("memory still off globally", pg.evaluate("DB.memv2") is not True)
    send(pg, "I wait again.", 3)
    c = pg.evaluate("(()=>{const s=DB.sessions[1];return {snap:!!(s.memSnap&&s.memSnap.ok),ev:(s.mem&&s.mem.events||[]).filter(e=>e.src==='meta').length,diag:(s.memDiag||[]).length}})()")
    check("in the copy: a backup snapshot is taken first, then memory records the new reply", c["snap"] and c["ev"] >= 1 and c["diag"] >= 1, c)
    check("the original still has no memory after playing the copy", pg.evaluate("!DB.sessions[0].mem&&!DB.sessions[0].memv2"))
    pg.click("button[aria-label='Menu']"); pg.click("button.drow:has-text('Story memory (beta)')"); pg.wait_for_selector("text=Turn story memory off")
    check("sheet shows what has been remembered", "Remembered so far" in pg.inner_text("body"))
    pg.click("button:text-is('Turn story memory off')"); pg.wait_for_timeout(300)
    check("turning it off keeps what was remembered", pg.evaluate("DB.sessions[1].memv2===false&&!!DB.sessions[1].mem"))
    br.close()
srv.terminate()
print("ERRORS:", errs); bad = [n for n, ok in results if not ok]; print(f"{len(results)-len(bad)} passed, {len(bad)} failed"); sys.exit(1 if bad or errs else 0)
