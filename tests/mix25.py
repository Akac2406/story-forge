import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","story-forge-pwa"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time as _t
from playwright.sync_api import sync_playwright
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8785","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);_t.sleep(1)
hits=[]
def mk(tag):
    def f(route):
        b=json.loads(route.request.post_data);hits.append((tag,b["model"],route.request.headers.get("authorization")));c=b["messages"][0]["content"]
        if "game master" in c: txt=json.dumps({"title":"W","setting":"S","starts":["a"],"style":"x","tag":"t","rules":"r","power":"Aura","known":"well"}) if "setting" in c and "starts" in c else '[{"k":"A","t":"B"}]'
        else: txt="ready"
        if b.get("stream"):
            body="data: "+json.dumps({"choices":[{"delta":{"content":"The gate opens.\n\n[[META]]\nCAST: none"}}]})+"\n\ndata: "+json.dumps({"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":5}})+"\n\ndata: [DONE]\n\n"
            return route.fulfill(status=200,content_type="text/event-stream",headers={"access-control-allow-origin":"*"},body=body)
        route.fulfill(status=200,content_type="application/json",headers={"access-control-allow-origin":"*"},body=json.dumps({"choices":[{"message":{"content":txt},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":5}}))
    return f
errs=[]
with sync_playwright() as p:
    br=p.chromium.launch(args=["--no-sandbox"]);pg=br.new_context(viewport={"width":390,"height":844}).new_page();pg.set_default_timeout(15000)
    pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.route("https://openrouter.ai/**",mk("openrouter"));pg.route("https://sf.example.workers.dev/**",mk("opencode"))
    pg.route("https://graphql.anilist.co/**",lambda r:r.fulfill(status=200,headers={"access-control-allow-origin":"*"},content_type="application/json",body='{"data":{"Page":{"media":[]}}}'));pg.route("https://openlibrary.org/**",lambda r:r.fulfill(status=200,headers={"access-control-allow-origin":"*"},content_type="application/json",body='{"docs":[]}'))
    pg.goto("http://127.0.0.1:8785/index.html");pg.wait_for_selector(".cta")
    pg.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({prov:'opencode',ocKey:'ock',ocProxy:'sf.example.workers.dev',migrated:true,modes:[{n:'Swift',id:'deepseek/deepseek-v4.1-flash',d:''}],mode:0}))}");pg.reload();pg.wait_for_selector(".cta")
    pg.click("header >> text=Settings");pg.wait_for_selector("text=OpenRouter key (optional")
    pg.click("button:has-text('Add a mode')");pg.wait_for_timeout(300);print('chk count:',pg.locator("label.chk:has-text('Run this mode on OpenRouter')").count(),'items:',pg.locator('.item').count());pg.locator("label.chk:has-text('Run this mode on OpenRouter instead')").last.click()
    pg.wait_for_function("document.querySelectorAll(\"input[placeholder='provider/model-id']\").length===1")
    pg.locator("input[placeholder='Name']").nth(1).fill("Canon");pg.fill("input[placeholder='provider/model-id']","google/gemini-3.1-pro")
    print("browse buttons:",pg.locator("button:text-is('Browse')").count())
    pg.locator("button:text-is('Test')").nth(2).click();pg.wait_for_timeout(600);print("test without key ->",pg.inner_text("#toast"))
    pg.fill("input[placeholder='sk-or-...']","sk-or-test");pg.locator("button:text-is('Test')").nth(2).click();pg.wait_for_timeout(600);print("test with key ->",pg.inner_text("#toast"),"| hit:",hits[-1][:2])
    pg.locator("button:text-is('Test')").nth(0).click();pg.wait_for_timeout(600);print("swift test ->",pg.inner_text("#toast"),"| hit:",hits[-1][:2])
    pg.click("button.back");pg.click(".cta");pg.wait_for_selector("text=Build with")
    pg.select_option("label.fld:has-text('Build with') select",index=1)
    pg.fill("input[placeholder^='Any anime']","An original world");pg.fill("input[placeholder^='Any anime']","");pg.fill("label.fld:has-text('Your idea') textarea","A floating archipelago")
    n=len(hits);pg.click("button:text-is('Build world')");pg.wait_for_selector(".hero",timeout=30000)
    print("build went to:",sorted(set((h[0],h[1]) for h in hits[n:])))
    pg.fill("input[placeholder='Your character’s name']","A");pg.click("button:text-is('Start story')");pg.wait_for_selector("text=The gate opens")
    print("play went to:",hits[-1][:2])
    br.close()
srv.terminate();print("ERRORS:",errs)
