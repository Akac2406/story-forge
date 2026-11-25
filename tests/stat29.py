import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","site"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time as _t
from urllib.parse import urlparse,parse_qs
from playwright.sync_api import sync_playwright
import menu_helper  # opens collapsible novel-menu categories for older tests (UI overhaul)
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8790","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);_t.sleep(1)
calls=[];n=[0]
def model(route):
    b=json.loads(route.request.post_data)
    if not b.get("stream"): calls.append(b);return route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":"- Nurses work 12-hour shifts.\n- Charting is constant."},"finish_reason":"stop"}]}))
    calls.append(b);n[0]+=1
    txt="Mira smiles at you.\n\n[[META]]\nAGE: 18\nCAST: Mira | classmate | - | kind | friendly\nSTATUS: Level=3; Class=Student Nurse; Money=$120\nBONDS: Mira=+6\nQUESTS: +Pass the anatomy exam; +Find out who sent the letter\nTOPICS: nursing school; anatomy exam"
    if n[0]==2: txt="You pass.\n\n[[META]]\nAGE: 18\nSTATUS: unchanged\nBONDS: Mira=-2\nQUESTS: -Passed the anatomy exam\nTOPICS: none"
    body="data: "+json.dumps({"choices":[{"delta":{"content":txt}}]})+"\n\ndata: "+json.dumps({"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":5}})+"\n\ndata: [DONE]\n\n"
    route.fulfill(status=200,content_type="text/event-stream",body=body)
wq=[]
def wiki(route):
    q={k:v[0] for k,v in parse_qs(urlparse(route.request.url).query).items()};wq.append(q.get("srsearch") or q.get("page"))
    if q.get("list")=="search": body={"query":{"search":[{"title":"Nursing school"}]}} if "nursing" in q["srsearch"].lower() else {"query":{"search":[]}}
    else: body={"parse":{"title":"Nursing school","wikitext":"A '''nursing school''' trains nurses.\n== Curriculum ==\nAnatomy, pharmacology and clinical rotations."}}
    route.fulfill(status=200,content_type="application/json",headers={"access-control-allow-origin":"*"},body=json.dumps(body))
errs=[]
with sync_playwright() as p:
    br=p.chromium.launch(args=["--no-sandbox"]);pg=br.new_context(viewport={"width":390,"height":844}).new_page();pg.set_default_timeout(15000)
    pg.on("pageerror",lambda e:errs.append(str(e)));pg.route("https://openrouter.ai/**",model);pg.route("https://en.wikipedia.org/**",wiki)
    pg.goto("http://127.0.0.1:8790/index.html");pg.wait_for_selector(".cta")
    pg.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,modes:[{n:'Swift',id:'a/b',d:''}],mode:0}))}");pg.reload();pg.wait_for_selector(".cta")
    pg.click(".card:has-text('A Modern Life')");pg.fill("input[placeholder='Your character’s name']","Anna");pg.click("button:text-is('Begin life')");pg.wait_for_selector("text=Mira smiles")
    sp=calls[-1]["messages"][0]["content"];print("life prompt asks TOPICS/QUESTS/BONDS:","TOPICS:" in sp,"QUESTS:" in sp,"BONDS:" in sp,"| STATUS off by default:","STATUS:" not in sp)
    pg.wait_for_timeout(800)
    d=pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).sessions[0]")
    print("bond:",d["cast"]["Mira"].get("b"),"| quests:",[q["t"] for q in d.get("quests",[])],"| research:",[(r["q"],r.get("t"),r["x"][:30]) for r in d.get("rs",[])])
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Status and quests')");pg.click("label.chk:has-text('Status window')");pg.evaluate("document.getElementById('sheetbg').remove()")
    pg.fill("#input","I study hard.");pg.click("button[aria-label='Send']");pg.wait_for_selector("text=You pass")
    sp=calls[-1]["messages"][0]["content"];print("prompt has research:","nursing school" in sp.lower() and "clinical rotations" in sp,"| open threads:","Pass the anatomy exam" in sp,"| status asked:","STATUS:" in sp)
    d=pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).sessions[0]")
    print("after 2: bond",d["cast"]["Mira"]["b"],"| quests done:",[(q["t"],bool(q.get("done"))) for q in d["quests"]])
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Research')");pg.wait_for_selector("text=Deep research");pg.locator("button:text-is('Deep research')").first.click();pg.wait_for_selector("text=12-hour shifts");print("deep research ok, web plugin:",calls[-1].get("plugins"))
    pg.evaluate("document.getElementById('sheetbg').remove()");pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Characters')");print("bond bar shown:",pg.locator(".bond").count())
    br.close()
srv.terminate();print("ERRORS:",errs)
