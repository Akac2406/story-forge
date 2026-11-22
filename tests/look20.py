import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","story-forge-pwa"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time
from playwright.sync_api import sync_playwright
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8780","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
calls=[];slow={"on":False}
REPLY='— Seoul · Late autumn, 2009 —\n\nThe rain had not stopped since the gate opened. A man in a grey coat stepped forward: **Baek Joon-ho**, guild scout.\n\n"You\'re lucky you\'re alive," Joon-ho said.\n\n*He thinks I can\'t feel it.*\n\n[QUEST]\nSurvive the gate break.\nReward: ??? · Failure: death\n\n**KRA-KOOM.**\n\n◆ ◆ ◆\n\n📱 Hana: are you coming home tonight?\n📱 Angelice: late. don\'t wait up\n\n"Lucky isn\'t the word," said Mira the nurse.\n\n[[META]]\nSTATS: Chakra=12; Bonds=14; Renown=1\nENDING: none\nCAST: Baek Joon-ho | Guild scout | grey coat, scar through one eyebrow | wary, dry humor, loyal | curious, doesn\'t trust you yet; Mira | Hospital nurse | - | kind, tired | warm\nGOAL: Get home\nNEXT: Nod. "Thanks." | Wait. "Why?" | Leave. "Later."'
def h(route):
    b=json.loads(route.request.post_data);calls.append(b)
    if not b.get("stream"): return route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":"- n"},"finish_reason":"stop"}]}))
    if slow["on"]: time.sleep(1.2)
    route.fulfill(status=200,content_type="text/event-stream",body="data: "+json.dumps({"choices":[{"delta":{"content":REPLY}}]})+"\n\ndata: [DONE]\n\n")
