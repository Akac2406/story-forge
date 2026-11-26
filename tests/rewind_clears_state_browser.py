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
    T.append({"role": "user", "text": f"Action {n}"}); T.append({"role": "ai", "text": f"Reply {n}. " + ("word " * 50), "st2": {"Health": 100 - n}, **({"ss": {"Age": "0"}} if n == 0 else {})})
STORY = {"id": "s1", "kind": "story", "title": "Twins", "setting": "A cold house.", "starts": [], "stats": [{"n": "Health", "v": 100}], "endings": [], "entries": []}
SE = {"id": "e1", "storyId": "s1", "char": {"name": "Ann"}, "turns": T, "stats": {"Health": 93}, "mems": [], "sugg": [], "ended": [], "updated": 1,
      "chaps": [{"i": 0, "t": "Birth", "sum": "Old run: the twins are born."}, {"i": 6, "t": "Year five", "sum": "Old run: the twins are five; four herb packets."}, {"i": 12, "t": "Packets"}],
      "facts": ["The twins are five years old.", "Halven brought four frost-herb packets."], "fprev": {"k": 1, "f": ["The twins were just born."]},
      "canonReviews": [{"id": "r1", "k": 0, "ok": True, "issues": []}, {"id": "r2", "k": 1, "ok": True, "issues": []}], "canonReviewed": 1, "posHint": 4, "posRemind": 15, "statusOn": True, "status": {"Age": "5", "Curse": "eight strands"},
      "life": {"age": 5, "time": ""}, "log": [{"a": 0, "t": "Born in the snow", "ch": 0}, {"a": 5, "t": "The frost-dragon names its price", "ch": 1}, {"a": 5, "t": "Untagged old milestone"}],
      "quests": [{"t": "Find the archive entry", "at": 1, "ch": 1}, {"t": "Learn to walk", "at": 1, "ch": 0}, {"t": "My own goal", "at": 1}],
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
    ok(b["facts"] == ["The twins were just born."] and len(b["chaps"]) == 1 and "sum" not in b["chaps"][0] and b["stats"] == {"Health": 99}, "a branch inside chapter 1 goes back to chapter 1's facts, drops the stale summary and later stats")
    # Rewind in place to the first reply (turn 1)
    J("go({n:'chat',id:'e1'})"); pg.wait_for_timeout(300); J("turnMenu(DB.sessions[0],1)")
    btn = pg.locator("button:has-text('Rewind to here')"); btn.click(); pg.locator("button:has-text('Tap again to confirm')").click(); pg.wait_for_timeout(300)
    se = J("DB.sessions.find(s=>s.id==='e1')")
    ok(len(se["turns"]) == 2, "rewind keeps only the turns up to the chosen reply")
    ok(se["facts"] == ["The twins were just born."], "story facts go back to before the removed chapter (was: 'The twins are five years old')")
    ok(len(se["chaps"]) == 1 and "sum" not in se["chaps"][0], "the old summary of the kept chapter is gone")
    ok(se["stats"] == {"Health": 100}, "stats go back to the chosen reply")
    ok([x["t"] for x in se["log"]] == ["Born in the snow", "Untagged old milestone"], "life milestones from the removed chapter are gone")
    J("lifeSheet(DB.sessions.find(s=>s.id==='e1'))"); pg.locator(".tl button").nth(1).click(); pg.locator(".tl button:has-text('Tap again')").click(); pg.wait_for_timeout(100)
    pg.locator("label:has-text('Current age') input").fill("0"); pg.wait_for_timeout(100)
    se2 = J("DB.sessions.find(s=>s.id==='e1')")
    ok([x["t"] for x in se2["log"]] == ["Born in the snow"] and se2["life"]["age"] == 0, "the Life timeline lets the player remove a milestone and correct the age")
    J("closeSheet()")
    ok(se["status"] == {"Age": "5", "Curse": "eight strands"}, "replies from before v116 have no snapshot: the status window is left as it was, not wiped")
    ok([q["t"] for q in se["quests"]] == ["Learn to walk", "My own goal"], "quests opened in removed chapters are gone; earlier and hand-added ones stay")
    ok("Neska" not in se["cast"] and se["cast"]["Raon"]["r"] == "twin brother" and se["cast"]["Raon"]["b"] == 92, "people met in the removed chapter are gone; everyone else is kept")
    ok(se.get("canonReviews") == [] and "canonReviewed" not in se and "posHint" not in se and "posRemind" not in se, "canon reviews and position notices of removed chapters are gone, so new chapters get reviewed")
    ok(J("SFCanon.notes(DB,DB.sessions[0],getStory('s1'),DB.sessions[0].turns,'x',{}).active.every(n=>!/five years/.test(n.text))"), "nothing of the old run reaches the notes")
    # deleting every message from the end clears the old run too (Anna deleted all chapters by hand)
    J("""(()=>{const t=[];for(let n=0;n<6;n++){t.push({role:'user',text:'A'+n});t.push({role:'ai',text:'R'+n+' '+'w '.repeat(60)})}
      DB.sessions.push({id:'e2',storyId:'s1',char:{name:'Ann'},turns:t,stats:{},life:{age:5,time:''},log:[{a:5,t:'old'}],mems:[],sugg:[],ended:[],updated:1,statusOn:true,status:{Age:'5'},quests:[{t:'Old quest',at:1,ch:1}],
        chaps:[{i:0,t:'A',sum:'old'},{i:6,t:'B'}],facts:['The twins are five.']});save();return null})()""")
    J("go({n:'chat',id:'e2'})"); pg.wait_for_timeout(200)
    for _ in range(12):
        J("turnMenu(DB.sessions.find(s=>s.id==='e2'),DB.sessions.find(s=>s.id==='e2').turns.length-1)")
        pg.locator("button:has-text('Delete message')").click(); pg.locator("button:has-text('Tap again to confirm')").click(); pg.wait_for_timeout(80)
    e2 = J("DB.sessions.find(s=>s.id==='e2')")
    ok(e2["turns"] == [] and e2["status"] == {} and e2["quests"] == [] and e2["facts"] == [] and e2["log"] == [], "deleting all messages leaves no old status, quests or facts: " + json.dumps({k: e2.get(k) for k in ("status", "quests", "facts")}))
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
