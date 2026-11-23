import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","site"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time
from playwright.sync_api import sync_playwright
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8767","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(1)
calls=[];gets=[];U={"prompt_tokens":1000,"completion_tokens":200,"cost":0.0012}
CAT=[{"id":"deepseek/deepseek-v4.1-flash","name":"DeepSeek: DeepSeek V4.1 Flash","created":300,"context_length":1000000,"pricing":{"prompt":"0.0000000507","completion":"0.0000002028"}},
     {"id":"anthropic/claude-sonnet-5.5","name":"Anthropic: Claude Sonnet 5.5","created":200,"context_length":1000000,"pricing":{"prompt":"0.000002","completion":"0.00001"}},
     {"id":"z-ai/glm-5.3","name":"Z.ai: GLM 5.3","created":100,"context_length":1000000,"pricing":{"prompt":"0.0000000699","completion":"0.0000014"}},
     {"id":"openrouter/auto","name":"Auto Router","created":50,"pricing":{"prompt":"-1","completion":"-1"}}]
def sse(text):
    parts=[text[i:i+40] for i in range(0,len(text),40)]
    return "".join("data: "+json.dumps({"choices":[{"delta":{"content":p}}]})+"\n\n" for p in parts)+"data: "+json.dumps({"choices":[{"delta":{},"finish_reason":"stop"}],"usage":U})+"\n\ndata: [DONE]\n\n"
def handler(route):
    rq=route.request
    if rq.method=="GET":
        gets.append(rq.url);data=CAT[:2] if "category=roleplay" in rq.url else CAT
        route.fulfill(status=200,content_type="application/json",body=json.dumps({"data":data,"total_count":len(data),"links":{"next":None}}));return
    body=json.loads(rq.post_data);calls.append(body);first=body["messages"][0];c=first["content"];last=body["messages"][-1]["content"]
    if not body.get("stream"):
        if "single word" in c: txt="ready"
        elif "Condense these story notes" in c: txt="TITLE: **The Gate**\nMEMORY: The first gate opened over the harbor and everything changed."
        elif "game master" in c:
            if '"title"' in c: txt=json.dumps({"title":"Test Saga","known":"well","tag":"Mystery","setting":"A foggy city where you arrive as a stranger.","style":"gothic","power":"Sequence","rules":"Potions grant powers.","starts":["Before the story","Chapter one"]})
            elif "characters" in c: txt=json.dumps([{"k":"Klein Moretti","t":"A careful diviner."}])
            else: txt="[]"
        else: txt="- Met a neighbor\n- Started school"
        route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":txt},"finish_reason":"stop"}],"usage":U}));return
    if first["role"]!="system":
        route.fulfill(status=200,content_type="text/event-stream",body=sse("- Born in a border town"));return
    n=len([x for x in calls if x.get("stream") and x["messages"][0]["role"]=="system"])
    life="life simulator" in c
    txt='Her fingers find the railing. "We need to change the route," she says. *She does not look back.*\n\n[[META]]\nSTATS: '+('Health=80; Sequence=%d; Bonds=30; Reputation=2; Wealth=12; Happiness=65'%(3+n) if life else 'Chakra=%d; Bonds=12; Renown=1'%(10+n))+'\nENDING: none'+('\nAGE: %d\nTIME: Spring, early years\nEVENT: Started lessons'%(5+n) if life else '')+'\nPEOPLE: Minji = training partner, wary\nGOAL: Reach the north peak before winter\nNEXT: Nod, meeting her gaze. "Add two kilometers." | Look at Siwoo, then back. "Distance is easy." | Walk past her. "Distance isn\'t the problem."'
    route.fulfill(status=200,content_type="text/event-stream",body=sse(txt))
