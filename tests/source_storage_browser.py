"""Large EPUB, real localStorage pressure and atomic IndexedDB recovery on a phone viewport."""
import io
import json
import os
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = Path(os.environ.get("SF_STORAGE_SITE") or Path(__file__).resolve().parents[1] / "site")
BASELINE = os.environ.get("SF_STORAGE_BASELINE") == "105"
CHAPTERS = 502
ART = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

def make_epub():
    book = io.BytesIO()
    with zipfile.ZipFile(book, "w", compression=zipfile.ZIP_DEFLATED) as epub:
        epub.writestr("META-INF/container.xml", '<container><rootfile full-path="book.opf"/></container>')
        manifest = "".join(f'<item id="ch{n}" href="chapter-{n}.xhtml"/>' for n in range(1, CHAPTERS + 1))
        spine = "".join(f'<itemref idref="ch{n}"/>' for n in range(1, CHAPTERS + 1))
        epub.writestr("book.opf", f'<package xmlns:dc="urn:dc"><metadata><dc:title>Large Source</dc:title></metadata>'
                      f'<manifest>{manifest}</manifest><spine>{spine}</spine></package>')
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        for n in range(1, CHAPTERS + 1):
            name = "Archivist N" + alphabet[n % 26] + alphabet[(n // 26) % 26]
            title = f"Chapter {n}"
            text = (f"{name} checked catalog item {n}. Alice recorded the silver archive key. "
                    f"{name} checked the ledger again. Alice verified the entry. ") * 35
            epub.writestr(f"chapter-{n}.xhtml", f"<html><body><h1>{title}</h1><p>{text}</p></body></html>")
    return book.getvalue()

with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
base = f"http://127.0.0.1:{port}"
server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                          cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(.6)
    with sync_playwright() as p:
        browser_name = os.environ.get("SF_STORAGE_BROWSER", "chromium")
        browser = getattr(p, browser_name).launch()
        context = browser.new_context(**p.devices["iPhone 15"], service_workers="block")
        context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
        context.add_init_script("""(()=>{
          if(location.search.includes('fixture-no-idb')){
            IDBFactory.prototype.open=()=>{throw new DOMException("Test connection failure","InvalidStateError")};
          }
        })()""")
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(error.stack))
        page.goto(base)
        page.wait_for_function("!!idb&&!!window.SFFanUI")
        book = make_epub()
        page.evaluate("""async ([bytes,art])=>{
          window.fixture=new File([new Uint8Array(bytes)],"large.epub",{type:"application/epub+zip"});
          const r=await ffImportPreview(fixture,{mode:"basic"});
          const saved=r.commit();
          if(!saved.applied)throw Error(saved.reason);
          const u=ffUniverse("large-source");
          u.artwork={cover:art,banner:art};
          DB.key="fixture-key";DB.ocKey="fixture-connector";DB.theme="moon";
          DB.stories=[{id:"fixture-story",kind:"story",title:"Saved story",cover:art}];
          DB.sessions=[{id:"fixture-session",storyId:"fixture-story",turns:[{role:"ai",text:"Saved turn."}],
            char:{name:"Fixture"},cast:{},chaps:[{i:0,t:""}],mems:[{t:"Fixture",x:"Saved memory."}],canon:{universe:u.id,rev:u.rev,position:{ch:1}}}];
          await idbSet("fixture-original-art",art);
          save();
          await idbSet(KEY,JSON.stringify(savedDB()));
          window.readProtected=()=>JSON.stringify([DB.stories,DB.sessions,DB.key,DB.ocKey,DB.theme,ffUniverse("large-source").artwork]);
          window.protectedBefore=readProtected();
          window.mirrorBefore=localStorage.getItem(KEY);
          window.sourceKey=ffSourceKey(u.id,u.sources[0].id);
          window.catalogBefore=JSON.stringify(u);
          // Fill the browser's real localStorage quota, leaving less than a KB.
          let low=0,high=12*1024*1024;
          while(high-low>512){
            const size=Math.floor((low+high)/2);
            try{localStorage.setItem("fixture-storage-filler","x".repeat(size));low=size}
            catch(e){if(e.name!=="QuotaExceededError")throw e;high=size}
          }
          if(high===12*1024*1024||low<1000000)throw Error("Unexpected test storage quota");
          localStorage.setItem("fixture-storage-filler","x".repeat(low-128));
        }""", [list(book), ART])
        if BASELINE:
            result = page.evaluate("ffAttachSourceText('large-source',fixture)")
            assert not result["ok"] and "Could not save the index metadata" in result["reason"], result
            assert page.evaluate("readProtected()===protectedBefore")
            assert not page.evaluate("idbGet(sourceKey)")
            print("Reproduced v105 on a phone viewport with a 502-chapter EPUB and real localStorage quota pressure.")
        else:
            page.evaluate("""async()=>{
              const parsed=await ffReadSource(fixture);
              const ix=SFFan.indexSource(parsed.input,{title:parsed.title});
              const old=ffIndexedChapters(ix).slice(0,2);
              await idbSet(sourceKey,old);
              window.previous=JSON.stringify(old);
              window.diskBefore=await idbGet(KEY);
              window.realPut=IDBObjectStore.prototype.put;
              IDBObjectStore.prototype.put=function(value,key){
                if(key===KEY && typeof value==="string"&&JSON.parse(value).sourceIndexStore)
                  throw new DOMException("Simulated quota on the second write","QuotaExceededError");
                return realPut.call(this,value,key);
              };
            }""")
            result = page.evaluate("ffAttachSourceText('large-source',fixture)")
            assert not result["ok"] and "IndexedDB is full" in result["reason"], result
            assert page.evaluate("""async()=>JSON.stringify(await idbGet(sourceKey))===previous
                &&await idbGet(KEY)===diskBefore&&JSON.stringify(ffUniverse('large-source'))===catalogBefore
                &&readProtected()===protectedBefore&&localStorage.getItem(KEY)===mirrorBefore""")
            page.evaluate("""()=>{
              window.abortAttachment=new AbortController();
              IDBObjectStore.prototype.put=function(value,key){
                const result=realPut.call(this,value,key);
                if(key===sourceKey)abortAttachment.abort();
                return result;
              };
            }""")
            cancelled = page.evaluate("ffAttachSourceText('large-source',fixture,{signal:abortAttachment.signal})")
            assert not cancelled["ok"] and "cancelled" in cancelled["reason"], cancelled
            assert page.evaluate("async()=>JSON.stringify(await idbGet(sourceKey))===previous&&await idbGet(KEY)===diskBefore")
            page.evaluate("""async()=>{
              IDBObjectStore.prototype.put=realPut;
              const newer=JSON.parse(diskBefore);
              newer.ts+=10000;
              newer.globalNote="Saved in another tab";
              window.newerSnapshot=JSON.stringify(newer);
              await idbSet(KEY,newerSnapshot);
            }""")
            conflict = page.evaluate("ffAttachSourceText('large-source',fixture)")
            assert not conflict["ok"] and "another tab" in conflict["reason"], conflict
            assert page.evaluate("async()=>JSON.stringify(await idbGet(sourceKey))===previous&&await idbGet(KEY)===newerSnapshot")
            page.evaluate("async()=>{await idbSet(KEY,diskBefore);window.SFFanUI.sourceIndex('large-source')}")
            page.get_by_text("Attach or remove local text", exact=True).click()
            page.locator("input[type=file][accept='.epub,.txt,.md']").set_input_files(
                {"name":"large.epub", "mimeType":"application/epub+zip","buffer":book})
            page.get_by_role("button", name="Attach matching file", exact=True).click()
            page.get_by_text(f"Stored {CHAPTERS} matching chapters.").wait_for(timeout=30000)
            before = page.evaluate("protectedBefore")
            assert page.evaluate("localStorage.getItem(KEY)===mirrorBefore&&readProtected()===protectedBefore")
            assert page.evaluate(f"async()=> (await idbGet(sourceKey)).length==={CHAPTERS} && JSON.parse(await idbGet(KEY)).sourceIndexStore")
            page.reload()
            page.wait_for_function("!!idb&&DB.sourceIndexStore===true")
            actual = page.evaluate("JSON.stringify([DB.stories,DB.sessions,DB.key,DB.ocKey,DB.theme,ffUniverse('large-source').artwork])")
            assert json.loads(actual) == json.loads(before), [(i,a,b) for i,(a,b) in enumerate(zip(json.loads(actual),json.loads(before))) if a!=b]
            assert page.evaluate("idbGet('fixture-original-art')") == ART
            assert page.evaluate("ffSourceStatus('large-source')")["text"]["chapters"] == CHAPTERS
            assert page.evaluate("ffSearchSource('large-source','silver archive key',{maxChapter:1,limit:1})")[0]["chapter"] == 1
            page.evaluate("""async()=>{DB.globalNote='Saved after migration';save();
              await new Promise(resolve=>setTimeout(resolve,320));}""")
            page.reload()
            page.wait_for_function("!!idb&&DB.globalNote==='Saved after migration'")
            assert page.evaluate("JSON.stringify([DB.stories,DB.sessions,DB.key,DB.ocKey,DB.theme,ffUniverse('large-source').artwork])") == before
            assert page.evaluate("localStorage.getItem(SOURCE_STORE_MARKER)") == "1"
            page.goto(base+"/?fixture-no-idb")
            page.wait_for_function("sourceStoreReadOnly===true")
            assert not page.evaluate("save()")
            page.goto(base)
            page.wait_for_function("!!idb&&!sourceStoreReadOnly&&DB.globalNote==='Saved after migration'")
            assert page.evaluate("ffSourceStatus('large-source')")["text"]["chapters"] == CHAPTERS
            assert not errors, errors
            print(f"{browser_name} phone viewport: quota rollback, cancellation, retry, reload, artwork and post-migration writes passed.")
        browser.close()
finally:
    server.terminate()
print("ERRORS: []")
