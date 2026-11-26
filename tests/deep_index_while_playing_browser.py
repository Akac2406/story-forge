"""Deep Indexing keeps running while the player reads or plays: regular saves during the run (a reply, scrolling, settings) must not cancel
an analysis checkpoint. Before v111, save() aborted the in-flight checkpoint write and the run stopped with "App data changed during
indexing", losing that batch. Mocked provider, no paid requests. Run: python tests/deep_index_while_playing_browser.py"""
import io, json, socket, subprocess, sys, time, zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright
SITE = Path(__file__).resolve().parents[1] / "site"
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]
BASE = f"http://127.0.0.1:{port}"
fails = []; errors = []; sent = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
# 8 long chapters so the run needs several batches (and several checkpoint writes)
CH = [("Mira Vale walks the archive halls. " * 600) + f"Mira Vale finds clue {n}." for n in range(1, 9)]
book = io.BytesIO()
with zipfile.ZipFile(book, "w") as epub:
    epub.writestr("META-INF/container.xml", '<container><rootfile full-path="book.opf"/></container>')
    items = "".join(f'<item id="c{n}" href="c{n}.xhtml"/>' for n in range(1, 9)); spine = "".join(f'<itemref idref="c{n}"/>' for n in range(1, 9))
    epub.writestr("book.opf", f'<package xmlns:dc="urn:dc"><metadata><dc:title>Long Archive</dc:title></metadata><manifest>{items}</manifest><spine>{spine}</spine></package>')
    for n in range(1, 9): epub.writestr(f"c{n}.xhtml", f"<html><body><h1>Chapter {n}</h1><p>{CH[n-1]}</p></body></html>")
def mock(route):
    data = json.loads(route.request.post_data); sent.append(1)
    raw = json.loads(data["messages"][-1]["content"])
    records = [{"sourceRef": row["sourceRef"], "kind": "event", "title": f"Clue found {row['sourceRef']}", "text": "Mira finds a clue.", "evidence": "Mira Vale finds clue", "private": False} for row in raw]
    time.sleep(0.05)
    route.fulfill(json={"choices": [{"message": {"content": json.dumps({"entries": records})}}], "usage": {"prompt_tokens": 200, "completion_tokens": 100}})
with subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as server:
    try:
        time.sleep(.6)
        with sync_playwright() as p:
            browser = p.chromium.launch(); page = browser.new_page(service_workers="block"); page.set_default_timeout(60000)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.route("https://source-fixture.example/**", mock); page.route("https://openrouter.ai/**", lambda r: r.abort())
            page.goto(BASE); page.wait_for_function("!!idb&&!!window.SFFanUI")
            page.evaluate("""bytes=>{window.epubFixture=new File([new Uint8Array(bytes)],'long.epub');
              DB.prov='opencode';DB.ocKey='fixture';DB.ocProxy='https://source-fixture.example';DB.modes=[{n:'Local test',id:'test',d:''}];DB.mode=0;DB.ocLog=[];}""", list(book.getvalue()))
            uid = page.evaluate("async()=>{const r=await ffImportPreview(epubFixture,{mode:'basic'});await r.commit();return r.preview.universe}")
            ok(page.evaluate(f"async()=>(await ffAttachSourceText('{uid}',epubFixture)).ok"), "the book text is attached")
            est = page.evaluate(f"ffDeepEstimate('{uid}',{{from:1,to:8}})"); ok(est["ok"] and est["requests"] >= 3, "the run needs several batches (" + str(est.get("requests")) + ")")
            # the player keeps using the app: frequent regular saves during the whole run
            page.evaluate("window.__saves=0;window.__tick=setInterval(()=>{DB.readingTick=(DB.readingTick||0)+1;save();__saves++},3);null")
            r = page.evaluate(f"async()=>{{const r=await ffDeepIndex('{uid}',{{from:1,to:8,confirmed:true}});clearInterval(__tick);return r}}")
            ok(page.evaluate("__saves") > 50, "many saves happened during the run (" + str(page.evaluate("__saves")) + ")")
            ok(r["ok"] is not False and sorted(r["done"]) == list(range(1, 9)) and not r.get("reason"), "the run finishes every chapter despite saves: " + json.dumps({k: r.get(k) for k in ("done", "reason")}))
            ok(page.evaluate(f"ffIndexedUniverse(ffUniverse('{uid}')).events.length") >= 8, "all analysis results are kept")
            ok(page.evaluate("DB.readingTick") > 50, "the player's own changes are kept too")
            page.reload(); page.wait_for_function("!!idb&&!!window.SFFanUI")
            ok(page.evaluate(f"ffIndexedUniverse(ffUniverse('{uid}')).events.length") >= 8 and page.evaluate("DB.readingTick") > 50, "both survive a reload")
            browser.close()
    finally:
        server.terminate()
ok(not errors, "no page errors " + str(errors[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
