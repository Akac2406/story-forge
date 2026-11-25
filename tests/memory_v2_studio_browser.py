"""Memory overhaul: Studio API inside the app (memView/memQuery/memEdit/memPin/memDelete/memUndo/memConflicts/memResolve).
Simulated replies, no network. Run: python tests/memory_v2_studio_browser.py"""
import json, os, re, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8897
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
N = {"n": 0}
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"):
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    N["n"] += 1
    txt = ('Rae | "Reply %d."\n\n[[META]]\nEVENTS: 3 | reveal | Rae | harbor office | Rae finds clue %d | none\nLEARNED: Rae: clue %d matters (she saw it)\nSCENE: harbor office | Rae | night\nENDING: none') % (N["n"], N["n"], N["n"])
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\ndata: [DONE]\n\n")
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "notes": [{"id": "g1", "text": "Keep it under 250 words.", "pri": "must", "on": True}],
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "A harbor town.", "starts": [], "stats": [], "endings": [],
                     "entries": [{"k": "Dale", "t": "Harbor master.", "lock": True}]}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "memv2": True, "dead": ["Old Tom"], "quests": ["Find the forger"],
                      "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog over the harbor."}],
                      "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    ok(pg.evaluate("!!window.SFMem2"), "memory-v2.js loads")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    for i in (1, 2):
        pg.fill("#input", "Look around %d." % i); pg.click("button[aria-label='Send']"); pg.wait_for_selector(f"text=Reply {i}."); pg.wait_for_timeout(300)
    st = pg.evaluate("SFMem2.stats(memView(DB.sessions[0]))")
    ok(st["episodic"] >= 2 and st["permanent"] >= 3 and st["working"] == 1 and st["world"] >= 2, f"memView builds layers from the live story: {st}")
    ok(pg.evaluate("SFMem2.integrity(memView(DB.sessions[0])).ok"), "view integrity ok")
    ev = pg.evaluate("memQuery(DB.sessions[0],{layer:'episodic'}).map(r=>[r.id,r.text])")
    first_id = ev[0][0]
    pg.evaluate(f"memEdit(DB.sessions[0],'{first_id}',{{text:'Rae finds the real clue (player fix)'}})")
    pg.evaluate("memPin(DB.sessions[0],memQuery(DB.sessions[0],{layer:'semantic'})[0].id,true)")
    pg.reload(); pg.wait_for_selector(".cta")
    ok(pg.evaluate(f"memQuery(DB.sessions[0],{{text:'player fix'}})[0].id") == first_id, "edit persists after reload")
    # regenerate the LAST reply; the edited first event belongs to reply 1 and must survive
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    pg.click("button[aria-label='Regenerate']"); pg.wait_for_selector("text=Reply 3."); pg.wait_for_timeout(400)
    texts = pg.evaluate("memQuery(DB.sessions[0],{layer:'episodic'}).map(r=>r.text)")
    ok(any("player fix" in t for t in texts) and any("clue 3" in t for t in texts) and not any("clue 2" in t for t in texts), f"player edit survives regenerate; regenerated memory shown: {texts}")
    pg.evaluate(f"memDelete(DB.sessions[0],'{first_id}')")
    ok(not any(r == first_id for r in pg.evaluate("memQuery(DB.sessions[0],{}).map(r=>r.id)")), "soft delete hides the record")
    pg.evaluate("memUndo(DB.sessions[0])")
    ok(any(r == first_id for r in pg.evaluate("memQuery(DB.sessions[0],{}).map(r=>r.id)")), "undo brings it back")
    ok(pg.evaluate("JSON.stringify(DB.sessions[0].mem).includes('player fix')") is False, "player edits never write into the v1 store (se.mem)")
    # refinements for Memory Studio (ChatGPT review)
    lk = pg.evaluate("memQuery(DB.sessions[0],{layer:'permanent'}).find(r=>r.kind==='canon'&&r.lock).id")
    r = pg.evaluate(f"memEdit(DB.sessions[0],'{lk}',{{text:'changed'}})")
    ok(r["applied"] is False and r["reason"] == "locked" and not any(o["id"] == lk for o in pg.evaluate("DB.sessions[0].memEdits.ops")), "editing locked canon reports applied:false/locked and stores nothing")
    r = pg.evaluate(f"memDelete(DB.sessions[0],'{first_id}')")
    ok(r["applied"] and r["record"]["deleted"], "a successful change reports applied:true with the resulting record")
    only = pg.evaluate("memQuery(DB.sessions[0],{deleted:'only'}).map(r=>r.id)")
    ok(only == [first_id], f"deleted:'only' lists just deleted records: {only}")
    pg.evaluate(f"memRestore(DB.sessions[0],'{first_id}')")
    h = pg.evaluate(f"memHistory(DB.sessions[0],'{first_id}').map(x=>x.op)")
    ok(h[:1] == ["edit"] and "delete" in h and h[-1] == "restore", f"memHistory gives the full edit history: {h}")
    turns = pg.evaluate("memQuery(DB.sessions[0],{layer:'episodic'}).map(r=>r.t)")
    lo = min(turns); ok(all(r <= lo for r in pg.evaluate(f"memQuery(DB.sessions[0],{{layer:'episodic',asOf:{lo}}}).map(r=>r.t)")), "asOf hides memories from later turns")
    # conflicts list + resolve
    pg.evaluate("DB.sessions[0].memDiag=(DB.sessions[0].memDiag||[]).concat([{t:3,rp:{ok:true,conflicts:['scene: narrator said kitchen, step said harbor office']}}])")
    c = pg.evaluate("memConflicts(DB.sessions[0])")
    ok(len(c) == 1 and c[0]["id"] == "c3", "memConflicts lists open conflicts")
    rr = pg.evaluate(f"memResolve(DB.sessions[0],'c3','edited',{{edit:{{id:'{first_id}',patch:{{where:'harbor office'}}}}}})")
    ok(rr["ok"] and rr["edit"]["applied"] and pg.evaluate("memConflicts(DB.sessions[0]).length") == 0 and pg.evaluate(f"memQuery(DB.sessions[0],{{}}).find(r=>r.id==='{first_id}').where") == "harbor office", "memResolve closes a conflict and can apply a fix through memEdit")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