errs=[]
def db(pg): return pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2'))")
def sess(pg,i=-1): return db(pg)["sessions"][i]
def lastsys(): return [x for x in calls if x.get("stream") and x["messages"][0]["role"]=="system"][-1]
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"])
    ctx=b.new_context(viewport={"width":390,"height":844},device_scale_factor=2)
    pg=ctx.new_page();pg.set_default_timeout(15000)
    pg.on("pageerror",lambda e:errs.append("PAGEERROR "+str(e)))
    pg.on("console",lambda m:errs.append("CONSOLE "+m.text) if m.type=="error" else None)
    pg.route("https://openrouter.ai/**",handler)
    pg.goto("http://127.0.0.1:8767/index.html");pg.wait_for_selector(".cta")
    long_temp="\\n".join("- note number %d about the harbor and the gate and the long road north"%i for i in range(30))
    turns=",".join("{role:'user',text:'go %d'},{role:'ai',text:'Scene %d.'}"%(i,i) for i in range(11))
    pg.evaluate("""()=>{localStorage.clear();localStorage.setItem('story-forge-v2',JSON.stringify({key:'sk-or-test',modes:[{n:'Swift',id:'deepseek/deepseek-v4.1-flash',d:''},{n:'Grand',id:'anthropic/claude-sonnet-5.5',d:''}],mode:0,fs:17,globalNote:'',chars:[{id:'c1',name:'Aiko',desc:'courier',trait:''}],stories:[],found:{},migrated:true,sessions:[{id:'old1',storyId:'lib:naruto',start:'Chunin Exams arc',follow:'strict',char:{name:'Aiko',desc:'courier',trait:''},turns:[{role:'user',text:'Begin',hide:true},{role:'ai',text:'Old scene.'},%s],temp:'%s',mems:['Kakashi owes me ramen'],note:'',stats:{Chakra:10,Bonds:10,Renown:0},upto:0,len:'300',sugg:[],ending:null,ended:[],updated:1}]}))}"""%(turns,long_temp))
    pg.reload();pg.wait_for_selector(".cta")
    print("migrated mems:",sess(pg)["mems"])
    pg.click("text=Continue");pg.click(".sessbtn");pg.wait_for_selector("#log")
    print("layout: ai turns",pg.locator(".turn.ai").count(),"| askline",pg.locator(".askline").count(),"| acts(last)",pg.locator(".acts:not(.old) button").count(),"| bar buttons",pg.locator(".bar button").count())
    pg.fill("#input","hello");pg.click("button[aria-label='Send']");pg.wait_for_selector(".sg")
    print("suggestions:",[t.replace("\n"," ") for t in pg.locator(".sg .sgtext").all_inner_texts()],"| dlg spans",pg.locator(".sg .dlg").count())
    time.sleep(1.0)
    se=sess(pg);print("goal:",se["goal"],"| people:",se.get("cast"),"| archived memory:",se["mems"][0],"| mems:",len(se["mems"]),"| temp now:",se["temp"][:40].replace("\n"," / "))
    pg.screenshot(path=SP+"/h-chat.png")
    print("reply cost lines:",pg.locator(".spend").all_inner_texts())
    pg.click(".sg >> nth=1 >> button[aria-label='Edit this reply']");print("edit ->",pg.input_value("#input"))
    pg.fill("#input","");pg.click("button[aria-label='Add an action or thought']");pg.keyboard.type("nods");print("action ->",pg.input_value("#input"))
    pg.fill("#input","");pg.click("button[aria-label='Commands']");pg.click(".cmdrow:has-text('/ooc')");pg.keyboard.type("skip ahead");print("ooc ->",pg.input_value("#input"));pg.fill("#input","")
    pg.click("button[aria-label='Suggested replies on or off']");print("sugg off:",pg.locator(".sg").count());pg.click("button[aria-label='Suggested replies on or off']");print("sugg on:",pg.locator(".sg").count())
    pg.click(".sg >> nth=0 >> button[aria-label='Send this reply']");pg.wait_for_function("document.querySelectorAll('.turn.user').length>=13 && document.querySelector('.sg')")
    print("sent suggestion as:",pg.locator(".turn.user .body").last.inner_text())
    pg.click("button[aria-label='Regenerate']");pg.wait_for_function("document.querySelector('.sg')");print("regen ok, turns:",pg.locator(".turn").count())
    # drawer
    pg.click("button[aria-label='Menu']");pg.wait_for_selector(".drawer");pg.screenshot(path=SP+"/i-drawer.png")
    print("drawer rows:",[t.replace("\n"," ") for t in pg.locator(".drawer .drow").all_inner_texts()],"|",pg.inner_text(".spent"))
    pg.click(".drow:has-text('Play guide')");pg.wait_for_selector("text=How to play");pg.screenshot(path=SP+"/j-guide.png");pg.click(".sheethead >> text=Done")
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Avatars')");pg.wait_for_selector(".av");print("avatars:",pg.locator(".av").count(),"| current badge:",pg.locator(".badge").count())
    pg.click("text=New avatar");pg.fill(".sheet input[placeholder='Your character’s name']","Angelice");pg.fill(".sheet textarea","White hair, silver eyes.");pg.click("text=Save avatar");pg.wait_for_selector(".av:has-text('Angelice')")
    pg.click(".av:has-text('Angelice') .avmain");pg.screenshot(path=SP+"/k-avatars.png");print("now playing:",sess(pg)["char"],"| badge on:",pg.locator(".av.on b").inner_text());pg.click(".sheethead >> text=Done")
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('User notes')");pg.fill(".sheet textarea >> nth=0","No time skips without asking.");pg.click(".sheethead >> text=Done")
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Length & depth')");pg.wait_for_selector("input[aria-label='Thinking depth']")
    pg.evaluate("()=>{const e=document.querySelector(\"input[aria-label='Thinking depth']\");e.value='2';e.dispatchEvent(new Event('change'))}")
    pg.evaluate("()=>{const e=document.querySelector(\"input[aria-label='Reply length']\");e.value='2';e.dispatchEvent(new Event('change'))}")
    pg.screenshot(path=SP+"/l-depth.png");print("len/think:",sess(pg)["len"],sess(pg)["think"],"|",[t for t in pg.locator(".sheet h3").all_inner_texts()]);pg.click(".sheethead >> text=Done")
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Writing style')");pg.click(".opt:has-text('Punchy')");pg.screenshot(path=SP+"/m-style.png");print("style:",sess(pg)["wstyle"],"| preview heads:",pg.locator(".prev h3").all_inner_texts());pg.click(".sheethead >> text=Done")
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Memories')");pg.wait_for_selector(".pills");print("mem tabs:",pg.locator(".pills button").all_inner_texts())
    pg.click(".acc >> nth=0 >> button");pg.screenshot(path=SP+"/n-mem.png");print("open memory text:",pg.input_value(".acc textarea"))
    pg.click("text=Add a memory");pg.fill(".acc textarea","Minji hates heights.");pg.fill(".acc input","Minji")
    pg.click(".pills button:has-text('Short-term')");pg.click(".pills button:has-text('Characters')");print("characters tab button:",pg.locator(".sheet button:has-text('Open character profiles')").count())
    pg.click(".pills button:has-text('Goal')");print("goal box:",pg.input_value(".sheet textarea"));pg.click(".sheethead >> text=Done")
    pg.fill("#input","(OOC: slow down) I wait.");pg.click("button[aria-label='Send']");pg.wait_for_function("document.querySelector('.sg')")
    L=lastsys();sysm=L["messages"][0]["content"]
    print("prompt:",{k:(k in sysm) for k in ["Writing style for this session: Use short, hard","current goal: Reach the north peak","starts with OOC:","- Minji: Minji hates heights.","The Gate: The first gate","No time skips without asking","Player character: Angelice","about 500 words","GOAL: the player"]})
    print("request: reasoning",L.get("reasoning"),"| max_tokens",L["max_tokens"],"| temperature" , "temperature" in L)
    # mode sheet + settings models
    pg.click("button.pill:has-text('▾')");pg.wait_for_selector(".modebtn");print("mode sheet:",[t.replace("\n"," | ") for t in pg.locator(".modebtn").all_inner_texts()]);pg.click(".sheethead >> text=Done")
    pg.click("button.back");pg.click("text=Settings");pg.wait_for_selector("h2:text-is('Modes')");pg.screenshot(path=SP+"/o-settings.png",full_page=True)
    pg.click("text=Add a mode");pg.wait_for_function("document.querySelectorAll(\"input[placeholder='provider/model-id']\").length===3")
    pg.locator("button:text-is('Browse')").nth(2).click();pg.wait_for_selector(".mrow");print("catalog rp rows:",pg.locator(".mrow").count())
    pg.click(".pills button:has-text('All models')");pg.wait_for_function("document.querySelectorAll('.mrow').length===3");pg.screenshot(path=SP+"/p-catalog.png")
    print("catalog all rows:",[t.replace("\n"," | ") for t in pg.locator(".mrow").all_inner_texts()])
    pg.fill(".sheet input[placeholder='Search models']","glm");pg.click(".mrow");pg.wait_for_selector("h2:text-is('Modes')")
    d=db(pg);print("modes:",d["modes"],"| price keys:",sorted(d["price"].keys()),"| gets:",len(gets))
    pg.locator("button:text-is('Test')").nth(2).click();pg.wait_for_selector("#toast.on");time.sleep(.3);print("test toast:",pg.inner_text("#toast"))
    print("estimates shown:",pg.locator("small.sub:has-text('a reply')").all_inner_texts())
    pg.click("text=Manage avatars");pg.wait_for_selector(".av");print("settings avatars:",pg.locator(".av").count());pg.click(".sheethead >> text=Done")
    # life sim regression
    pg.click("button.back");pg.click(".card:has-text('Saltglass')");pg.select_option("label.fld:has-text('How to play') select","life");pg.click("text=Begin life");pg.wait_for_selector(".sg")
    print("life:",sess(pg)["life"],"| skips:",pg.locator(".skips button").count(),"| askline:",pg.locator(".askline").count())
    pg.get_by_role("button", name="Advance time").click()
    pg.locator(".sheet").get_by_role("button", name="Skip a year", exact=True).click()
    pg.wait_for_function("DB.sessions.at(-1).turns.some(turn => turn.worldDays === 365) && !busy")
    pg.screenshot(path=SP+"/q-life.png")
    pg.click("button[aria-label='Menu']");print("life drawer has timeline:",pg.locator(".drow:has-text('Life timeline')").count());pg.click(".drow:has-text('Life timeline')");pg.wait_for_selector(".tl");pg.click(".sheethead >> text=Done")
    # save money
    pg.click("button.pill:has-text('▾')");pg.click(".modebtn:has-text('Grand')")
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Save money')");pg.wait_for_selector(".sheet .modebtn")
    print("saver options:",[t.replace("\n"," | ") for t in pg.locator(".sheet .modebtn").all_inner_texts()])
    print("tips:",pg.locator(".sheet .memline").all_inner_texts());pg.screenshot(path=SP+"/r-saver.png")
    pg.click(".sheet .modebtn:has-text('Maximum')");pg.click(".sheet button:text-is('Switch')");pg.click(".sheet button:text-is('Turn off')")
    d=db(pg);print("after: saver",d.get("saver"),"| mode",d["mode"],"| sugg",d.get("sugg"),"| tips left:",pg.locator(".sheet .memline").all_inner_texts());pg.click(".sheethead >> text=Done")
    pg.fill("#input","I wait.");pg.click("button[aria-label='Send']");pg.wait_for_function("document.querySelectorAll('.spend').length>=3")
    sysm=lastsys()["messages"][0]["content"];print("lean prompt: PEOPLE asked",("PEOPLE:" in sysm),"| GOAL asked",("GOAL:" in sysm),"| NEXT asked",("NEXT:" in sysm),"| model",lastsys()["model"],"| sg shown",pg.locator(".sg").count())
    pg.click("button[aria-label='Suggested replies on or off']")
    # character chat regression
    pg.click("button.back");pg.click("text=Create");pg.click("text=New character");pg.fill("input[placeholder='Who you’ll talk to']","Mira");pg.fill("textarea >> nth=1","\"You're late.\"");pg.click("header >> text=Save");pg.wait_for_selector(".hero");pg.click("text=Start chat");pg.wait_for_selector(".turn.ai")
    print("character chat: who label",pg.locator(".turn.ai .who").inner_text(),"| askline:",pg.locator(".askline").count())
    print("overflow-x:",pg.evaluate("document.documentElement.scrollWidth>window.innerWidth"))
    b.close()
srv.terminate()
print("ERRORS:",errs)
