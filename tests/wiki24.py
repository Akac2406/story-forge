import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","site"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time as _t
from urllib.parse import urlparse,parse_qs
from playwright.sync_api import sync_playwright
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8784","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);_t.sleep(1)
RAON="""{{Character Infobox
|image = Raon.png
|name = Raon Zieghart
|Age = 12
|Affiliation = [[House Zieghart]], [[Light Wind]]
|Weapon = Sword
}}
'''Raon Zieghart''' is the main protagonist of ''[[The Reincarnated Assassin is a Swordmaster]]''. He was formerly an assassin of [[Eden]].<ref>Chapter 1</ref>
== Appearance ==
Raon has red eyes and blond hair.
== Personality ==
Cold and calculating at first, he slowly learns warmth.
== Gallery ==
[[File:Raon2.png]]
== Trivia ==
* He loves food."""
wcalls=[];calls=[]
def wiki(route):
    u=urlparse(route.request.url);q={k:v[0] for k,v in parse_qs(u.query).items()};host=u.hostname;wcalls.append((host,q.get("action"),q.get("page") or q.get("srsearch") or q.get("cmtitle")))
    H={"access-control-allow-origin":"*"}
    if host!="reincarnated-assassin-is-a-swordmaster.fandom.com": return route.fulfill(status=404,headers=H,body="nope")
    if q.get("meta")=="siteinfo": body={"query":{"general":{"sitename":"Reincarnated Assassin Wiki","mainpage":"Main Page"},"statistics":{"articles":412}}}
    elif q.get("action")=="parse":
        p=q["page"]
        body={"parse":{"title":"Raon Zieghart","wikitext":RAON}} if p in("Raon Zieghart","Raon") else ({"parse":{"title":"Glenn Zieghart","wikitext":"'''Glenn''' is the Lord of [[House Zieghart]], Raon's grandfather.\n== Abilities ==\nSword of the Abyss."}} if p=="Glenn Zieghart" else {"error":{"info":"missing"}})
    elif q.get("list")=="search": s=q["srsearch"];body={"query":{"search":[{"title":"Raon Zieghart"}] if "Raon" in s or "Reincarnated" in s else ([{"title":"Glenn Zieghart"}] if "Glenn" in s else [])}}
    elif q.get("list")=="categorymembers": body={"query":{"categorymembers":[{"title":"Raon Zieghart"},{"title":"Glenn Zieghart"}]}}
    else: body={}
    route.fulfill(status=200,content_type="application/json",headers=H,body=json.dumps(body))
def sse(txt):return "".join("data: "+json.dumps({"choices":[{"delta":{"content":txt[i:i+50]}}]})+"\n\n" for i in range(0,len(txt),50))+"data: "+json.dumps({"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":10}})+"\n\ndata: [DONE]\n\n"
def model(route):
    b=json.loads(route.request.post_data);calls.append(b);c=b["messages"][0]["content"]
    if "game master" in c:
        if len([x for x in calls if "game master" in x["messages"][0]["content"]])==1:
            return route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":""},"finish_reason":"length"}]}))
        if '"setting"' in c or "setting" in c and "starts" in c: txt=json.dumps({"title":"Reincarnated Assassin","setting":"House Zieghart.","starts":["The annex"],"style":"dark","tag":"x","rules":"r","power":"Aura","known":"partly"})
        else: txt='[{"k":"Raon","t":"Hero."}]'
        return route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":txt},"finish_reason":"stop"}]}))
    if "How well do you know" in c: txt='{"known":"partly","covers":"a","gaps":"b"}';return route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":txt},"finish_reason":"stop"}]}))
    txt='Raon looks up. "Instructor," Glenn Zieghart says.\n\n[[META]]\nCAST: none\nNEXT: a | b | c'
    route.fulfill(status=200,content_type="text/event-stream",body=sse(txt))
errs=[]
with sync_playwright() as p:
    br=p.chromium.launch(args=["--no-sandbox"]);pg=br.new_context(viewport={"width":390,"height":844}).new_page();pg.set_default_timeout(15000)
    pg.on("pageerror",lambda e:errs.append(str(e)));pg.route("https://openrouter.ai/**",model);pg.route("**/*.fandom.com/**",wiki);pg.route("https://graphql.anilist.co/**",lambda r:r.fulfill(status=200,headers={"access-control-allow-origin":"*"},content_type="application/json",body='{"data":{"Page":{"media":[]}}}'));pg.route("https://openlibrary.org/**",lambda r:r.fulfill(status=200,headers={"access-control-allow-origin":"*"},content_type="application/json",body='{"docs":[]}'))
    pg.goto("http://127.0.0.1:8784/index.html");pg.wait_for_selector(".cta")
    pg.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,modes:[{n:'Swift',id:'a/b',d:''}],mode:0}))}");pg.reload();pg.wait_for_selector(".cta")
    pg.click(".cta");pg.fill("input[placeholder^='Any anime']","The Reincarnated Assassin is a Swordmaster by Yu Jin-sung (Web novel, 2023)")
    pg.click("text=Find automatically");pg.wait_for_selector(".wikibox small.ok");print("find:",pg.inner_text(".wikibox small"))
    pg.click("label:has-text('Look it up on the web') input") if False else None
    pg.click("button:text-is('Build world')");pg.wait_for_selector(".hero",timeout=30000)
    st=pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).stories[0]");print("built: wiki",st.get("wiki"),"| entries",len(st["entries"]))
    gm=[x for x in calls if "game master" in x["messages"][0]["content"]];print("retry after empty-thinking reply: max",gm[0].get("max_tokens"),"->",gm[1].get("max_tokens"),"| wiki extracts in build prompt:","Fan wiki extracts" in gm[1]["messages"][0]["content"] and "red eyes" in gm[1]["messages"][0]["content"])
    print("story page wiki box:",pg.inner_text(".wikibox small"))
    pg.fill("input[placeholder='Your character’s name']","Angelice");pg.click("button:text-is('Start story')");pg.wait_for_selector("text=Instructor")
    pg.fill("#input","I bow to Glenn Zieghart and look at Raon.");pg.click("button[aria-label='Send']");pg.wait_for_function("document.querySelectorAll('.turn.ai').length>=2")
    pg.wait_for_timeout(500)
    ns=calls[-1]["messages"][0]["content"];i=ns.find("Fan wiki notes")
    print("wiki notes in narrator prompt:",i>=0);print(ns[i:i+700].replace("\n"," / ") if i>=0 else "")
    print("cache keys:",pg.evaluate("Object.keys(JSON.parse(localStorage.getItem('sf-wiki'))['https://reincarnated-assassin-is-a-swordmaster.fandom.com'])"))
    n=len(wcalls);pg.fill("#input","I nod to Raon.");pg.click("button[aria-label='Send']");pg.wait_for_function("document.querySelectorAll('.turn.ai').length>=3");pg.wait_for_timeout(300)
    print("wiki requests on repeat turn (cached):",[w for w in wcalls[n:] if w[1]=="parse"])
    br.close()
srv.terminate();print("ERRORS:",errs)
