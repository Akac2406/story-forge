import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","site"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time as _t,zipfile,io
from playwright.sync_api import sync_playwright
import menu_helper
SP=sys.argv[1];BOOK=sys.argv[2]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8791","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);_t.sleep(1)
calls=[]
def model(route):
    b=json.loads(route.request.post_data);calls.append(b)
    if not b.get("stream"): return route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":"You arrived at the academy and met Kevin."},"finish_reason":"stop"}]}))
    txt='Kevin says "Hello there" and walks off.\n\n[[META]]\nCAST: none'
    body="data: "+json.dumps({"choices":[{"delta":{"content":txt}}]})+"\n\ndata: "+json.dumps({"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":5}})+"\n\ndata: [DONE]\n\n"
    route.fulfill(status=200,content_type="text/event-stream",body=body)
errs=[]
with sync_playwright() as p:
    br=p.chromium.launch(args=["--no-sandbox"]);ctx=br.new_context(viewport={"width":390,"height":844},device_scale_factor=2,accept_downloads=True);pg=ctx.new_page();pg.set_default_timeout(30000)
    pg.on("pageerror",lambda e:errs.append(str(e)));pg.route("https://openrouter.ai/**",model)
    pg.add_init_script("window.__said=[];speechSynthesis.speak=function(u){window.__said.push([u.text,u.voice?u.voice.name:''])};")
    pg.goto("http://127.0.0.1:8791/index.html");pg.wait_for_selector(".cta")
    pg.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,modes:[{n:'Swift',id:'a/b',d:''}],mode:0}))}");pg.reload();pg.wait_for_selector(".cta")
    pg.click("nav.tabs >> text=Library");pg.set_input_files("input[type=file]",BOOK);pg.wait_for_selector(".sessbtn",timeout=60000)
    print("library row:",pg.inner_text(".sessbtn").replace("\n"," | "))
    bk=pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).books[0]");print("chapters:",bk["n"],"| first titles:",bk["chT"][:4])
    pg.click(".sessbtn");pg.wait_for_selector(".bookpage .body p");print("chapter 1 paragraphs:",pg.locator(".bookpage .body p").count(),"| title:",pg.inner_text(".bookpage .chead"))
    pg.click("text=Next ›");pg.wait_for_selector(".bookpage .body p");pg.evaluate("document.querySelector('#log').scrollTop=300");pg.wait_for_timeout(700)
    print("position saved:",pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).books[0].pos"))
    pg.screenshot(path=SP+"/book.png")
    pg.click("button[aria-label='Listen']");pg.click("text=This and the next 4");pg.click(".sheet button:text-is('Read here')");pg.wait_for_selector("#player");pg.wait_for_timeout(400)
    print("player:",pg.inner_text("#ptext"),"| spoken parts:",pg.evaluate("window.__said.length"))
    pg.evaluate("ttsStop()")
    pg.click("button[aria-label='Book menu']");pg.click("text=Start my own story in this book");pg.wait_for_selector("text=Build any world")
    print("builder src:",pg.input_value("input[placeholder^='Any anime']"),"| notice:",pg.locator(".notice").first.inner_text()[:80])
    print("ref attached:",pg.evaluate("view.b.refs.length"),"digest chars:",pg.evaluate("view.b.ref.length"))
    # export a story as epub
    pg.evaluate("()=>{DB.stories.push({id:'s1',kind:'story',title:'RA Story',setting:'x',entries:[],stats:[],endings:[],starts:[]});DB.sessions.push({id:'e1',storyId:'s1',char:{name:'Anna'},turns:[{role:'user',text:'I wave.'},{role:'ai',text:'Kevin waves back.\\n\\nThe sun sets.'}],chaps:[{i:0,t:'Arrival'}],temp:'',mems:[],note:'',stats:{},len:'300',sugg:[],ended:[],cast:{}});save()}")
    pg.evaluate("go({n:'chat',id:'e1'})");pg.wait_for_selector("#log");pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Export as EPUB')")
    with pg.expect_download() as dl: pg.click("button:text-is('Export as EPUB')")
    path=dl.value.path();z=zipfile.ZipFile(path);names=z.namelist();print("epub files:",names[:3],"... ok mimetype first:",names[0]=="mimetype","| chapter:",z.read("OEBPS/c1.xhtml").decode()[-160:])
    print("zip test:",z.testzip())
    # two voices
    pg.evaluate("DB.voice2='x';");print("dialogue split:",pg.evaluate("ttsParts('Kevin said \"Hello there.\" Then he left.').map(x=>x.charCodeAt(0)===2?'[D]'+x.slice(1):x)"))
    br.close()
srv.terminate();print("ERRORS:",errs)
