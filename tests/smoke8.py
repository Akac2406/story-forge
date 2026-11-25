import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","site"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time
from playwright.sync_api import sync_playwright
import menu_helper  # opens collapsible novel-menu categories for older tests (UI overhaul)
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8769","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
calls=[];U={"prompt_tokens":1000,"completion_tokens":200,"cost":0.0012}
def sse(text):
    parts=[text[i:i+60] for i in range(0,len(text),60)]
    return "".join("data: "+json.dumps({"choices":[{"delta":{"content":p}}]})+"\n\n" for p in parts)+"data: "+json.dumps({"choices":[{"delta":{},"finish_reason":"stop"}],"usage":U})+"\n\ndata: [DONE]\n\n"
def handler(route):
    body=json.loads(route.request.post_data);calls.append(body);c=body["messages"][0]["content"]
    if not body.get("stream"):
        txt="1: Opening Moves\n2. Second Wind\n3: **Third Act**" if "numbered story excerpt" in c else "- note"
        route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":txt},"finish_reason":"stop"}],"usage":U}));return
    txt='She waits. "Well?" he asks. It was quiet. Nobody moved! Then the door opened.\n\nA second paragraph follows here.\n\n[[META]]\nSTATS: Chakra=12; Bonds=12; Renown=1\nENDING: none\nPEOPLE: none\nGOAL: none'+('\nCHAPTER: **The North Road**' if "CHAPTER:" in c else '')+'\nNEXT: Nod. "Yes." | Wait. "No." | Leave. "Later."'
    route.fulfill(status=200,content_type="text/event-stream",body=sse(txt))
