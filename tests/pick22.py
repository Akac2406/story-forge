import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","story-forge-pwa"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time
from playwright.sync_api import sync_playwright
SP=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8782","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
AL={"solo leveling":[{"type":"MANGA","format":"MANGA","countryOfOrigin":"KR","status":"FINISHED","startDate":{"year":2018},"title":{"romaji":"Na Honjaman Level Up","english":"Solo Leveling"},"popularity":289284,"staff":{"edges":[{"role":"Story (chs 1-92)","node":{"name":{"full":"So-Ryeong Gi"}}},{"role":"Original Story","node":{"name":{"full":"Chu-Gong"}}},{"role":"Art","node":{"name":{"full":"Seong-Rak Jang"}}}]}},
  {"type":"ANIME","format":"TV","countryOfOrigin":"JP","status":"FINISHED","startDate":{"year":2024},"title":{"romaji":"Ore dake Level Up na Ken","english":"Solo Leveling"},"popularity":463265,"staff":{"edges":[{"role":"Original Story","node":{"name":{"full":"Chu-Gong"}}},{"role":"Director","node":{"name":{"full":"Shunsuke Nakashige"}}}]}},
  {"type":"MANGA","format":"NOVEL","countryOfOrigin":"KR","status":"FINISHED","startDate":{"year":2016},"title":{"romaji":"Na Honjaman Level Up","english":"Solo Leveling"},"popularity":40000,"staff":{"edges":[{"role":"Story","node":{"name":{"full":"Chu-Gong"}}}]}}]}
calls=[]
def model(route):
    b=json.loads(route.request.post_data);calls.append(b);c=b["messages"][0]["content"]
    if "Identify the published works" in c: txt='```json\n[{"t":"The Author\'s POV","ty":"Web novel","a":"Entrail_JI","y":2021,"st":"Finished"}]\n```'
    elif "How well do you know" in c: txt='{"known":"partly" if False else "partly","covers":"main cast and early arcs","gaps":"later volumes and minor characters"}'.replace('"partly" if False else ','')
    else: txt="[]"
    time.sleep(.3);route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":txt},"finish_reason":"stop"}]}))
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]);pg=b.new_context(viewport={"width":390,"height":844},device_scale_factor=2).new_page();pg.set_default_timeout(12000)
    pg.on("pageerror",lambda e:errs.append(str(e)))
    def anilist(route):
        q=json.loads(route.request.post_data)["variables"]["s"].lower();route.fulfill(status=200,content_type="application/json",headers={"access-control-allow-origin":"*"},body=json.dumps({"data":{"Page":{"media":AL.get(q,[])}}}))
    pg.route("https://graphql.anilist.co/**",anilist);pg.route("https://graphql.anilist.co",anilist)
    pg.route("https://openlibrary.org/**",lambda r:r.fulfill(status=200,content_type="application/json",headers={"access-control-allow-origin":"*"},body=json.dumps({"docs":[{"title":"Nothing Man","author_name":["C. R. Howard"],"first_publish_year":2020},{"title":"Solo Leveling, Vol. 1 (novel)","author_name":["Chugong"],"first_publish_year":2021}]})))
    pg.route("https://openrouter.ai/**",model)
    pg.goto("http://127.0.0.1:8782/index.html");pg.wait_for_selector(".cta")
    pg.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,modes:[{n:'Swift',id:'a/b',d:''},{n:'Grand',id:'c/d',d:''}],mode:0}))}");pg.reload();pg.wait_for_selector(".cta")
    pg.click(".cta");pg.wait_for_selector("input[placeholder^='Any anime']")
    pg.type("input[placeholder^='Any anime']","solo leveling",delay=20);pg.wait_for_selector(".wprow b:text-is('Solo Leveling')")
    print("results:",[t.replace("\n"," | ") for t in pg.locator(".wprow").all_inner_texts()])
    pg.screenshot(path=SP+"/al-picker.png")
    pg.locator(".wprow").nth(2).click();pg.wait_for_selector(".rk:not(.wait)")
    print("card:",pg.inner_text(".wcard").replace("\n"," | "))
    rc=[x for x in calls if "How well do you know" in x["messages"][0]["content"]][-1];print("recall check used model:",rc["model"])
    pg.screenshot(path=SP+"/am-card.png")
    pg.click("button:text-is('Build world')");time.sleep(.6)
    bc=[x for x in calls if "game master" in x["messages"][0]["content"]];print("build source line:",bc[0]["messages"][0]["content"].split("\n")[1][:120] if bc else "none")
    # AI find for a web novel
    pg.click("button.back") if pg.locator(".hero").count() else None
    pg.goto("http://127.0.0.1:8782/index.html");pg.wait_for_selector(".cta");pg.click(".cta")
    pg.type("input[placeholder^='Any anime']","the author's pov",delay=20);pg.wait_for_selector(".wprow.ai")
    print("no-db results:",[t.replace("\n"," | ") for t in pg.locator(".wprow").all_inner_texts()])
    pg.click(".wprow.ai");pg.wait_for_selector(".wprow b:text-is(\"The Author's POV\")");print("AI found:",pg.locator(".wprow").first.inner_text().replace("\n"," | "))
    pg.locator(".wprow").first.click();pg.wait_for_selector(".rk:not(.wait)");print("card2 badge:",pg.inner_text(".rk"))
    # editor picker
    pg.goto("http://127.0.0.1:8782/index.html");pg.wait_for_selector(".cta");pg.click("text=Create");pg.click("text=New story by hand")
    pg.type("input[placeholder='Leave empty for an original world']","solo leveling",delay=20);pg.wait_for_selector(".wprow b");pg.locator(".wprow").first.click();pg.wait_for_selector(".rk:not(.wait)")
    print("editor canon:",pg.input_value("input[placeholder='Leave empty for an original world']"),"| badge:",pg.inner_text(".rk"))
    pg.fill("input[placeholder='e.g. The Lantern Road']","SL test");pg.click("header >> text=Save");pg.wait_for_selector(".hero")
    st=pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2')).stories[0]");print("saved canon:",st["canon"],"| known:",st.get("known"),"| notice on page:",pg.locator(".notice").count())
    b.close()
srv.terminate();print("ERRORS:",errs)
