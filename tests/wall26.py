import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","story-forge-pwa"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time as _t
from urllib.parse import urlparse,parse_qs
from playwright.sync_api import sync_playwright
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8786","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);_t.sleep(1)
PAGES={f"Page {i}":f"'''Page {i}''' is filler about farming number {i}.\n== Overview ==\nNothing about swords here, just crops and weather {i}." for i in range(120)}
PAGES["Raon Zieghart"]="{{Infobox\n|Age = 12\n}}\n'''Raon''' is the protagonist.\n== Abilities ==\nRing of Fire: a cultivation technique that burns away impurities."
PAGES["Ring of Fire"]="'''Ring of Fire''' is a cultivation technique from the Five Demons. It burns hot and is extremely painful for the user."
PAGES["Light Wind"]="'''Light Wind''' is a sword division of House Zieghart led by Raon, with Burren, Martha and Runaan."
wc=[];calls=[]
def wiki(route):
    u=urlparse(route.request.url);q={k:v[0] for k,v in parse_qs(u.query).items()};wc.append(q.get("list") or q.get("prop") or q.get("action"))
    H={"access-control-allow-origin":"*"}
    if q.get("meta")=="siteinfo": body={"query":{"general":{"sitename":"RA Wiki","mainpage":"Main Page"},"statistics":{"articles":123}}}
    elif q.get("list")=="allpages":
        t=sorted(PAGES)+["Main Page"];start=t.index(q["apcontinue"]) if q.get("apcontinue") else 0;part=t[start:start+100]
        body={"query":{"allpages":[{"title":x} for x in part]}};
        if start+100<len(t): body["continue"]={"apcontinue":t[start+100]}
    elif q.get("prop")=="revisions": body={"query":{"pages":[{"title":x,"revisions":[{"slots":{"main":{"content":PAGES.get(x,"#REDIRECT [[X]]")}}}]} for x in q["titles"].split("|")]}}
    else: body={"error":{"info":"missing"}}
    route.fulfill(status=200,content_type="application/json",headers=H,body=json.dumps(body))
def model(route):
    b=json.loads(route.request.post_data);calls.append(b)
    txt='Raon breathes and the Ring of Fire burns.\n\n[[META]]\nCAST: none'
    body="data: "+json.dumps({"choices":[{"delta":{"content":txt}}]})+"\n\ndata: "+json.dumps({"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":5}})+"\n\ndata: [DONE]\n\n"
    route.fulfill(status=200,content_type="text/event-stream",body=body)
errs=[]
with sync_playwright() as p:
    br=p.chromium.launch(args=["--no-sandbox"]);pg=br.new_context(viewport={"width":390,"height":844},device_scale_factor=2).new_page();pg.set_default_timeout(20000)
    pg.on("pageerror",lambda e:errs.append(str(e)));pg.route("https://openrouter.ai/**",model);pg.route("**/*.fandom.com/**",wiki)
    pg.goto("http://127.0.0.1:8786/index.html");pg.wait_for_selector(".cta")
    pg.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,modes:[{n:'Swift',id:'a/b',d:''}],mode:0,stories:[{id:'s1',kind:'story',title:'RA',canon:'The Reincarnated Assassin is a Genius Swordsman',setting:'House Zieghart',wiki:'https://ra.fandom.com',entries:[],stats:[],endings:[],starts:[]}]}))}");pg.reload();pg.wait_for_selector(".cta")
    pg.click(".card:has-text('RA')");pg.wait_for_selector("text=Download the whole wiki")
    pg.click("text=Download the whole wiki");pg.wait_for_selector("text=Whole wiki downloaded");print("status:",pg.locator(".wikibox small").last.inner_text())
    print("requests:",{k:wc.count(k) for k in set(wc)})
    r=pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).refs");print("ref:",[(x['name'],x['n'],x['for'],x.get('wiki')) for x in r])
    pg.screenshot(path=SP+"/wiki-dl.png")
    pg.goto("http://127.0.0.1:8786/index.html");pg.wait_for_selector(".cta");pg.click(".card:has-text('RA')");pg.wait_for_selector("text=Whole wiki downloaded");print("revisit:",pg.locator(".wikibox small").last.inner_text()[:80])
    pg.fill("input[placeholder='Your character’s name']","Angelice");pg.click("button:text-is('Start story')");pg.wait_for_selector("text=Ring of Fire burns")
    n=len(wc);pg.fill("#input","I ask Raon about the Ring of Fire technique and the Light Wind.");pg.click("button[aria-label='Send']");pg.wait_for_function("document.querySelectorAll('.turn.ai').length>=2");pg.wait_for_timeout(300)
    sp=calls[-1]["messages"][0]["content"];i=sp.find("[Fan wiki]")
    print("wiki passages in prompt:",sp.count("[Fan wiki]"),"| farming filler included:","farming" in sp,"| live per-turn lookups skipped:",len([x for x in wc[n:] if x=="parse"])==0)
    print(sp[i:i+400].replace("\n"," / "))
    br.close()
srv.terminate();print("ERRORS:",errs)
