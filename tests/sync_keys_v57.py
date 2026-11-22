"""v57: the OpenCode key can travel with encrypted sync, off by default.
Two simulated devices and a fake connector (no real key, no network, no model calls).
Run: python tests/sync_keys_v57.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8853
CONN = "https://connector.example.test"
fails = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
STORE = {}; PUTS = []
def conn(route):
    rq = route.request; sid = rq.headers.get("x-sync-id", "")
    if rq.method == "GET":
        if sid in STORE: return route.fulfill(status=200, content_type="text/plain", body=STORE[sid])
        return route.fulfill(status=404, body="")
    if rq.method == "PUT":
        STORE[sid] = rq.post_data; PUTS.append(rq.post_data); return route.fulfill(status=200, body="ok")
    route.fulfill(status=405, body="")
BASE = {"migrated": True, "prov": "opencode", "ocProxy": CONN, "syncPass": "correct horse battery staple test",
        "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "stories": [], "sessions": [], "chars": [], "found": {}}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
errs = []
def device(br, extra):
    ctx = br.new_context(accept_downloads=True); pg = ctx.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route(CONN + "/**", conn)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(dict(BASE, **extra)))
    pg.reload(); pg.wait_for_selector(".cta"); return pg
def sync(pg): pg.evaluate("syncNow(true)"); pg.wait_for_timeout(300); pg.wait_for_function("!SYNC.busy")
def st(pg): return pg.evaluate("({k:DB.ocKey||'',on:!!DB.syncKeys,at:DB.keysAt||0})")
def settings(pg): pg.evaluate("go({n:'settings'})"); pg.wait_for_timeout(200)
with sync_playwright() as p:
    br = p.chromium.launch()
    A = device(br, {"ocKey": "test-key-A1"})
    B = device(br, {})
    sync(A); sync(B)
    ok(st(B)["k"] == "", "switch off by default: key does not travel")
    ok(all("test-key" not in x for x in PUTS), "connector never receives the key in readable form")
    settings(A); A.click("label.chk:has-text('Also sync my OpenCode key') input"); A.wait_for_timeout(100)
    ok(st(A)["on"], "switch turns on from Settings")
    sync(A); sync(B)
    b = st(B); ok(b["k"] == "test-key-A1" and b["on"], "new device gets the key with only connector + passphrase")
    ok(B.locator("text=Your OpenCode key arrived").count() > 0, "new device is told the key arrived")
    ok(all("test-key" not in x for x in PUTS), "key is encrypted in every upload")
    settings(A); f = A.locator("input[type=password]").first; f.fill("test-key-A2"); f.dispatch_event("change"); A.wait_for_timeout(100)
    sync(A); sync(B)
    ok(st(B)["k"] == "test-key-A2", "a changed key reaches the other device")
    settings(B); B.click("label.chk:has-text('Also sync my OpenCode key') input"); B.wait_for_timeout(100)
    sync(B); sync(A)
    a = st(A); ok(not a["on"] and a["k"] == "test-key-A2", "turning off on one device turns it off everywhere; keys already there stay")
    C = device(br, {}); sync(C)
    ok(st(C)["k"] == "", "after turning off, a new device no longer receives the key")
    wrong = device(br, {"syncPass": "a different passphrase"}); sync(wrong)
    ok(st(wrong)["k"] == "", "a wrong passphrase gets nothing")
    # backups leave out keys, passphrase and connector
    settings(A)
    with A.expect_download() as dl: A.click("button:has-text('Save or send a backup')")
    d = json.loads(open(dl.value.path()).read())
    ok(not any(k in d for k in ("key", "ocKey", "syncPass", "ocProxy")), "backup file has no keys, passphrase or connector address")
    # replace-restore keeps this device's passphrase, connector and key
    before = A.evaluate("({p:DB.syncPass,c:DB.ocProxy,k:DB.ocKey})")
    A.evaluate("""d=>{const inp=[...document.querySelectorAll('input[type=file]')].find(i=>/json/.test(i.accept));
        const btn=[...document.querySelectorAll('button')].find(b=>/Replace everything/.test(b.textContent));btn.click();
        const f=new File([JSON.stringify(d)],'b.json',{type:'application/json'});const dt=new DataTransfer();dt.items.add(f);inp.files=dt.files;inp.dispatchEvent(new Event('change'))}""", d)
    A.wait_for_timeout(600)
    after = A.evaluate("({p:DB.syncPass,c:DB.ocProxy,k:DB.ocKey})")
    ok(after == before, "restoring a backup keeps this device's passphrase, connector and key")
    br.close()
srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
