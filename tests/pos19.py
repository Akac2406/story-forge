import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","story-forge-pwa"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time
from playwright.sync_api import sync_playwright
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8779","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
def h(route):
    b=json.loads(route.request.post_data)
    if not b.get("stream"): return route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":"- n"},"finish_reason":"stop"}]}))
    route.fulfill(status=200,content_type="text/event-stream",body="data: "+json.dumps({"choices":[{"delta":{"content":"NEW REPLY here.\n\n[[META]]\nSTATS: Chakra=1\nENDING: none\nPEOPLE: none\nGOAL: none\nNEXT: a | b | c"}}]})+"\n\ndata: [DONE]\n\n")
errs=[]
def db(pg): return pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2'))")
def enter(pg):
    pg.click("text=Continue");pg.click(".sessbtn");pg.wait_for_selector("#log .chead");time.sleep(.3)
def at(pg):
    return pg.evaluate("(()=>{const l=document.querySelector('#log');for(const el of l.querySelectorAll('[data-i]')){const y=el.offsetTop-l.offsetTop;if(y+el.offsetHeight>l.scrollTop)return [ +el.getAttribute('data-i'), Math.round(l.scrollTop-y), Math.round(l.scrollHeight-l.scrollTop-l.clientHeight)]}})()")
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]);pg=b.new_context(viewport={"width":390,"height":844}).new_page();pg.set_default_timeout(12000)
    pg.on("pageerror",lambda e:errs.append(str(e)));pg.route("https://openrouter.ai/**",h)
    pg.goto("http://127.0.0.1:8779/index.html");pg.wait_for_selector(".cta")
    big=lambda k:"\n\n".join("Chapter %d, paragraph %d. The storm came over the ridge and she ran."%(k,j) for j in range(60))
    turns=[{"role":"user","text":"Begin","hide":True},{"role":"ai","text":big(1)},{"role":"user","text":"I stand."},{"role":"ai","text":big(2)},{"role":"user","text":"I wait."},{"role":"ai","text":big(3)}]
    seed={"key":"k","modes":[{"n":"Swift","id":"a/b","d":""}],"mode":0,"migrated":True,"rec":False,"sessions":[{"id":"s1","storyId":"lib:naruto","start":"","follow":"strict","char":{"name":"A","desc":"","trait":""},"turns":turns,"chaps":[{"i":0,"t":"One"},{"i":2,"t":"Two"},{"i":4,"t":"Three"}],"chapN":1,"temp":"","mems":[],"note":"","stats":{},"upto":0,"len":"300","sugg":[],"ending":None,"ended":[],"updated":1}]}
    pg.evaluate("(d)=>{localStorage.clear();localStorage.setItem('story-forge-v2',JSON.stringify(d))}",seed);pg.reload();pg.wait_for_selector(".cta")
    enter(pg);print("first entry (no saved spot) -> at:",at(pg),"| arrows:",pg.locator(".chbtn .cn").all_inner_texts())
    pg.click("#ch0 .chbtn");time.sleep(.2)
    pg.evaluate("(()=>{const l=document.querySelector('#log');const el=l.querySelector('[data-i=\"1\"]');l.scrollTop=el.offsetTop-l.offsetTop+900})()");time.sleep(.6)
    before=at(pg);print("reading spot:",before,"| saved:",db(pg)["sessions"][0].get("pos"),"| och:",db(pg)["sessions"][0].get("och"))
    pg.click("button.back");time.sleep(.2);enter(pg);after=at(pg);print("after leaving and coming back:",after,"| ch1 open:",pg.locator("#ch0 .chbtn").get_attribute("aria-expanded"))
    pg.reload();pg.wait_for_selector(".cta");enter(pg);print("after closing the app:",at(pg))
    # fold the latest chapter
    pg.click("#ch2 .chbtn");time.sleep(.2);print("latest folded:",pg.locator("#ch2 .chbtn").get_attribute("aria-expanded"),"| visible turns:",pg.locator("#log [data-i]").count(),"| arrows:",pg.locator(".chbtn .cn").all_inner_texts())
    pg.click("#ch2 .chbtn");time.sleep(.2);print("latest reopened:",pg.locator("#ch2 .chbtn").get_attribute("aria-expanded"))
    pg.click("#ch2 .chbtn");time.sleep(.2)
    pg.fill("#input","Next.");pg.click("button[aria-label='Send']");pg.wait_for_function("document.body.innerText.includes('NEW REPLY')");time.sleep(.4)
    print("new reply on screen:",pg.evaluate("(()=>{const l=document.querySelector('#log'),r=l.getBoundingClientRect();const el=[...l.querySelectorAll('.turn.ai')].pop().getBoundingClientRect();return el.bottom>r.top&&el.top<r.bottom})()"));print("after sending: new chapter heading open:",pg.locator(".chead").last.locator(".chbtn").get_attribute("aria-expanded"),"| near bottom:",at(pg)[2]<60,"| saved spot cleared:", "pos" not in db(pg)["sessions"][0])
    x=at(pg);pg.click("button.back");enter(pg);print("re-enter after sending -> same spot:",at(pg)[:2]==x[:2])
    b.close()
srv.terminate();print("ERRORS:",errs)
