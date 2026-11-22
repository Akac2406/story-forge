import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","story-forge-pwa"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time
from playwright.sync_api import sync_playwright
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8777","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
calls=[];U={"prompt_tokens":100,"completion_tokens":50}
def h(route):
    b=json.loads(route.request.post_data);calls.append(b)
    if not b.get("stream"): return route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":"- a rival"},"finish_reason":"stop"}],"usage":U}))
    route.fulfill(status=200,content_type="text/event-stream",body="data: "+json.dumps({"choices":[{"delta":{"content":"You are born.\n\n[[META]]\nSTATS: Health=80\nENDING: none\nAGE: 30\nTIME: Spring\nEVENT: none\nPEOPLE: none\nGOAL: none\nNEXT: a | b | c"}}]})+"\n\ndata: [DONE]\n\n")
errs=[]
def db(pg): return pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2'))")
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"])
    pg=b.new_context(viewport={"width":390,"height":844},device_scale_factor=2).new_page();pg.set_default_timeout(12000)
    pg.on("pageerror",lambda e:errs.append(str(e)));pg.route("https://openrouter.ai/**",h)
    pg.goto("http://127.0.0.1:8777/index.html");pg.wait_for_selector(".cta")
    pg.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,rec:false,modes:[{n:'Swift',id:'a/b',d:''}],mode:0}))}");pg.reload();pg.wait_for_selector(".cta")
    pg.click(".card:has-text('A Modern Life')");pg.wait_for_selector("text=Begin life")
    pg.fill("input[placeholder='Your character’s name']","Angelice")
    def custom(label,val):
        f=pg.locator("label.fld:has-text('%s')"%label).first;f.locator("select").select_option("__c");f.locator("input").fill(val)
    custom("Trait","quietly ruthless when cornered");custom("Start your life at","30");custom("When in the world","The year 1995, in Seoul");custom("Reply length","1200")
    pg.screenshot(path=SP+"/ac-custom.png",full_page=True)
    print("custom boxes shown:",pg.locator("label.fld input[placeholder^='Describe a trait'], label.fld input[placeholder^='Age in years']").count())
    pg.click("text=Begin life");pg.wait_for_selector(".turn.ai")
    se=db(pg)["sessions"][0];c=[x for x in calls if x.get("stream")][-1]["messages"][0]["content"]
    print("session:",se["char"]["trait"],"|",se["start"],"|",se["len"],"| age:",se["life"]["age"])
    print("prompt: trait",("quietly ruthless" in c),"| start","The year 1995" in c,"| ~1200 words","about 1200 words" in c)
    pg.click("button[aria-label='Menu']");print("drawer length:",pg.locator(".drow:has-text('Length & depth')").inner_text().replace("\n"," "))
    pg.click(".drow:has-text('Length & depth')");print("depth heading:",pg.locator(".sheet h3").first.inner_text());pg.click(".sheethead >> text=Done")
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Generate ideas')")
    f=pg.locator(".sheet label.fld:has-text('What to create')");f.locator("select").select_option("__c");f.locator("input").fill("A rival who wants the same thing I do")
    pg.click(".sheet button:text-is('Generate')");time.sleep(.6);g=calls[-1]["messages"][0]["content"];print("custom idea task:","Create this for the story: A rival" in g);pg.click(".sheethead >> text=Done")
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Chapters')");f=pg.locator(".sheet label.fld:has-text('Start a new chapter')");f.locator("select").select_option("__c");f.locator("input").fill("2000");time.sleep(.2);print("chapN:",db(pg)["sessions"][0]["chapN"]);pg.click(".sheethead >> text=Done")
    # editor follow custom
    pg.click("button.back");pg.click("text=Create");pg.click("text=New story by hand");pg.fill("input[placeholder='e.g. The Lantern Road']","Test");pg.fill("input[placeholder='Leave empty for an original world']","Naruto")
    f=pg.locator("label.fld:has-text('How closely to follow it')");f.locator("select").select_option("__c");f.locator("input").fill("Follow canon, but I can save people");pg.click("header >> text=Save");pg.wait_for_selector(".hero")
    print("story follow:",db(pg)["stories"][0]["follow"],"| story page shows custom:",pg.locator("label.fld:has-text('How closely') input").input_value())
    # settings
    pg.click("button.back");pg.click("text=Settings");f=pg.locator("label.fld:has-text('Story text size')");f.locator("select").select_option("__c");f.locator("input").fill("18");time.sleep(.2)
    f=pg.locator("label.fld:has-text('Creativity')").first;f.locator("select").select_option("__c");f.locator("input").fill("1.3");time.sleep(.2)
    d=db(pg);print("fs:",d["fs"],"| creativity:",d["modes"][0]["t"])
    pg.reload();pg.wait_for_selector(".cta");pg.click("text=Settings");print("after reload, size box kept:",pg.locator("label.fld:has-text('Story text size') input").input_value(),"| select shows:",pg.locator("label.fld:has-text('Story text size') select").input_value())
    f=pg.locator("label.fld:has-text('Story text size')");f.locator("select").select_option("17");time.sleep(.2);print("back to preset:",db(pg)["fs"],"| box hidden:",not f.locator("input").is_visible())
    print("overflow-x:",pg.evaluate("document.documentElement.scrollWidth>window.innerWidth"))
    b.close()
srv.terminate();print("ERRORS:",errs)
