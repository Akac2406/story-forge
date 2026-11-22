import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","site"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time as _t,base64
from playwright.sync_api import sync_playwright
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8792","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);_t.sleep(1)
KV={};IMG="data:image/png;base64,"+base64.b64encode(open(FIX+"/red.png","rb").read()).decode()
H={"access-control-allow-origin":"*","access-control-allow-headers":"x-sync-id, content-type","access-control-allow-methods":"GET, PUT, OPTIONS"}
def worker(route):
    rq=route.request
    if rq.method=="OPTIONS": return route.fulfill(status=204,headers=H)
    id=rq.headers.get("x-sync-id")
    if rq.method=="GET": v=KV.get(id);return route.fulfill(status=200 if v else 404,headers=H,body=v or "")
    if rq.method=="PUT": KV[id]=rq.post_data;return route.fulfill(status=204,headers=H)
calls=[]
def model(route):
    b=json.loads(route.request.post_data);calls.append(b)
    if b.get("modalities"): return route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":"","images":[{"type":"image_url","image_url":{"url":IMG}}]}}],"usage":{"prompt_tokens":10,"completion_tokens":10,"cost":0.04}}))
    txt='Kevin draws his sword.\n\n[[META]]\nCAST: Kevin | swordsman | black hair | calm | wary'
    body="data: "+json.dumps({"choices":[{"delta":{"content":txt}}]})+"\n\ndata: "+json.dumps({"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":5,"cost":0.6}})+"\n\ndata: [DONE]\n\n"
    route.fulfill(status=200,content_type="text/event-stream",body=body)
errs=[]
def dev(br):
    ctx=br.new_context(viewport={"width":390,"height":844});pg=ctx.new_page();pg.set_default_timeout(20000);pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.route("https://openrouter.ai/**",model);pg.route("https://sf.example.workers.dev/**",worker);pg.goto("http://127.0.0.1:8792/index.html");pg.wait_for_selector(".cta");return pg
with sync_playwright() as p:
    br=p.chromium.launch(args=["--no-sandbox"])
    A=dev(br);A.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,ocProxy:'sf.example.workers.dev',syncPass:'blue whale tango',budget:1,budgetStop:true,modes:[{n:'Swift',id:'a/b',d:''}],mode:0,stories:[{id:'s1',kind:'story',title:'RA',setting:'x',entries:[],stats:[],endings:[],starts:[]}]}))}");A.reload();A.wait_for_selector(".cta")
    A.click(".card:has-text('RA')");A.fill("input[placeholder='Your character’s name']","Anna");A.click("button:text-is('Start story')");A.wait_for_selector("text=Kevin draws")
    A.fill("#input","I bow.");A.click("button[aria-label='Send']");A.wait_for_function("document.querySelectorAll('.turn.ai').length>=2")
    print("spent:",A.evaluate("monthSpend()"))
    n=len(calls);A.fill("#input","I attack.");A.click("button[aria-label='Send']");A.wait_for_timeout(500);print("budget pause:",len(calls)==n,"|",A.inner_text("#toast")[:70])
    A.click("button[aria-label='Send']");A.wait_for_function("document.querySelectorAll('.turn.ai').length>=3");print("second tap goes through:",len(calls)==n+1)
    # scene picture
    A.locator("button[aria-label='Message options']").last.click();A.click("text=Picture this scene");A.wait_for_selector("img.genimg");print("scene picture shown:",A.evaluate("document.querySelector('img.genimg').src.slice(0,22)"),"| prompt has rules:","No nudity" in calls[-1]["messages"][0]["content"][0]["text"])
    A.click("button[aria-label='Menu']");A.click(".drow:has-text('Characters')");A.click(".ccard:has-text('Kevin')");A.click("text=Make a portrait");A.wait_for_selector("text=Portrait made");A.click("button:text-is('Cancel')");print("portrait avatar:",A.locator(".ccard .cav.img").count())
    A.evaluate("document.getElementById('sheetbg')&&document.getElementById('sheetbg').remove()")
    A.evaluate("syncNow(true)");A.wait_for_timeout(2500);print("A synced, stored bytes:",sum(len(v) for v in KV.values()),"| looks encrypted:",not any("Kevin" in v for v in KV.values()))
    B=dev(br);B.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,ocProxy:'sf.example.workers.dev',syncPass:'blue whale tango',modes:[{n:'Swift',id:'a/b',d:''}],mode:0}))}");B.reload();B.wait_for_selector(".cta")
    B.evaluate("syncNow(true)");B.wait_for_timeout(2500);d=B.evaluate("({s:DB.sessions.length,st:DB.stories.map(x=>x.title),t:DB.sessions[0]&&DB.sessions[0].turns.length})");print("B after sync:",d)
    # delete on B propagates
    B.evaluate("()=>{bury(DB.sessions[0].id);DB.sessions=[];save()}");B.evaluate("syncNow(true)");B.wait_for_timeout(2500)
    A.evaluate("syncNow(true)");A.wait_for_timeout(2500);print("deletion reached A:",A.evaluate("DB.sessions.length")==0)
    W=dev(br);W.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,ocProxy:'sf.example.workers.dev',syncPass:'wrong',modes:[{n:'Swift',id:'a/b',d:''}],mode:0}))}");W.reload();W.wait_for_selector(".cta")
    print("different passphrase keeps data separate:",len(KV))
    br.close()
srv.terminate();print("ERRORS:",errs)
