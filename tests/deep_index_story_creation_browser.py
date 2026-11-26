"""Keep a selected Deep Indexing range alive across story creation, pause and reload."""
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[1] / "site"
PROVIDER = "https://source-fixture.example/"
BOOK = "\n\n".join(
    f"Chapter {n}\n\n" + "Mira Vale walks the archive halls. " * 550 + f"Mira Vale finds clue {n}."
    for n in range(1, 5)
)

with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
origin = f"http://127.0.0.1:{port}"
requests, errors = [], []


def reply(route, data):
    route.fulfill(json={"choices": [{"message": {"content": json.dumps(data)}}],
                        "usage": {"prompt_tokens": 200, "completion_tokens": 100}})


def mock(route):
    if route.request.url.startswith(origin + "/"):
        route.continue_()
        return
    if not route.request.url.startswith(PROVIDER):
        route.abort()
        return
    messages = json.loads(route.request.post_data)["messages"]
    session = route.request.headers["x-opencode-session"]
    if "You set up an interactive fanfiction" in messages[0]["content"]:
        requests.append(("create", session))
        reply(route, {"title": "Into the Archive", "premise": "Search for the lost key.",
                      "modes": ["oc"], "player": {"name": "Ash", "desc": "An archivist"},
                      "opening": "The archive opens.", "characters": []})
        return
    chapters = json.loads(messages[-1]["content"])
    chapter = int(chapters[0]["sourceRef"].split("-")[1])
    requests.append((chapter, session))
    result = {"entries": [{"sourceRef": row["sourceRef"], "kind": "event",
                           "title": "Clue " + row["sourceRef"], "text": "A clue is found.",
                           "evidence": "Mira Vale finds clue", "private": False} for row in chapters]}
    reply(route, result)


server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                          cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    with sync_playwright() as pw:
        browser = getattr(pw, os.environ.get("SF_BROWSER", "chromium")).launch()
        page = browser.new_page(viewport={"width": 390, "height": 844}, service_workers="block")
        page.set_default_timeout(12000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("dialog", lambda dialog: dialog.accept())
        page.route("**/*", mock)
        page.goto(origin)
        page.wait_for_function("!!idb && !!window.SFFanUI")
        source = page.evaluate("""async text=>{
            DB.prov='opencode';DB.ocKey='fixture';DB.ocProxy='https://source-fixture.example';
            DB.modes=[{n:'Mock',id:'test'}];DB.mode=0;DB.ocMon=100;DB.ocLog=[];
            const fetch0=window.fetch;
            window.fetch=async (url,opts)=>{
                const result=await fetch0(url,opts);
                if(!String(url).startsWith(DB.ocProxy))return result;
                const messages=JSON.parse(opts.body).messages;
                if(messages[0].content.startsWith('Extract only evidence-based')){
                    const ref=JSON.parse(messages.at(-1).content)[0].sourceRef;
                    if(['section-1-0','section-3-0'].includes(ref))await new Promise((resolve,reject)=>{
                        if(opts.signal.aborted){reject(opts.signal.reason);return}
                        const abort=()=>reject(opts.signal.reason);
                        opts.signal.addEventListener('abort',abort,{once:true});
                        window.releaseIndex=()=>{opts.signal.removeEventListener('abort',abort);resolve()};
                        window.heldRef=ref;
                    });
                }
                return result;
            };
            DB.stories.push({id:'existing',kind:'story',title:'Existing story',cover:'data:image/png;base64,YQ=='});
            const p=await ffImportPreview(new File([text],'Archive.txt'),{mode:'smart',title:'Archive'});
            if(!(await p.commit()).applied)throw Error('Cannot save fixture');
            return p.preview.sourceId;
        }""", BOOK)

        def open_index():
            page.evaluate("source=>SFFanUI.sourceIndex('archive',source)", source)

        def start():
            page.get_by_role("button", name="Estimate analysis").click()
            page.get_by_text("planned requests", exact=False).wait_for()
            page.get_by_role("button", name="Start or resume AI analysis").click()

        open_index()
        page.get_by_label("Last index entry").fill("4")
        page.get_by_label("Re-analyze completed chapters").check()
        start()
        page.wait_for_function("window.heldRef==='section-1-0'")
        assert requests[0][0] == 1
        page.get_by_role("button", name="Done", exact=True).click()
        page.locator("#sf-deep-task").get_by_role("status").wait_for()
        page.evaluate("""()=>{
            window.creation=qcPreview({sourceTitle:'Archive',concept:'Ash finds clues',character:'Ash',maxChapter:4},
                {universeId:'archive'}).then(r=>{
                if(!r.ok)throw Error(r.reason);
                const saved=qcCommit(r.blueprint);
                if(!saved.applied)throw Error(saved.reason);
                return saved.storyId;
            }).then(id=>{window.createdId=id},error=>{window.createError=error.message});
        }""")
        assert len(requests) == 1, requests
        page.evaluate("releaseIndex()")
        page.wait_for_function("window.createdId || window.createError")
        assert not page.evaluate("window.createError"), page.evaluate("window.createError")
        created = page.evaluate("window.createdId")
        page.wait_for_function("source=>ffUniverse('archive').deep?.sources[source]?.done.includes(2)", arg=source)
        assert [r[0] for r in requests[:3]] == [1, "create", 2], requests
        assert requests[0][1] != requests[1][1]
        page.wait_for_function("""source=>ffUniverse('archive').deep.sources[source].done.length===2
            && window.heldRef==='section-3-0'""", arg=source)
        page.get_by_role("button", name="Pause Deep Indexing").click()
        page.get_by_text("Analysis paused", exact=True).wait_for()
        page.reload()
        page.wait_for_function("ffDeepTask.job?.options.to==='4' && !ffDeepTask.controller")
        assert page.evaluate("id=>getStory(id)?.title", created) == "Into the Archive"
        assert page.evaluate("getStory('existing').cover") == "data:image/png;base64,YQ=="
        open_index()
        assert page.get_by_label("Last index entry").input_value() == "4"
        assert page.get_by_label("Re-analyze completed chapters").is_checked()
        start()
        page.get_by_text("Analysis saved for 2 chapters.", exact=True).first.wait_for()
        assert [r[0] for r in requests] == [1, "create", 2, 3, 3, 4], requests
        assert page.evaluate("source=>ffUniverse('archive').deep.sources[source].done", source) == [1, 2, 3, 4]
        assert not page.evaluate("idbGet(FF_DEEP_TASK_KEY)")
        assert not errors, errors
        browser.close()
finally:
    server.terminate()
    server.wait()
print("PASS: navigation, story creation, request priority, pause, reload and resume")
print("ERRORS: []")