errs=[]
def db(pg): return pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2'))")
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]);ctx=b.new_context(viewport={"width":390,"height":844},device_scale_factor=2,has_touch=True)
    pg=ctx.new_page();pg.set_default_timeout(12000);pg.on("pageerror",lambda e:errs.append(str(e)));pg.route("https://openrouter.ai/**",h)
    pg.goto("http://127.0.0.1:8780/index.html");pg.wait_for_selector(".cta")
    big=lambda k:"\n\n".join("Chapter %d, paragraph %d. The storm came over the ridge."%(k,j) for j in range(40))
    turns=[{"role":"user","text":"Begin","hide":True},{"role":"ai","text":big(1)},{"role":"user","text":"I stand."},{"role":"ai","text":big(2)}]
    seed={"key":"k","modes":[{"n":"Swift","id":"a/b","d":""}],"mode":0,"migrated":True,"rec":False,"sessions":[{"id":"s1","storyId":"lib:naruto","start":"","follow":"strict","char":{"name":"Angelice","desc":"","trait":""},"turns":turns,"chaps":[{"i":0,"t":"The Ridge"},{"i":2,"t":"The River Gate"}],"chapN":1,"temp":"","mems":[],"note":"","stats":{"Chakra":10,"Bonds":10,"Renown":0},"people":{"Hana":"younger sister, close"},"upto":0,"len":"300","sugg":[],"ending":None,"ended":[],"updated":5}]}
    pg.evaluate("(d)=>{localStorage.clear();localStorage.setItem('story-forge-v2',JSON.stringify(d))}",seed);pg.reload();pg.wait_for_selector(".cta")
    print("continue card:",pg.locator(".contc").inner_text().replace("\n"," | "))
    print("people migrated to cast:",db(pg)["sessions"][0].get("cast"))
    pg.click(".contc");pg.wait_for_selector("#log .chead")
    print("title cards:",[t.replace("\n"," ") for t in pg.locator(".chbtn.tc").all_inner_texts()],"| dropcap bodies:",pg.locator(".dropcap").count())
    pg.evaluate("()=>{window.__typ=false;const o=new MutationObserver(()=>{if(document.querySelector('.typing'))window.__typ=true});o.observe(document.body,{childList:true,subtree:true})}")
    slow["on"]=True;pg.fill("#input","I look around.");pg.click("button[aria-label='Send']");pg.wait_for_function("window.__typ===true");print("typing indicator shown");slow["on"]=False
    pg.wait_for_selector(".newc");sm=[x for x in calls if x.get("stream")][-1]["messages"][0]["content"]
    print("prompt: formats",("Formatting:" in sm and "[STATUS]" in sm and "◆ ◆ ◆" in sm),"| cast in prompt:","Hana: with the player: younger sister" in sm,"| CAST asked:","CAST: only named" in sm)
    lb=pg.locator(".turn.ai .body").last
    print("rendered: stamp",lb.locator(".stamp").count(),"win",lb.locator(".win").count(),"sfx",lb.locator(".sfx").count(),"brk",lb.locator(".brk").count(),"msg",lb.locator(".msg").count(),"me-line",lb.locator(".msg .me").count(),"bold",lb.locator("b.nm").count(),"thought",lb.locator("em.th").count())
    cols=lb.locator(".dlg").evaluate_all("els=>els.map(e=>e.style.color)");print("speech colors:",cols)
    print("new character chip:",pg.inner_text(".newc"))
    cast=db(pg)["sessions"][0]["cast"];print("cast:",{k:(v["r"],v["t"],v["a"],v["ch"]) for k,v in cast.items()})
    pg.screenshot(path=SP+"/ae-formats.png")
    pg.click(".newc");pg.wait_for_selector(".ccard");pg.screenshot(path=SP+"/af-cast.png");print("cast cards:",pg.locator(".ccard").count(),"| highlighted:",pg.locator(".ccard.hl b").first.inner_text())
    pg.click(".ccard.hl");pg.fill(".sheet input[placeholder='e.g. Guild scout']","Guild scout, Hunters Guild");pg.click(".sheet button:text-is('Save')");time.sleep(.2);print("edited role:",db(pg)["sessions"][0]["cast"]["Baek Joon-ho"]["r"]);pg.click(".sheethead >> text=Done")
    # formats off
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Story formats')");pg.click(".sheet .chk:has-text('Status and quest') input");pg.click(".sheet .chk:has-text('Chapter title cards') input");pg.click(".sheethead >> text=Done")
    print("after turning off windows/title cards: win",pg.locator(".turn.ai .body .win").count(),"| title cards",pg.locator(".chbtn.tc").count())
    # themes and layout
    pg.click("button.back");pg.click("text=Settings");pg.wait_for_selector("h2:text-is('Look')")
    for th in ["Paper","Ink","Moonlit","Ember","Sakura"]:
        pg.click(".opt:has-text('%s')"%th);time.sleep(.1)
    print("theme now:",pg.evaluate("document.documentElement.getAttribute('data-theme')"),"| bg:",pg.evaluate("getComputedStyle(document.body).backgroundColor"))
    pg.click(".opt:has-text('Paper')");pg.select_option("label.fld:has-text('Layout') select","novel")
    f=pg.locator("label.fld:has-text('Story font')");f.locator("select").select_option("book")
    pg.click(".chk:has-text('Show stats only when tapped') input");pg.click(".chk:has-text('Swipe left or right') input")
    pg.screenshot(path=SP+"/ag-settings.png",full_page=True)
    pg.click("button.back");pg.click(".contc");pg.wait_for_selector("#log .chead");time.sleep(.3)
    print("novel layout:",pg.evaluate("document.body.classList.contains('novel')"),"| statsmini:",pg.inner_text(".statsmini"),"| font:",pg.evaluate("getComputedStyle(document.querySelector('.body')).fontFamily")[:30])
    pg.screenshot(path=SP+"/ah-paper-novel.png")
    pg.click(".statsmini");print("stats opened:",pg.locator(".stats .stat").count())
    # swipe to previous chapter
    pg.evaluate("document.querySelector('#log').scrollTop=document.querySelector('#log').scrollHeight")
    box=pg.locator("#log").bounding_box();cx=box["x"]+box["width"]/2;cy=box["y"]+box["height"]/2
    pg.evaluate("([x,y])=>{const l=document.querySelector('#log');const mk=(t,cx)=>new TouchEvent(t,{bubbles:true,touches:t==='touchstart'?[new Touch({identifier:1,target:l,clientX:cx,clientY:y})]:[],changedTouches:[new Touch({identifier:1,target:l,clientX:cx,clientY:y})]});l.dispatchEvent(mk('touchstart',x-120));l.dispatchEvent(mk('touchend',x+60))}",[cx,cy]);time.sleep(.3)
    print("after swipe right: open chapters",[e.get_attribute("aria-expanded") for e in pg.locator(".chbtn").all()])
    # book mode
    pg.click("button[aria-label='Menu']");pg.click(".drawer .chk:has-text('Book mode') input");pg.mouse.click(20,400);time.sleep(.3)
    print("book mode: header visible",pg.locator("header").is_visible(),"| progress",pg.locator("#prog").is_visible(),"|",pg.inner_text("#bleft"))
    pg.screenshot(path=SP+"/ai-book.png")
    st0=pg.evaluate("document.querySelector('#log').scrollTop");pg.mouse.click(370,400);time.sleep(.7);st1=pg.evaluate("document.querySelector('#log').scrollTop");print("edge tap turned page:",st1!=st0)
    pg.mouse.click(195,420);time.sleep(.2);print("middle tap shows controls:",pg.locator("header").is_visible())
    print("overflow-x:",pg.evaluate("document.documentElement.scrollWidth>window.innerWidth"))
    b.close()
srv.terminate();print("ERRORS:",errs)
