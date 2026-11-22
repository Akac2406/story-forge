import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","story-forge-pwa"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time
from playwright.sync_api import sync_playwright
SP=sys.argv[1]
import time as _t
srv=subprocess.Popen([_sys.executable,"-m","http.server","8783","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);_t.sleep(1)
calls=[]
G1='''Ooh, **The Reincarnated Assassin is a Swordmaster**! Great choice. Here is what I know.

**World overview.** Raon Zieghart, once an assassin, is reborn into House Zieghart, one of the Six Kings. Wrath, a demon king fragment, lives inside him.

Now a few things before we start:

1. **Your role.** Original character, or someone from the story?

2. **Timeline.** Early arc in the annex?

3. **Reply length.** I suggest Long (~500 words).

[[META]]
WORLD: The Reincarnated Assassin is a Swordmaster, the continent of the Six Kings
CANON: The Reincarnated Assassin is a Swordmaster by Yu Jin-sung
ROLE: unknown
TIMELINE: unknown
GENRE: unknown
LENGTH: unknown
GOAL: unknown
RULES: none
READY: no
CONFIRMED: no'''
G2='''Perfect! Here is your preview.

Snow drifts over the annex training yard as the hired instructor arrives at the Zieghart gates. A red-eyed boy watches from the fence.

Does this look good? Say the word and we begin!

[[META]]
WORLD: The Reincarnated Assassin is a Swordmaster, the continent of the Six Kings
CANON: The Reincarnated Assassin is a Swordmaster by Yu Jin-sung
ROLE: An original character, a mysterious sword instructor recruited by House Zieghart shortly before Raon enters the annex
TIMELINE: Shortly before Raon enters the annex
GENRE: dark, action, rivalry
LENGTH: 500
GOAL: Earn the trust of House Zieghart
RULES: No one can read minds; Keep Wrath's voice snarky
READY: yes
CONFIRMED: no'''
G3='''Yay, here we go! The story is starting~

[[META]]
WORLD: The Reincarnated Assassin is a Swordmaster, the continent of the Six Kings
CANON: The Reincarnated Assassin is a Swordmaster by Yu Jin-sung
ROLE: An original character, a mysterious sword instructor recruited by House Zieghart shortly before Raon enters the annex
TIMELINE: Shortly before Raon enters the annex
GENRE: dark, action, rivalry
LENGTH: 500
GOAL: Earn the trust of House Zieghart
RULES: No one can read minds; Keep Wrath's voice snarky
READY: yes
CONFIRMED: yes'''
N1='''The gates of Zieghart groan open. "You're the new instructor?" Rimmer asks, yawning.

[[META]]
CAST: Rimmer | Light Wind instructor | messy hair | lazy, sharp, kind | curious
GOAL: Meet the annex children
DEAD: Old Gate Guard
NEXT: I bow. "Yes." | I look past him. "Where are the children?" | I say nothing.'''
def model(route):
    b=json.loads(route.request.post_data);calls.append(b);c=b["messages"][0]["content"]
    last=b["messages"][-1]["content"]
    if c.startswith("You are Quill"):
        txt=G3 if "start" in last.lower() and "yes" in last.lower() else (G2 if "original" in last.lower() else G1)
    elif "Summarize this interactive story" in b["messages"][-1]["content"]: txt="**Where things stand**\n- The instructor arrived at Zieghart."
    else: txt=N1
    if b.get("stream"):
        body="".join("data: "+json.dumps({"choices":[{"delta":{"content":txt[i:i+40]}}]})+"\n\n" for i in range(0,len(txt),40))+"data: "+json.dumps({"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":1000,"completion_tokens":200,"cost":0.001}})+"\n\ndata: [DONE]\n\n"
        route.fulfill(status=200,content_type="text/event-stream",body=body)
    else: route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":txt},"finish_reason":"stop"}],"usage":{"prompt_tokens":1000,"completion_tokens":200,"cost":0.001}}))
errs=[]
with sync_playwright() as p:
    br=p.chromium.launch(args=["--no-sandbox"]);pg=br.new_context(viewport={"width":390,"height":844},device_scale_factor=2).new_page();pg.set_default_timeout(12000)
    pg.on("pageerror",lambda e:errs.append(str(e)));pg.route("https://openrouter.ai/**",model)
    pg.goto("http://127.0.0.1:8783/index.html");pg.wait_for_selector(".cta")
    pg.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,modes:[{n:'Swift',id:'a/b',d:''}],mode:0,chars:[{id:'c1',name:'Angelice',desc:'White hair, silver eyes.',trait:''}]}))}");pg.reload();pg.wait_for_selector(".simcta")
    print("discover originals has sim card:",pg.locator(".card:has-text('World Simulator')").count())
    pg.click(".simcta");pg.wait_for_selector("text=Start setup with the guide");pg.screenshot(path=SP+"/sim-page.png")
    pg.click("text=Start setup with the guide");pg.wait_for_selector(".gname")
    print("welcome has commands:", "/impersonation" in pg.inner_text("#log"),"| status card:",pg.locator(".wstat").count(),"| placeholder:",pg.get_attribute("#input","placeholder"))
    pg.screenshot(path=SP+"/sim-welcome.png")
    pg.fill("#input","[long] Takes place in the webnovel “The reincarnated assassin is a swordmaster”");pg.click("button[aria-label='Send']");pg.wait_for_selector("text=World overview.")
    pg.wait_for_selector(".wstat >> text=Source work",state="detached") if False else None
    print("after 1: world:",pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).sessions[0].world"),"| start button:",pg.locator("text=Looks good, start the story").count())
    print("guide sys prompt has status:", "World Status so far" in calls[-1]["messages"][0]["content"])
    pg.fill("#input","I will be an original character, a mysterious sword instructor. Dark, action-focused tone.");pg.click("button[aria-label='Send']");pg.wait_for_selector("text=Looks good, start the story")
    print("card:",pg.locator(".wstat").last.inner_text().replace("\n"," | ")[:400])
    pg.screenshot(path=SP+"/sim-preview.png",full_page=False)
    pg.fill("#input","Yes, looks good, start!");pg.click("button[aria-label='Send']");pg.wait_for_selector("text=Rimmer asks")
    d=pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).sessions[0]")
    print("phase:",d["sim"]["ph"],"| turns:",len(d["turns"]),"| len:",d["len"],"| dead:",d.get("dead"),"| cast:",list(d.get("cast",{}).keys()),"| header:",pg.inner_text("header h1"))
    ns=calls[-1]["messages"][0]["content"]
    print("narrator prompt: canon:", "Base story: The Reincarnated Assassin is a Swordmaster by Yu Jin-sung" in ns,"| role:","The player’s role in this world: An original character" in ns,"| rules:","No one can read minds" in ns,"| preview:","Snow drifts over the annex" in ns,"| auto mode:","Narrative mode: Auto" in ns,"| DEAD line:","\nDEAD:" in ns)
    print("setup fold:",pg.locator(".simfold").inner_text())
    # commands
    pg.click("button[aria-label='Commands']");pg.wait_for_selector(".cmdrow");print("cmd rows:",pg.locator(".cmdrow b").all_inner_texts());pg.click(".sheethead >> text=Done") if pg.locator(".sheethead >> text=Done").count() else pg.keyboard.press("Escape")
    pg.evaluate("document.getElementById('sheetbg')&&document.getElementById('sheetbg').remove()")
    pg.fill("#input","/rule Wrath only talks to Raon");pg.click("button[aria-label='Send']");pg.wait_for_timeout(int(.3*1000))
    print("rules now:",pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).sessions[0].rules").replace("\n"," / "))
    n0=len(calls);pg.fill("#input","/impersonation stop moving my character");pg.click("button[aria-label='Send']");
    pg.wait_for_timeout(int(1*1000));print("impersonation regen sent:",len(calls)>n0,"| correction in prompt:","CORRECTION" in calls[-1]["messages"][0]["content"] and "stop moving my character" in calls[-1]["messages"][0]["content"],"| turns:",len(pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).sessions[0].turns")))
    pg.fill("#input","/ooc make the next scene at night");pg.click("button[aria-label='Send']");pg.wait_for_timeout(int(1*1000))
    print("ooc sent as:",[m["content"][:40] for m in calls[-1]["messages"] if m["role"]=="user"][-1])
    print("imp flag cleared:", "CORRECTION" not in calls[-1]["messages"][0]["content"])
    pg.fill("#input","/summary");pg.click("button[aria-label='Send']");pg.wait_for_selector("text=Save as a memory");pg.click("text=Save as a memory");print("memory saved:",pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).sessions[0].mems[0].t"))
    pg.evaluate("document.getElementById('sheetbg')&&document.getElementById('sheetbg').remove()")
    pg.fill("#input","/status");pg.click("button[aria-label='Send']");pg.wait_for_selector(".sheet h2:text-is('World Status')");pg.screenshot(path=SP+"/sim-status.png")
    print("status sheet dead chips:",pg.locator(".deadl button").all_inner_texts())
    br.close()
srv.terminate();print("ERRORS:",errs)
