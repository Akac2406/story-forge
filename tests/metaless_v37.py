"""v37 marker-less META tests: drives the real app in Chromium with stand-in model replies.
Run: python tests/memory_phase1_browser.py      (prints "ERRORS: []" and exits 0 when everything passes)"""
import json, os, sys, subprocess, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.normpath(os.path.join(HERE, "..", "site"))
PORT = 8813
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
    meta = f"\n\n" + ("[[META]]\n" if n % 3 == 0 else "") + f"CAST: Kevin | swordsman | - | calm | wary\nEVENTS: 3 | action | Kevin | hall {n} | Kevin performs deed number {n} | Mira"
    meta += (f"\nLEARNED: Mira: hidden truth number {n} (she overheard)" if n % 2 == 0 else "\nLEARNED: none")
    meta += f"\nSCENE: hall {n} | Kevin, Mira | night {n}"
    txt = f"Reply number {n}. Kevin moves." + meta + "\nNEXT: I draw my sword. | I call out to Mira. | I step back."
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
    for flag in (False, True):
        state["n"] = 0; start(pg, flag); wait_reply(pg, 1); send(pg, "I wait.", 2); send(pg, "I wait again.", 3)
        s = sess(pg); tag = "memory on" if flag else "memory off"
        shown = pg.inner_text("#log") if pg.query_selector("#log") else pg.inner_text("body")
        check(tag + ": metadata lines never shown in the story (no marker on replies 1-2)", "EVENTS:" not in shown and "SCENE:" not in shown and "NEXT:" not in shown and "CAST:" not in shown, shown[-400:])
        check(tag + ": stored reply text has no metadata", all("EVENTS:" not in t["text"] and "NEXT:" not in t["text"] for t in s["turns"]))
        check(tag + ": suggestions read from marker-less NEXT", len(s.get("sugg") or []) == 3, s.get("sugg"))
        check(tag + ": existing CAST handling works without marker", "Kevin" in (s.get("cast") or {}), list((s.get("cast") or {}).keys()))
        if flag:
            check("memory on: events from marker-less replies recorded", deeds(pg) == [1, 2, 3], deeds(pg))
            check("memory on: scene from marker-less reply", s["mem"]["scene"]["where"] == "hall 3")
            d = s.get("memDiag") or []
            check("memory on: diagnostics flag missing marker on replies 1-2 only", [bool(x.get("nm")) for x in d] == [True, True, False], [x.get("nm") for x in d])
    # prose that merely contains a capitalised label is left alone
    check("plain prose with a label is not cut", pg.evaluate("vis('He reads the sign.\\n\\nWARNING: keep out.')") == "He reads the sign.\n\nWARNING: keep out.")
    br.close()
srv.terminate()
print("ERRORS:", errs); bad = [n for n, ok in results if not ok]; print(f"{len(results)-len(bad)} passed, {len(bad)} failed"); sys.exit(1 if bad or errs else 0)
