"""Local EPUB, source retention, evidence, revisions and usage gates. No paid requests."""
import io
import json
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[1] / "site"
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
BASE = f"http://127.0.0.1:{port}"
CHAPTERS = [
    "Mira Vale found the silver lock. Mira Vale studied its mechanism. Mira Vale stored the key.",
    "Mira Vale entered the golden archive. Mira Vale recorded the moon cipher. Mira Vale left the archive.",
]
book = io.BytesIO()
with zipfile.ZipFile(book, "w") as epub:
    epub.writestr("META-INF/container.xml", '<container><rootfile full-path="book.opf"/></container>')
    epub.writestr("book.opf", '<package xmlns:dc="urn:dc"><metadata><dc:title>Archive Test</dc:title></metadata>'
                  '<manifest><item id="one" href="one.xhtml"/><item id="two" href="two.xhtml"/></manifest>'
                  '<spine><itemref idref="one"/><itemref idref="two"/></spine></package>')
    for number, path in enumerate(("one", "two"), 1):
        epub.writestr(path+".xhtml", f"<html><body><h1>Chapter {number}</h1><p>{CHAPTERS[number-1]}</p></body></html>")

def mock(route):
    data = json.loads(route.request.post_data)
    sent.append(data)
    raw = json.loads(data["messages"][-1]["content"])
    records = [{"chapter": row["n"], "kind": "event", "title": f"Indexed event {row['n']}",
                "text": "The archive research advances.", "evidence": "Mira Vale", "private": False}
               for row in raw]
    route.fulfill(json={"choices":[{"message":{"content":json.dumps({"entries":records})}}],
                         "usage":{"prompt_tokens":200,"completion_tokens":100}})

sent, errors = [], []
with subprocess.Popen([sys.executable,"-m","http.server",str(port),"--bind","127.0.0.1"],
                      cwd=SITE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL) as server:
    try:
        time.sleep(.6)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(service_workers="block")
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.route("https://source-fixture.example/**", mock)
            page.route("https://openrouter.ai/**", lambda route: route.abort())
            page.goto(BASE)
            page.wait_for_function("!!idb&&!!window.SFFanUI")
            page.evaluate("""bytes=>{window.epubFixture=new File([new Uint8Array(bytes)],'archive.epub');
              DB.prov='opencode';DB.ocKey='fixture';DB.ocProxy='https://source-fixture.example';
              DB.modes=[{n:'Local test',id:'test',d:''}];DB.mode=0;}""", list(book.getvalue()))
            assert page.evaluate("""async()=>{const r=await ffImportPreview(epubFixture,{mode:'basic'});
                window.importPreview=r;
                return r.ok&&r.preview.added.length===2&&!ffUniverse(r.preview.universe)&&!(await ffStoredSource(r.preview.universe,r.preview.sourceId)).length;
            }""")
            assert page.evaluate("importPreview.commit().applied")
            assert page.evaluate("ffSourceStatus('archive-test')")["readiness"] == "basic"
            assert not page.evaluate("""ffAttachSourceText('archive-test',new File(['Different text'],'other.txt'))""")["ok"]
            assert page.evaluate("ffAttachSourceText('archive-test',epubFixture)")["matched"] == 2
            assert page.evaluate("ffSourceStatus('archive-test')")["readiness"] == "searchable"
            assert page.evaluate("ffSearchSource('archive-test','golden archive',{maxChapter:1})") == []
            assert page.evaluate("ffSearchSource('archive-test','golden archive',{maxChapter:2})")[0]["chapter"] == 2
            assert page.evaluate("""async()=>{const result=await ffQuickSourceFacts(ffUniverse('archive-test'),
                {concept:'Mira Vale and the silver lock',maxChapter:1});return result.some(r=>r.id.startsWith('c1.')&&r.source.title.startsWith('Chapter 1'));}""")
            assert page.evaluate("""async()=>{const u=ffUniverse('archive-test'),canon={universe:u.id,rev:u.rev,position:{ch:1}};
                const out=await ffSourcePrompt({canon,mem:{}},{kind:'story'},[],'silver lock');
                return out.includes('SOURCE PASSAGES')&&out.includes('silver lock')&&!out.includes('golden archive');
            }""")
            assert page.evaluate("ffDeepEstimate('archive-test',{from:1,to:2})")["requests"] == 1
            assert not page.evaluate("ffDeepIndex('archive-test',{from:1,to:2})")["ok"]
            assert not sent
            page.evaluate("DB.ocMon=100;DB.ocLog=[[Date.now(),45]]")
            assert "45%" in page.evaluate("ffDeepIndex('archive-test',{from:1,to:2,confirmed:true})")["reason"]
            assert not sent
            page.evaluate("DB.ocLog=[]")
            assert page.evaluate("""async()=>{const c=new AbortController();c.abort();
                return await ffDeepIndex('archive-test',{from:1,to:2,confirmed:true,signal:c.signal});}""")["paused"]
            assert not sent
            first = page.evaluate("ffUniverse('archive-test').rev")
            assert page.evaluate("ffDeepIndex('archive-test',{from:1,to:2,confirmed:true})")["done"] == [1,2]
            assert len(sent) == 1
            assert page.evaluate(f"ffIndexedUniverse(ffUniverse('archive-test'),{first}).events.length") == 0
            latest = page.evaluate("ffUniverse('archive-test').rev")
            assert page.evaluate("ffIndexedUniverse(ffUniverse('archive-test')).events.length") == 2
            assert page.evaluate("ffDeepEstimate('archive-test',{from:1,to:2})")["requests"] == 0
            assert page.evaluate("ffDeepIndex('archive-test',{from:1,to:1,confirmed:true,rerun:true})")["done"] == [1]
            assert page.evaluate(f"ffIndexedUniverse(ffUniverse('archive-test'),{latest}).events.length") == 2
            assert page.evaluate("ffIndexedUniverse(ffUniverse('archive-test')).events.length") == 2
            assert not page.evaluate("JSON.stringify(savedDB()).includes('silver lock')")
            page.evaluate("window.SFFanUI.sourceIndex('archive-test')")
            page.get_by_text("Passage search",exact=True).wait_for()
            page.get_by_placeholder("Names, places or events").fill("silver lock")
            page.get_by_role("button",name="Find passages").click()
            page.get_by_text("Mira Vale found the silver lock.",exact=False).wait_for()
            assert page.evaluate("ffDropSourceText('archive-test',ffUniverse('archive-test').sources[0].id)")["ok"]
            assert page.evaluate("ffSourceStatus('archive-test')")["text"]["missing"] == ["Archive Test"]
            assert page.evaluate("ffIndexedUniverse(ffUniverse('archive-test')).events.length") == 2
            assert not errors, errors
            browser.close()
    finally:
        server.terminate()
print("ERRORS: []")
