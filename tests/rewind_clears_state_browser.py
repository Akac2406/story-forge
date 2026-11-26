"""Rewind clears what the removed turns built (v114, Anna 2026-11-26: after "Rewind to here" to chapter 1 the narrator rebuilt her old
storyline — the twins were five again, the old herb packets came back). Before, Rewind kept story facts, chapter summaries, stats,
canon reviews and hints from the removed turns. Branches use the same trimming. No network. Run: python tests/rewind_clears_state_browser.py"""
import json, os, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site")
with socket.socket() as s:
    s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
T = []
for n in range(8):
    T.append({"role": "user", "text": f"Action {n}"}); T.append({"role": "ai", "text": f"Reply {n}. " + ("word " * 50), "st2": {"Health": 100 - n}})
STORY = {"id": "s1", "kind": "story", "title": "Twins", "setting": "A cold house.", "starts": [], "stats": [{"n": "Health", "v": 100}], "endings": [], "entries": []}
SE = {"id": "e1", "storyId": "s1", "char": {"name": "Ann"}, "turns": T, "stats": {"Health": 93}, "mems": [], "sugg": [], "ended": [], "updated": 1,
      "chaps": [{"i": 0, "t": "Birth", "sum": "Old run: the twins are born."}, {"i": 6, "t": "Year five", "sum": "Old run: the twins are five; four herb packets."}, {"i": 12, "t": "Packets"}],
      "facts": ["The twins are five years old.", "Halven brought four frost-herb packets."], "fprev": {"k": 1, "f": ["The twins were just born."]},
      "canonReviews": [{"id": "r1", "k": 0, "ok": True, "issues": []}, {"id": "r2", "k": 1, "ok": True, "issues": []}], "canonReviewed": 1, "posHint": 4, "posRemind": 15,
      "cast": {"Raon": {"r": "twin brother", "l": "", "t": [], "a": "now trusts her judgment in the frost", "b": 92, "ch": 0}, "Neska": {"r": "warden", "l": "", "t": [], "a": "wary", "ch": 1}}}
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "stories": [STORY], "sessions": [SE]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(service_workers="block"); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", lambda r: r.abort())
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    J = lambda e: pg.evaluate(e)
    # a branch from turn 3 (inside chapter 1) — same trimming
    J("(()=>{branchAt(DB.sessions[0],3,{staged:true});return null})()")
    b = J("DB.sessions[1]")
    ok(b["facts"] == [] and len(b["chaps"]) == 1 and "sum" not in b["chaps"][0] and b["stats"] == {"Health": 99}, "a branch inside chapter 1 drops later facts, the stale summary and later stats")
    # Rewind in place to the first reply (turn 1)
    J("go({n:'chat',id:'e1'})"); pg.wait_for_timeout(300); J("turnMenu(DB.sessions[0],1)")
    btn = pg.locator("button:has-text('Rewind to here')"); btn.click(); pg.locator("button:has-text('Tap again to confirm')").click(); pg.wait_for_timeout(300)
    se = J("DB.sessions.find(s=>s.id==='e1')")
    ok(len(se["turns"]) == 2, "rewind keeps only the turns up to the chosen reply")
    ok(se["facts"] == [], "story facts from the removed turns are gone (was: 'The twins are five years old')")
    ok(len(se["chaps"]) == 1 and "sum" not in se["chaps"][0], "the old summary of the kept chapter is gone")
    ok(se["stats"] == {"Health": 100}, "stats go back to the chosen reply")
    ok("Neska" not in se["cast"] and se["cast"]["Raon"]["a"] == "" and "b" not in se["cast"]["Raon"] and se["cast"]["Raon"]["r"] == "twin brother", "people met later are gone; earlier people keep who they are but lose later feelings and bonds")
    ok(se.get("canonReviews") == [] and "canonReviewed" not in se and "posHint" not in se and "posRemind" not in se, "canon reviews and position notices of removed chapters are gone, so new chapters get reviewed")
    ok(J("SFCanon.notes(DB,DB.sessions[0],getStory('s1'),DB.sessions[0].turns,'x',{}).active.every(n=>!/five years/.test(n.text))"), "nothing of the old run reaches the notes")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
