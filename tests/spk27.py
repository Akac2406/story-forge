import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","site"));FIX=_os.path.join(HERE,"fixtures")
import sys,subprocess,time as _t
from playwright.sync_api import sync_playwright
srv=subprocess.Popen([_sys.executable,"-m","http.server","8787","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);_t.sleep(1)
errs=[]
with sync_playwright() as p:
    br=p.chromium.launch(args=["--no-sandbox","--autoplay-policy=no-user-gesture-required"]);pg=br.new_page();pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.add_init_script("navigator.audioSession={type:'auto'};window.speechSynthesis.speak=function(u){window.__spoke=(window.__spoke||0)+1};")
    pg.goto("http://127.0.0.1:8787/index.html");pg.wait_for_selector(".cta")
    pg.evaluate("ttsStart(['Hello there. This is a test of reading aloud.'],'test')")
    pg.wait_for_timeout(500)
    print("audioSession:",pg.evaluate("navigator.audioSession.type"),"| silent track playing:",pg.evaluate("SPK&&!SPK.paused"),"| spoke:",pg.evaluate("window.__spoke||0"))
    pg.evaluate("ttsStop()");print("after stop playing:",pg.evaluate("!SPK.paused"))
    pg.click("header button[aria-label='Settings']");print("setting shown:",pg.locator("text=Read aloud through the speaker").count())
    br.close()
srv.terminate();print("ERRORS:",errs)
