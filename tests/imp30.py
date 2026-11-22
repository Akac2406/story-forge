import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","story-forge-pwa"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time as _t
from playwright.sync_api import sync_playwright
W=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8794","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);_t.sleep(1)
EXT={"title":"He Forgot Me and Fell for the Saint","author":"@ Yorune","tags":["#Fantasy","#Romance","#Amnesia","#Regret"],"description":"My husband came home from war. He remembers everyone but me—and loves the saint who saved him.\nPlay his grand duchess. Every humiliation goes into a ledger. When he remembers, he'll owe every line.",
 "characters":[{"name":"Lenox","age":"29","role":"Grand duke & husband","looks":"190cm, black hair","hook":"His body remembers what his mind forgot.","quote":"\"Expect nothing more from me.\""},{"name":"Lumia","age":"21","role":"The saint","looks":"160cm, silver hair","hook":"Her tears keep taking your place.","quote":"I'll leave. Unless he asks me to stay."},{"name":"Julian","age":"27","role":"Personal guard","looks":"black hair, silver streak, glasses","hook":"The one man who never leaves your side.","quote":"Only say the word, Your Highness."},{"name":"Adrian","age":"26","role":"Crown prince","looks":"silver hair, golden eyes","hook":"Half politics.","quote":"Divorce him. Leave the rest to me."},{"name":"Riette","age":"19","role":"Loyal maid","looks":"freckles, sharp tongue","hook":"She gets angry when you're too tired to.","quote":"My lady. She's crying again."}],
 "starts":["The Day He Returns"],"selected_start":"The Day He Returns","endings":"5 endings + 1 hidden","systems":"Regret Ledger · 7 memories · 5 evidence slots","counters":[{"name":"Memory","max":7},{"name":"Evidence","max":5}],"commands":["/Status","/Ledger","/Evidence","/Memory","/Summary"],
 "play_guide":"Play a grand duchess pushed aside for a saint. Counter schemes, recover memories, and decide what his regret is worth.","prologue":"A year of waiting ends with a carriage at the gates.\nLumia | \"Careful, Your Highness. I can manage.\"\nThe saint descends on his arm.\nLenox | \"Who is that?\"","info_panel":"📍 Veillard gates · Return day 1 | 🏰 Her place: Mistress of the House / 🧩 Memory 0/7 · 🗂 Evidence 0/5",
 "images":[{"shot":1,"shows":"prologue"},{"shot":3,"shows":"cover"},{"shot":4,"shows":"scene"},{"shot":5,"shows":"character","character":"Lenox"},{"shot":6,"shows":"character","character":"Lumia"},{"shot":7,"shows":"character","character":"Julian"},{"shot":8,"shows":"character","character":"Adrian"},{"shot":9,"shows":"character","character":"Riette"}]}
FILL={"setting":"The grand duchy of Veillard after the northern war.","style":"melodrama, slow-burn regret","rules":"The Regret Ledger records each humiliation. Memory rises when Lenox recovers a memory. Evidence rises with verified clues against Lumia.","starts":[{"name":"The Day He Returns","situation":"At the gates as his carriage arrives."},{"name":"The Welcome Banquet","situation":"Day 7."},{"name":"The Divorce Papers","situation":"A month later."}],
 "endings":[{"n":"Paid in Full","r":"SSR","c":"he remembers everything and the ledger is settled"},{"n":"A Life of My Own","r":"SR","c":"she leaves"},{"n":"Saint Exposed","r":"SR","c":"5 evidence"},{"n":"The Prince's Offer","r":"R","c":"accepts Adrian"},{"n":"Ashes","r":"N","c":"she gives up"},{"n":"(hidden) The Guard's Vow","r":"SSR","c":"chooses Julian"}],
 "counters":[{"name":"Memory","max":7},{"name":"Evidence","max":5}],"info":"📍 Place · Return day N | 🏰 Her place / 🧩 Memory n/7 · 🗂 Evidence n/5 / 🎯 Next event","notes":[{"k":"Regret Ledger","t":"A list of slights."}],"guide":""}
calls=[]
def model(route):
    b=json.loads(route.request.post_data);calls.append(b);c=b["messages"][0]["content"]
    if isinstance(c,list): return route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":"```json\n"+json.dumps(EXT)+"\n```"},"finish_reason":"stop"}]}))
    if "hidden setup" in c: return route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":json.dumps(FILL)},"finish_reason":"stop"}]}))
    last=b["messages"][-1]["content"]
    txt=('Ledger so far: 1. He called you a stranger.\n\n[[META]]\nCAST: none' if "/Ledger" in last else
     'Lenox looks away.\nLenox | "Expect nothing more from me."\nRiette bristles.\n\n[[META]]\nCAST: none\nINFO: 📍 Veillard gates · Return day 1 | 🏰 Mistress of the House / 🧩 Memory 1/7 · 🗂 Evidence 0/5\nCOUNTERS: Memory=1; Evidence=0')
    body="data: "+json.dumps({"choices":[{"delta":{"content":txt}}]})+"\n\ndata: "+json.dumps({"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":5}})+"\n\ndata: [DONE]\n\n"
    route.fulfill(status=200,content_type="text/event-stream",body=body)
