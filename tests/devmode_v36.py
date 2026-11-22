"""memDevEnable must work only in development (localhost / ?dev=1) and must never turn memory on globally."""
import os, sys, subprocess, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.normpath(os.path.join(HERE, "..", "story-forge-pwa")); PORT = 8813
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
res = []; errs = []
SEED = "()=>{localStorage.clear();localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,modes:[{n:'S',id:'a/b'}],mode:0,stories:[{id:'s1',kind:'story',title:'T',setting:'x',entries:[],stats:[],endings:[],starts:[]}],sessions:[{id:'x1',storyId:'s1',char:{name:'A'},turns:[],mems:[],stats:{},len:'300',sugg:[],ended:[],cast:{}}]}))}"
def run(url, expect, label):
    with sync_playwright() as p:
        br = p.chromium.launch(args=["--no-sandbox", f"--host-resolver-rules=MAP story-forge.example 127.0.0.1:{PORT}"])
        pg = br.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url); pg.wait_for_selector(".cta"); pg.evaluate(SEED); pg.reload(); pg.wait_for_selector(".cta")
        r = pg.evaluate("memDevEnable('x1')"); s = pg.evaluate("[DB.sessions[0].memv2===true, DB.memv2]")
        ok = (r is expect) and (s[0] is expect) and (s[1] is False)
        res.append(ok); print(("ok  " if ok else "FAIL"), label, r, s); br.close()
run(f"http://127.0.0.1:{PORT}/index.html", True, "localhost: enables memory for one playthrough only")
run(f"http://story-forge.example/index.html", False, "real hostname: refuses and changes nothing")
run(f"http://story-forge.example/index.html?dev=1", True, "real hostname with ?dev=1: enables for one playthrough only")
srv.terminate(); print("ERRORS:", errs + [] if all(res) else ["devmode checks failed"]); sys.exit(0 if all(res) and not errs else 1)
