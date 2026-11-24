"""Trial page finds the OpenCode key when the app keeps its data in IndexedDB, and never creates that database.
Run: python tests/memtrial_idb_key_v87.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8897
fails = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
U = f"http://127.0.0.1:{PORT}/memtrial.html"
with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(); pg = ctx.new_page(); pg.goto(U); pg.wait_for_selector("#setup p")
    ok("No OpenCode key" in pg.inner_text("#setup"), "no data anywhere: page says no key")
    ok(not pg.evaluate("indexedDB.databases().then(d=>d.some(x=>x.name==='story-forge'))"), "the app's database was not created by the trial page")
    ctx.close()
    ctx = br.new_context(); pg = ctx.new_page(); pg.goto(U); pg.wait_for_selector("#setup p")
    db = {"prov": "opencode", "ocKey": "dummy-not-real", "ocProxy": "https://connector.example.test", "sessions": [], "stories": []}
    pg.evaluate("""d=>new Promise(r=>{const q=indexedDB.open('story-forge',1);q.onupgradeneeded=()=>q.result.createObjectStore('kv');q.onsuccess=()=>{const t=q.result.transaction('kv','readwrite');t.objectStore('kv').put(d,'story-forge-v2');t.oncomplete=()=>{q.result.close();r()}}})""", json.dumps(db))
    pg.reload(); pg.wait_for_selector("#setup p")
    ok("key and connector found" in pg.inner_text("#setup"), "key kept only in IndexedDB is found")
    ok(pg.evaluate("localStorage.getItem('story-forge-v2')") is None, "nothing written to the app's storage")
    ctx.close(); br.close()
srv.terminate()
print("ERRORS:", fails); sys.exit(1 if fails else 0)
