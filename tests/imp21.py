import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","site"));FIX=_os.path.join(HERE,"fixtures")
import json,sys,subprocess,time
from playwright.sync_api import sync_playwright
SP=sys.argv[1];BOOK=sys.argv[2]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8781","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
calls=[]
def h(route):
    b=json.loads(route.request.post_data);calls.append(b);c=b["messages"][0]["content"]
    if '"title"' in c: txt=json.dumps({"title":"Imported Saga","known":"partly","tag":"Fantasy","setting":"A world drawn from the imported book.","style":"epic","power":"Aether","rules":"Rules from the book.","starts":["Opening","Middle","End"]})
    elif "characters" in c: txt=json.dumps([{"k":"Ren","t":"A main character from the book."},{"k":"Kevin","t":"Another lead."}])
    elif "places" in c: txt=json.dumps([{"k":"The Lock","t":"A key place."}])
    else: txt=json.dumps([{"k":"Arc one","t":"First arc."}])
    route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":txt},"finish_reason":"stop"}]}))
errs=[]
def db(pg): return pg.evaluate("JSON.parse(localStorage.getItem('story-forge-v2'))")
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]);pg=b.new_context(viewport={"width":390,"height":844},device_scale_factor=2).new_page();pg.set_default_timeout(60000)
    pg.on("pageerror",lambda e:errs.append(str(e)));pg.route("https://openrouter.ai/**",h)
    pg.goto("http://127.0.0.1:8781/index.html");pg.wait_for_selector(".cta")
    pg.evaluate("()=>{localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,modes:[{n:'Swift',id:'a/b',d:''},{n:'Grand',id:'c/d',d:''}],mode:0}))}");pg.reload();pg.wait_for_selector(".cta")
    # 1) world builder with the EPUB
    pg.click(".cta");pg.wait_for_selector("text=Import the book or notes")
    t0=time.time()
    with pg.expect_file_chooser() as fc: pg.click("button:text-is('Import an EPUB or text file')")
    fc.value.set_files(BOOK);pg.wait_for_selector(".notice:has-text('Imported')");print("import: %.1fs |"%(time.time()-t0),pg.inner_text(".notice:has-text('Imported')")[:150])
    print("based-on prefilled:",pg.input_value("input[placeholder^='Any anime']"))
    pg.screenshot(path=SP+"/aj-build-import.png",full_page=True)
    pg.click("button:text-is('Build world')");pg.wait_for_selector(".hero")
    bc=[x for x in calls if "game master" in x["messages"][0]["content"]];c0=bc[0]["messages"][0]["content"]
    print("build requests:",len(bc),"| digest used:","Digest of a book the player imported" in c0,"| has names:","FREQUENT NAMES:" in c0,"| excerpts:",c0.count("% in]"),"| prompt chars:",len(c0))
    print("names sample:",c0.split("FREQUENT NAMES: ")[1].split("\n")[0][:200])
    d=db(pg);st=d["stories"][0];print("story:",st["title"],"| canon:",st["canon"],"| refs attached:",[(r["name"],r["for"]==[st["id"]]) for r in d["refs"]])
    print("story page refs button:",pg.locator("button:has-text('Reference texts')").inner_text())
    # 2) editor: paste notes and fill
    calls.clear();pg.click("button.back");pg.click("text=Create");pg.click("text=New story by hand");pg.wait_for_selector("text=Fill in from a book or notes")
    pg.fill(".item textarea","My notes about the world. "*40);pg.click("button:text-is('Use pasted text')");pg.wait_for_selector(".notice:has-text('Imported')")
    pg.fill("input[placeholder='e.g. The Lantern Road']","My Own Title")
    pg.click("button:text-is('Fill in the fields')");pg.wait_for_function("document.querySelector('input[placeholder=\"Leave empty for an original world\"]').value.length>0")
    time.sleep(.3)
    print("editor: title kept:",pg.input_value("input[placeholder='e.g. The Lantern Road']"),"| setting:",pg.input_value("label.fld:has-text('World and premise') textarea")[:40],"| canon notes:",pg.locator("input[placeholder='Keywords: name, alias']").count(),"| starts:",pg.input_value("label.fld:has-text('Starting points') textarea").replace("\n"," / "))
    print("pasted text sent whole:", "My notes about the world." in [x for x in calls][0]["messages"][0]["content"])
    pg.screenshot(path=SP+"/ak-edit-fill.png",full_page=True)
    pg.click("header >> text=Save");pg.wait_for_selector(".hero");d=db(pg);st2=d["stories"][0]
    print("saved: title",st2["title"],"| no temp field:","_refs" not in st2,"| pasted ref attached:",[r["for"] for r in d["refs"] if r["name"]=="Pasted notes"])
    b.close()
srv.terminate();print("ERRORS:",errs)
