import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","site"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time
from playwright.sync_api import sync_playwright
import menu_helper  # opens collapsible novel-menu categories for older tests (UI overhaul)
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8776","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"])
    ctx=b.new_context(viewport={"width":390,"height":844},device_scale_factor=2);ctx.grant_permissions(["clipboard-read","clipboard-write"],origin="http://127.0.0.1:8776")
    pg=ctx.new_page();pg.set_default_timeout(15000);pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.goto("http://127.0.0.1:8776/index.html");pg.wait_for_selector(".cta")
    big=lambda k:("Chapter %d text. "%k)+("The rain came down over the ridge and *she* ran. \"Hold on,\" he said.\n\n"*120)
    turns=[{"role":"user","text":"Begin","hide":True},{"role":"ai","text":big(1)},{"role":"user","text":"I stand my ground."},{"role":"ai","text":big(2)},{"role":"user","text":"A year passes.","show":"A year passes."},{"role":"ai","text":big(3)}]
    seed={"key":"k","modes":[{"n":"Swift","id":"a/b","d":""}],"mode":0,"chars":[],"stories":[],"found":{},"migrated":True,"rec":False,"sessions":[{"id":"s1","storyId":"lib:naruto","start":"","follow":"strict","char":{"name":"Angelice","desc":"","trait":""},"turns":turns,"chaps":[{"i":0,"t":"The Ridge"},{"i":2,"t":"Nacht"},{"i":4,"t":"A Year On"}],"temp":"","mems":[],"note":"","stats":{},"upto":0,"len":"300","sugg":[],"ending":None,"ended":[],"updated":1}]}
    pg.evaluate("(d)=>{localStorage.clear();localStorage.setItem('story-forge-v2',JSON.stringify(d))}",seed);pg.reload();pg.wait_for_selector(".cta")
    pg.click("text=Continue");pg.click(".sessbtn");pg.wait_for_selector("#input")
    pg.click("button[aria-label='Menu']");print("drawer row:",pg.locator(".drow:has-text('Listen to chapters')").count());pg.click(".drow:has-text('Listen to chapters')");pg.wait_for_selector(".sheet .chk")
    print("default summary:",pg.locator(".sheet p.sub").nth(1).inner_text())
    pg.click(".sheet button:text-is('All')");print("all summary:",pg.locator(".sheet p.sub").nth(1).inner_text())
    pg.screenshot(path=SP+"/aa-listen-sheet.png")
    with ctx.expect_page() as np: pg.click(".sheet button:text-is('Open in Safari')")
    lp=np.value;lp.on("pageerror",lambda e:errs.append("LISTEN "+str(e)));lp.wait_for_selector("article h2")
    url=lp.url;print("link length:",len(url),"| compressed:","#z=" in url)
    print("page: title",lp.title(),"| h2s",lp.locator("article h2").all_inner_texts(),"| paragraphs",lp.locator("article p").count(),"| player lines",lp.locator("p.you").all_inner_texts())
    print("asterisks gone:","*" not in lp.inner_text("article"),"| meta:",lp.inner_text(".meta"))
    lp.set_viewport_size({"width":390,"height":844});lp.screenshot(path=SP+"/ab-listen-page.png")
    pg.uncheck(".sheet .chk:has-text('Include my messages') input");pg.click(".sheet button:text-is('Copy link')");time.sleep(.3)
    u=pg.evaluate("navigator.clipboard.readText()");lp2=ctx.new_page();lp2.goto(u);lp2.wait_for_selector("article h2");print("copied link works, player lines now:",lp2.locator("p.you").count())
    lp3=ctx.new_page();lp3.goto("http://127.0.0.1:8776/listen.html#z=garbage!!");time.sleep(.6);print("bad link:",lp3.inner_text("#err"))
    lp4=ctx.new_page();lp4.goto("http://127.0.0.1:8776/listen.html");time.sleep(.4);print("no link:",lp4.inner_text("#err"))
    b.close()
srv.terminate();print("ERRORS:",errs)
