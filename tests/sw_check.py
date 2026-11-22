"""The service worker must exist, match the app version, and serve the app offline after one visit.
Run: python tests/sw_check.py   (prints "ERRORS: []" when everything passes)"""
import os, re, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8842
fails = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
sw = open(os.path.join(APP, "sw.js")).read(); html = open(os.path.join(APP, "index.html")).read()
ok(len(sw) > 200 and 'addEventListener("fetch"' in sw, "sw.js is not empty and has a fetch handler")
v = re.search(r"VER=(\d+)", html).group(1)
ok(f'sf-v{v}"' in sw, f"cache name matches app version {v}")
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
with sync_playwright() as p:
    br = p.chromium.launch(); ctx = br.new_context(); pg = ctx.new_page()
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    ok(pg.evaluate("navigator.serviceWorker.ready.then(r=>!!r.active)"), "service worker activates")
    pg.wait_for_timeout(1500); pg.reload(); pg.wait_for_selector(".cta")
    ctx.set_offline(True); pg.reload(); 
    try: pg.wait_for_selector(".cta", timeout=8000); off = True
    except Exception: off = False
    ok(off, "app opens offline after one visit")
    br.close()
srv.terminate()
print("ERRORS:", fails); sys.exit(1 if fails else 0)
