import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","site"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time as _t
from playwright.sync_api import sync_playwright
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8789","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);_t.sleep(1)
calls=[];n=[0]
def model(route):
    b=json.loads(route.request.post_data)
    if not b.get("stream"): return route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":"- ok"},"finish_reason":"stop"}]}))
    calls.append(b);n[0]+=1
    txt=f"Reply number {n[0]}. Things happen.\n\n[[META]]\nSTATS: Chakra={10+n[0]}\nCAST: none"
    body="data: "+json.dumps({"choices":[{"delta":{"content":txt}}]})+"\n\ndata: "+json.dumps({"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":5}})+"\n\ndata: [DONE]\n\n"
    route.fulfill(status=200,content_type="text/event-stream",body=body)
errs=[]
with sync_playwright() as p:
    br=p.chromium.launch(args=["--no-sandbox"]);pg=br.new_context(viewport={"width":390,"height":844}).new_page();pg.set_default_timeout(15000)
    pg.on("pageerror",lambda e:errs.append(str(e)));pg.route("https://openrouter.ai/**",model)
    pg.goto("http://127.0.0.1:8789/index.html");pg.wait_for_selector(".cta")
    pg.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,modes:[{n:'Swift',id:'a/b',d:''}],mode:0,stories:[{id:'s1',kind:'story',title:'RA',setting:'House',entries:[],stats:[{n:'Chakra',v:10,min:0,max:100}],endings:[],starts:[]}]}))}");pg.reload();pg.wait_for_selector(".cta")
    pg.click(".card:has-text('RA')");pg.fill("input[placeholder='Your character’s name']","Angelice");pg.click("button:text-is('Start story')");pg.wait_for_selector("text=Reply number 1")
    print("anti-repetition rule:", "Never retell or re-describe" in calls[-1]["messages"][0]["content"])
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Story controls')");pg.locator("input[aria-label='Pacing']").fill("4");pg.select_option("label.fld:has-text('Replies per tap') select","2");pg.select_option("label.fld:has-text('Your character during') select","full")
    pg.evaluate("document.getElementById('sheetbg').remove()")
    pg.click("button[aria-label='Move the story on without my input']");pg.wait_for_selector("text=Reply number 3")
    last=calls[-1]["messages"];print("two replies per tap:",n[0]==3,"| advance msg:",last[-1]["content"][:70],"| full-auto wording:","act" in last[-1]["content"] and "dialogue" in last[-1]["content"],"| controls in prompt:","Pacing: Fast, skip ahead often" in last[0]["content"])
    print("hidden prompt not shown:",pg.locator("text=Move the story forward").count()==0)
    pg.click("button[aria-label='Continue the scene']");pg.wait_for_selector("text=Reply number 4");print("continue msg:",calls[-1]["messages"][-1]["content"][:60])
    pg.click("button[aria-label='Regenerate']");pg.wait_for_selector("text=Reply number 5");print("version switch:",pg.inner_text(".vsw"))
    pg.click("button[aria-label='Previous version']");pg.wait_for_selector("text=Reply number 4");d=pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).sessions[0]");print("swapped back: stats",d["stats"],"| text:",d["turns"][-1]["text"][:16])
    # branch from turn 1 (first ai reply)
    pg.locator(".turn.ai").first.locator("..").page.locator("button[aria-label='Message options']").first.click()
    pg.click("text=Mark as a save point");pg.wait_for_selector(".savept")
    pg.locator("button[aria-label='Message options']").first.click();pg.click("text=Branch from here");pg.wait_for_selector("text=New branch started")
    ss=pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).sessions");print("sessions:",len(ss),"| branch turns:",len(ss[1]["turns"]),"of",len(ss[0]["turns"]),"| name:",ss[1].get("bname"),"| stats at branch:",ss[1]["stats"])
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Save points')");print("save sheet:",pg.inner_text(".sheet").replace("\n"," | ")[:300])
    br.close()
srv.terminate();print("ERRORS:",errs)
