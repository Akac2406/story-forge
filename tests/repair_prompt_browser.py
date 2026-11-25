"""Memory step prompt: includes the player's action as evidence for LEARNED only; hidden openers are not included. No network.
Run: python tests/repair_prompt_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8897
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
T = [{"role": "user", "text": "Begin secret opener", "hide": True}, {"role": "ai", "text": "The hall is quiet."},
     {"role": "user", "text": "I take Aled aside and tell him the deed is forged."}, {"role": "ai", "text": "Aled went pale and nodded slowly."}]
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Manor", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Ilse"}, "cast": {"Aled": {}}, "turns": T, "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    m = pg.evaluate("repairMsgs(DB.sessions[0],DB.sessions[0].turns[3])[0].content")
    ok("PLAYER ACTION" in m and "tell him the deed is forged" in m, "player's action included for the latest reply")
    ok(m.index("PLAYER ACTION") < m.index("REPLY\n") and "evidence for LEARNED only" in m and "never for EVENTS or SCENE" in m, "action is labelled as LEARNED-only evidence")
    m1 = pg.evaluate("repairMsgs(DB.sessions[0],DB.sessions[0].turns[1])[0].content")
    ok("PLAYER ACTION" not in m1 and "secret opener" not in m1, "hidden opener is not passed as a player action")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
