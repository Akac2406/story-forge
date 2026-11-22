import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","story-forge-pwa"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time as _t
from playwright.sync_api import sync_playwright
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8788","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);_t.sleep(1)
calls=[]
def model(route):
    b=json.loads(route.request.post_data);calls.append(b);m=b["messages"][-1]["content"]
    if isinstance(m,list):
        txt="A wolf-sized frost beast with a pale blue-white coat, two swept-back crystal horns of ice blue, and burning amber eyes. Its body is round and powerful, and a faint cold mist curls off its fur."
        return route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":txt},"finish_reason":"stop"}],"usage":{"prompt_tokens":900,"completion_tokens":60}}))
    txt='Frostmane stirs.\n\n[[META]]\nCAST: Frostmane | beast | - | loyal | bonded'
    body="data: "+json.dumps({"choices":[{"delta":{"content":txt}}]})+"\n\ndata: "+json.dumps({"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":5}})+"\n\ndata: [DONE]\n\n"
    route.fulfill(status=200,content_type="text/event-stream",body=body)
oc=[]
errs=[]
with sync_playwright() as p:
    br=p.chromium.launch(args=["--no-sandbox"]);pg=br.new_context(viewport={"width":390,"height":844},device_scale_factor=2).new_page();pg.set_default_timeout(15000)
    pg.on("pageerror",lambda e:errs.append(str(e)));pg.route("https://openrouter.ai/**",model)
    pg.route("https://sf.example.workers.dev/**",lambda r:(oc.append(1),model(r)))
    pg.goto("http://127.0.0.1:8788/index.html");pg.wait_for_selector(".cta")
    # OpenCode as main service, plus an OpenRouter key, like the user's setup
    pg.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({prov:'opencode',ocKey:'o',ocProxy:'sf.example.workers.dev',key:'k',migrated:true,modes:[{n:'Swift',id:'x',d:''}],mode:0,stories:[{id:'s1',kind:'story',title:'RA',setting:'House Zieghart',entries:[],stats:[],endings:[],starts:[]}],sessions:[{id:'e1',storyId:'s1',char:{name:'Angelice'},turns:[{role:'user',text:'hi',hide:true},{role:'ai',text:'Snow falls.'}],temp:'',mems:[],note:'I gain a magic beast in the future.',stats:{},len:'300',sugg:[],ended:[],cast:{}}]}))}");pg.reload();pg.wait_for_selector(".cta")
    pg.evaluate("go({n:'chat',id:'e1'})");pg.wait_for_selector("#log");pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Visual references')")
    pg.set_input_files(".sheet input[type=file]",FIX+"/beast.png");pg.wait_for_selector(".vprev")
    pg.select_option("label.fld:has-text('What it shows') select","creature")
    pg.fill("input[placeholder^='e.g. Frostmane']","Frostmane");pg.fill("label.fld:has-text('How it fits') textarea","The magic beast I gain later in the story")
    pg.screenshot(path=SP+"/vis-add.png")
    pg.click("text=Add and describe");pg.wait_for_function("document.querySelector('.vcard textarea')&&document.querySelector('.vcard textarea').value.length>20")
    vc=[c for c in calls if isinstance(c["messages"][-1]["content"],list)][0]
    print("describe call: model",vc["model"],"| has image:",vc["messages"][0]["content"][1]["image_url"]["url"][:23],"| went to OpenRouter not OpenCode:",len(oc)==0)
    pg.screenshot(path=SP+"/vis-card.png")
    pg.evaluate("document.getElementById('sheetbg').remove()")
    pg.fill("#input","I walk into the forest.");pg.click("button[aria-label='Send']");pg.wait_for_selector("text=Frostmane stirs")
    sp=[c for c in calls if not isinstance(c["messages"][-1]["content"],list)][-1]["messages"][0]["content"];i=sp.find("Visual references from the player")
    print("narrator via OpenCode:",len(oc)>0,"| visual refs in prompt:",i>=0);print(sp[i:i+700].replace("\n"," / "))
    pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Characters')");pg.wait_for_selector(".ccard");print("character card shows picture:",pg.locator(".ccard .cav.img").count())
    sz=pg.evaluate("localStorage.getItem('story-forge-v2').length");print("saved data size:",sz)
    br.close()
srv.terminate();print("ERRORS:",errs)