errs=[]
def db(pg): return pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2'))")
STUB="""(()=>{const st={speaking:false,pending:false,spoken:[],canceled:0,getVoices:()=>[{voiceURI:'v1',name:'Test Voice',lang:'en-US'},{voiceURI:'v2',name:'Autre',lang:'fr-FR'}],
 speak(u){this.spoken.push({t:u.text,r:u.rate});this.speaking=true;setTimeout(()=>{u.onstart&&u.onstart()},5)},cancel(){this.canceled++;this.speaking=false},pause(){},resume(){}};
 Object.defineProperty(window,'speechSynthesis',{value:st,configurable:true});window.SpeechSynthesisUtterance=function(t){this.text=t;this.rate=1}})()"""
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"])
    ctx=b.new_context(viewport={"width":390,"height":844},device_scale_factor=2);ctx.add_init_script(STUB)
    pg=ctx.new_page();pg.set_default_timeout(12000)
    pg.on("pageerror",lambda e:errs.append("PAGEERROR "+str(e)))
    pg.on("console",lambda m:errs.append("CONSOLE "+m.text) if m.type=="error" else None)
    pg.route("https://openrouter.ai/**",handler)
    pg.goto("http://127.0.0.1:8769/index.html");pg.wait_for_selector(".cta")
    longtxt=lambda n:("The storm came down over the ridge. \"Run,\" she said. "*200)
    turns=[{"role":"user","text":"Begin","hide":True},{"role":"ai","text":longtxt(1)},{"role":"user","text":"I stand my ground."},{"role":"ai","text":longtxt(2)},{"role":"user","text":"I answer him."},{"role":"ai","text":longtxt(3)}]
    seed={"key":"sk-or-test","modes":[{"n":"Swift","id":"a/b","d":""}],"mode":0,"chars":[],"stories":[],"found":{},"migrated":True,"sessions":[{"id":"s1","storyId":"lib:naruto","start":"","follow":"strict","char":{"name":"Angelice","desc":"","trait":""},"turns":turns,"temp":"","mems":[],"note":"","stats":{"Chakra":10,"Bonds":10,"Renown":0},"upto":0,"len":"300","sugg":[],"ending":None,"ended":[],"updated":1}]}
    pg.evaluate("(d)=>{localStorage.clear();localStorage.setItem('story-forge-v2',JSON.stringify(d))}",seed)
    pg.reload();pg.click("text=Continue");pg.click(".sessbtn");pg.wait_for_selector(".chead")
    print("chapters:",[t.replace("\n"," ") for t in pg.locator(".chead .chbtn").all_inner_texts()],"| visible replies:",pg.locator(".turn.ai").count())
    pg.screenshot(path=SP+"/s-chapters.png")
    pg.click("#ch0 .chbtn");print("after opening ch1, visible replies:",pg.locator(".turn.ai").count());pg.click("#ch0 .chbtn");print("after folding:",pg.locator(".turn.ai").count())
    pg.click("header h1");pg.wait_for_selector(".sheet .sessbtn");pg.click("text=Suggest titles");pg.wait_for_selector(".sheet .sessbtn:has-text('Opening Moves')")
    print("titled:",[t.replace("\n"," | ") for t in pg.locator(".sheet .sessbtn").all_inner_texts()])
    pg.click("button[aria-label^='Rename Chapter 2']");pg.fill(".sheet input[placeholder='Title for chapter 2']","Nacht Arrives");pg.click(".sheet .row.tight button:text-is('Done')")
    pg.screenshot(path=SP+"/t-chapsheet.png")
    pg.click(".sheet .sessbtn >> nth=0");pg.wait_for_selector("#ch0");time.sleep(.2)
    print("jumped: ch1 open",pg.locator("#ch0 .chbtn").get_attribute("aria-expanded"),"| scrollTop",pg.evaluate("document.querySelector('#log').scrollTop"),"| ch2 title:",pg.inner_text("#ch1 b"))
    # new chapter on send
    pg.fill("#input","I go north.");pg.click("button[aria-label='Send']");pg.wait_for_selector(".sg")
    d=db(pg)["sessions"][0];L=[x for x in calls if x.get("stream")][-1]["messages"][0]["content"]
    print("after send: chaps",d["chaps"],"| CHAPTER asked:","CHAPTER:" in L,"| headings:",pg.locator(".chead").count(),"| last heading:",pg.inner_text(".chead >> nth=-1").replace("\n"," "))
    pg.fill("#input","I keep going.");pg.click("button[aria-label='Send']");pg.wait_for_function("document.querySelectorAll('.turn.user').length>=2 && document.querySelector('.sg')")
    L=[x for x in calls if x.get("stream")][-1]["messages"][0]["content"];print("second send: CHAPTER asked:","CHAPTER:" in L,"| chaps:",len(db(pg)["sessions"][0]["chaps"]))
    pg.click("button[aria-label='Regenerate']");pg.wait_for_function("document.querySelector('.sg')");print("after regen chaps:",len(db(pg)["sessions"][0]["chaps"]),"| turns:",len(db(pg)["sessions"][0]["turns"]))
    pg.locator(".turn.user .dots").last.click();pg.click("text=Start a new chapter here");print("manual start:",[c["i"] for c in db(pg)["sessions"][0]["chaps"]])
    pg.locator(".turn.user .dots").last.click();pg.click("text=Join with the previous chapter");print("joined:",[c["i"] for c in db(pg)["sessions"][0]["chaps"]])
    # read aloud
    pg.locator("button[aria-label='Read this reply aloud']").last.click();pg.wait_for_selector("#player");time.sleep(.2)
    sp=pg.evaluate("speechSynthesis.spoken");print("reply chunks:",len(sp),"| first:",sp[0]["t"][:60],"| has META:",any("META" in x["t"] or "STATS" in x["t"] for x in sp),"| label:",pg.inner_text("#ptext"))
    pg.screenshot(path=SP+"/u-player.png")
    pg.click("button[aria-label='Pause reading']");print("paused label:",pg.inner_text("#ptext"));pg.click("button[aria-label='Resume reading']");time.sleep(.2);print("resumed label:",pg.inner_text("#ptext"))
    pg.click("button[aria-label='Reading speed']");time.sleep(.2);print("speed btn:",pg.inner_text("button[aria-label='Reading speed']"),"| last rate:",pg.evaluate("speechSynthesis.spoken.slice(-1)[0].r"))
    pg.click("button[aria-label='Stop reading']");print("player after stop:",pg.locator("#player").count())
    pg.evaluate("speechSynthesis.spoken=[]");pg.click("#ch0 .chsay");pg.wait_for_selector("#player");time.sleep(.2)
    sp=pg.evaluate("speechSynthesis.spoken");print("chapter read: chunks",len(sp),"| first:",sp[0]["t"],"| label:",pg.inner_text("#ptext")[:40]);pg.click("button[aria-label='Stop reading']")
    # drawer row
    pg.click("button[aria-label='Menu']");print("drawer chapters row:",pg.locator(".drow:has-text('Chapters'):not(:has-text('Listen'))").inner_text().replace("\n"," "));pg.click(".drow:has-text('Chapters'):not(:has-text('Listen'))");pg.wait_for_selector(".sheet .sessbtn");pg.click(".sheethead >> text=Done")
    # settings: voice + version + update
    pg.click("button.back");pg.click("text=Settings");pg.wait_for_selector("text=Reading aloud")
    print("voices:",pg.locator("label.fld:has-text('Voice') option").all_inner_texts(),"|",pg.locator("p.sub:has-text('version')").inner_text())
    pg.click("text=Check for update");pg.wait_for_selector("#toast.on");print("update toast:",pg.inner_text("#toast"))
    pg.route("**/index.html?v=*",lambda r:r.fulfill(status=200,content_type="text/html",body="<script>const VER=99;</script>"))
    with pg.expect_navigation(): pg.click("text=Check for update")
    pg.wait_for_selector(".cta");print("reloaded after update; stories kept:",len(db(pg)["sessions"]))
    print("overflow-x:",pg.evaluate("document.documentElement.scrollWidth>window.innerWidth"))
    b.close()
srv.terminate();print("ERRORS:",errs)