errs=[]
with sync_playwright() as p:
    br=p.chromium.launch(args=["--no-sandbox"]);pg=br.new_context(viewport={"width":390,"height":844},device_scale_factor=2).new_page();pg.set_default_timeout(30000)
    pg.on("pageerror",lambda e:errs.append(str(e)));pg.route("https://openrouter.ai/**",model)
    pg.goto("http://127.0.0.1:8794/index.html");pg.wait_for_selector(".cta")
    pg.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,modes:[{n:'Swift',id:'a/b',d:''},{n:'Canon',id:'google/gemini-3.1-pro-preview',d:''}],mode:0,chars:[{id:'c1',name:'Angeline',desc:'Silver-blonde duchess',trait:''}]}))}");pg.reload();pg.wait_for_selector(".cta")
    pg.click("nav.tabs >> text=Create");pg.click("text=Import from screenshots")
    pg.set_input_files("input[type=file]",[f"{FIX}/shots/s{i}.png" for i in range(1,11)]);pg.wait_for_selector(".shots img >> nth=9")
    pg.click("text=Read screenshots");pg.wait_for_selector("text=Found",timeout=60000)
    vc=[c for c in calls if isinstance(c["messages"][0]["content"],list)][0];print("vision call: images",len(vc["messages"][0]["content"])-1,"| model",vc["model"])
    print("found:",pg.inner_text("main .sub >> nth=-2")[:200] if False else pg.locator("main p.sub").nth(2).inner_text()[:220])
    print("crop labels:",[pg.locator(".crops select").nth(k).input_value() for k in range(pg.locator(".crops select").count())])
    pg.screenshot(path=W+"/imp-review.png",full_page=True)
    pg.click("text=Build my story");pg.wait_for_selector("text=Edit story page",timeout=60000)
    fc=[c for c in calls if not isinstance(c["messages"][0]["content"],list) and "hidden setup" in c["messages"][0]["content"]][0];print("fill used model:",fc["model"])
    st=pg.evaluate("DB.stories[0]");print("story:",st["title"],"| starts:",len(st["starts"]),"| endings:",len(st["endings"]),"| counters:",st["ctr"],"| cast:",[(c["n"],bool(c.get("img"))) for c in st["cast0"]],"| cover:",bool(st.get("cover")),"| prologue img:",bool(st.get("proImg")),"| cmds:",[c["c"] for c in st["cmds"]])
    pg.wait_for_timeout(800);pg.screenshot(path=W+"/imp-page.png",full_page=True)
    pg.click("button:text-is('Start story')");pg.wait_for_selector(".turn.ai");pg.wait_for_timeout(600)
    print("opening is the prologue (no model call):",len([c for c in calls if c.get("stream")])==0,"| tag lines:",pg.locator("p.tagl").count(),"| info panel:",pg.locator(".infobox").count(),"| guide card:",pg.locator(".oguide").count(),"| prologue picture:",pg.locator("img.genimg").count())
    pg.screenshot(path=W+"/imp-play.png")
    pg.fill("#input","\"Lenox. It's me. Your wife.\"");pg.click("button[aria-label='Send']");pg.wait_for_function("document.querySelectorAll('.turn.ai').length>=2")
    sp=calls[-1]["messages"][0]["content"];print("prompt: counters:","Memory 0/7" in sp,"| INFO asked:","INFO:" in sp,"| tag format:","Name | " in sp,"| commands:","/Ledger" in sp,"| cast portraits seeded:",pg.evaluate("Object.keys(DB.sessions[0].cast)"))
    print("counters now:",pg.evaluate("DB.sessions[0].ctr"),"| info panels:",pg.locator(".infobox").count())
    pg.fill("#input","/Ledger");pg.click("button[aria-label='Send']");pg.wait_for_selector("text=Ledger so far");print("/Ledger shown as:",pg.locator(".turn.user").last.inner_text()[-20:],"| sent:",calls[-1]["messages"][-1]["content"][:60])
    pg.click("button[aria-label='Commands']");print("commands sheet:",pg.locator(".cmdrow b").all_inner_texts())
    pg.evaluate("document.getElementById('sheetbg').remove()");pg.click("button[aria-label='Menu']");pg.click(".drow:has-text('Characters')");print("portrait avatars:",pg.locator(".cav.img").count())
    br.close()
srv.terminate();print("ERRORS:",errs)
