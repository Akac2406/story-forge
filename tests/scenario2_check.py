"""Second test story: the trial page can switch to it and complete a free dry run with every check passing.
Run: python tests/scenario2_check.py   (prints "ERRORS: []" when everything passes)"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8841
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
fails, errs = [], []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
S2 = json.load(open(os.path.join(APP, "trial", "scenario2.json")))
ok(len(S2["turns"]) == 30 and {t.get("op") for t in S2["turns"]} >= {"regen", "branch", "cancel"}, "scenario 2 has 30 turns with regen, branch and cancel")
with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.evaluate("localStorage.setItem('story-forge-v2',JSON.stringify({migrated:true,ocKey:'x',ocProxy:'https://c.example',stories:[],sessions:[]}))")
    pg.goto(f"http://127.0.0.1:{PORT}/memtrial.html"); pg.wait_for_selector("#sc")
    pg.select_option("#sc", "trial/scenario2.json"); pg.wait_for_timeout(400)
    ok(pg.input_value("input[type=number] >> nth=0") == "30", "picking the second story sets 30 turns")
    pg.check("#dry"); pg.click("text=Start trial")
    for _ in range(600):
        if pg.evaluate("!!window.__trialReport"): break
        pg.wait_for_timeout(500)
    pr = pg.evaluate("JSON.parse(localStorage.getItem('sf-trial-progress'))"); md = pg.evaluate("window.__trialReport||''")
    ok(pr and pr["opts"]["sc"] == "trial/scenario2.json" and len(pr["rows"]) == 30, "dry run played all 30 turns of the second story")
    ok("Night Shift at Cedar Ridge" in md, "report names the test story")
    allc = [v for r in pr["rows"] for v in r["checks"].values()]
    ok(len(allc) > 30 and all(allc), f"all {len(allc)} per-turn checks pass with the stand-in")
    ok(all(pr["ops"].get(k) is True for k in ("regen_then_back_to_v1_restores_memory", "branch_keeps_only_earlier_memory", "branch_original_untouched", "cancel_keeps_reply_and_memory")), "regen, branch and cancel pass: " + json.dumps(pr["ops"]))
    pg.reload(); pg.wait_for_selector("#sc")
    ok(pg.input_value("#sc") == "trial/scenario2.json", "page remembers the chosen story after reload")
    br.close()
srv.terminate()
print("ERRORS:", fails + errs); sys.exit(1 if fails or errs else 0)
