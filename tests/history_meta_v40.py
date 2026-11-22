"""v40 history keeps recent META: drives the real app in Chromium with stand-in model replies.
Run: python tests/memory_phase1_browser.py      (prints "ERRORS: []" and exits 0 when everything passes)"""
import json, os, sys, subprocess, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.normpath(os.path.join(HERE, "..", "site"))
PORT = 8815
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
    state["n"] = 0; start(pg, True); wait_reply(pg, 1)
    for k in range(2, 7): send(pg, f"I wait {k}.", k)
    msgs = [c for c in calls if c.get("stream")][-1]["messages"]
    asst = [m["content"] for m in msgs if m["role"] == "assistant"]
    withm = [("EVENTS:" in a) for a in asst]
    check("history: the last 3 replies carry their metadata, older ones don't", withm[-3:] == [True, True, True] and not any(withm[:-3]), withm)
    check("history: the metadata attached is that reply's own (deed numbers match)", all(f"deed number {n}" in a for a, n in zip(asst[-3:], [3, 4, 5])), [a[-160:] for a in asst[-3:]])
    s = sess(pg)
    check("stored reply text still has no metadata; it's kept separately in mt", all("EVENTS:" not in t["text"] for t in s["turns"]) and all(t.get("mt","").startswith(("[[META","CAST")) for t in s["turns"] if t["role"]=="ai"))
    check("nothing shows in the story", "EVENTS:" not in pg.inner_text("body"))
    pg.click("button[aria-label='Regenerate']"); wait_reply(pg, 7)
    v = sess(pg)["turns"][-1]
    check("regenerate: new version stores its own metadata", "deed number 7" in v.get("mt",""), v.get("mt","")[-80:])
    pg.click("button[aria-label='Previous version']"); pg.wait_for_timeout(300)
    v = sess(pg)["turns"][-1]
    check("version switch: metadata follows the version", "deed number 6" in v.get("mt",""), v.get("mt","")[-80:])
    send(pg, "I wait 8.", 8)
    msgs = [c for c in calls if c.get("stream")][-1]["messages"]; asst = [m["content"] for m in msgs if m["role"] == "assistant"]
    joined = "\n".join(asst)
    check("payload after a version switch: only the selected version's metadata, no duplicates", "deed number 6" in joined and "deed number 7" not in joined and joined.count("deed number 6") == 1, [a[-120:] for a in asst[-3:]])
    d = sess(pg).get("memDiag") or []
    check("diagnostics record how many earlier metadata blocks each request carried", d and d[-1].get("hm") == 3, [x.get("hm") for x in d])
    br.close()
srv.terminate()
print("ERRORS:", errs); bad = [n for n, ok in results if not ok]; print(f"{len(results)-len(bad)} passed, {len(bad)} failed"); sys.exit(1 if bad or errs else 0)
