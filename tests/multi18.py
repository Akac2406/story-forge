import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","site"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time
from playwright.sync_api import sync_playwright
import menu_helper  # opens collapsible novel-menu categories for older tests (UI overhaul)
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8778","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
STUB="""(()=>{const st={speaking:false,pending:false,spoken:[],getVoices:()=>[],speak(u){this.spoken.push(u.text);setTimeout(()=>{u.onstart&&u.onstart()},5)},cancel(){},pause(){},resume(){}};Object.defineProperty(window,'speechSynthesis',{value:st,configurable:true});window.SpeechSynthesisUtterance=function(t){this.text=t;this.rate=1}})()"""
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]);ctx=b.new_context(viewport={"width":390,"height":844},device_scale_factor=2);ctx.add_init_script(STUB)
    pg=ctx.new_page();pg.set_default_timeout(12000);pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.goto("http://127.0.0.1:8778/index.html");pg.wait_for_selector(".cta")
    big=lambda k:"Chapter %d opens. *She* runs.\n\nSecond paragraph of chapter %d."%(k,k)
    turns=[{"role":"user","text":"Begin","hide":True},{"role":"ai","text":big(1)},{"role":"user","text":"I stand."},{"role":"ai","text":big(2)},{"role":"user","text":"I wait."},{"role":"ai","text":big(3)}]
    seed={"key":"k","modes":[{"n":"Swift","id":"a/b","d":""}],"mode":0,"migrated":True,"rec":False,"sessions":[{"id":"s1","storyId":"lib:naruto","start":"","follow":"strict","char":{"name":"Angelice","desc":"","trait":""},"turns":turns,"chaps":[{"i":0,"t":"The Ridge"},{"i":2,"t":"Nacht"},{"i":4,"t":"A Year On"}],"temp":"","mems":[],"note":"","stats":{},"upto":0,"len":"300","sugg":[],"ending":None,"ended":[],"updated":1}]}
    pg.evaluate("(d)=>{localStorage.clear();localStorage.setItem('story-forge-v2',JSON.stringify(d))}",seed);pg.reload();pg.wait_for_selector(".cta")
    pg.click("text=Continue");pg.click(".sessbtn");pg.wait_for_selector("#input")
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Listen to chapters')");pg.wait_for_selector(".sheet .chk")
    pg.click(".sheet .chk:has-text('Chapter 1') input");pass
    # now chapters 1 and 3 picked (3 was default)
    pg.screenshot(path=SP+"/ad-multi.png")
    pg.click(".sheet button:text-is('Read here')");pg.wait_for_selector("#player");time.sleep(.3)
    print("spoken:",pg.evaluate("speechSynthesis.spoken"));print("label:",pg.inner_text("#ptext"))
    b.close()
srv.terminate();print("ERRORS:",errs)
