"""Living characters in the app: relationships evolve from replies, journals, agendas, voice warnings. No network. Run: python tests/character_app_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8887
fails = []; errs = []; N = {"n": 0}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
R = ['Rae | "Hold on!" Rae saves Dale from the falling crates.\n\n[[META]]\nEVENTS: 4 | action | Rae, Dale | harbor | Rae saves Dale from the falling crates | none\nSCENE: harbor | Rae, Dale | night\nENDING: none',
     'Mira | "Yeah, gonna be fine, dude." Dale lies to Rae about the ledger.\n\n[[META]]\nEVENTS: 3 | action | Dale, Rae | harbor | Dale lies to Rae about the ledger | none\nSCENE: harbor | Rae, Dale, Mira | night\nENDING: none']
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"): return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    txt = R[min(N["n"], 1)]; N["n"] += 1
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\ndata: [DONE]\n\n")
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "memv2": True, "cast": {"Mira": {"t": ["formal", "patient"], "v": "formal, precise"}},
                      "npcs": {"Dale": {"goals": ["Hide the debt"], "schedule": [{"day": 0, "where": "office", "doing": "works late"}, {"day": 2, "where": "cove", "doing": "pays the smugglers"}]}},
                      "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    pg.fill("#input", "Look out!"); pg.click("button[aria-label='Send']"); pg.wait_for_selector("text=Hold on!"); pg.wait_for_timeout(500)
    rel = pg.evaluate("chRelationships(DB.sessions[0])")
    ok(any(r["id"] == "rel:Dale>Rae" and r["trust"] > 0 for r in rel), "being saved raised Dale's trust in Rae after the reply")
    pg.fill("#input", "Hm."); pg.click("button[aria-label='Send']"); pg.wait_for_selector("text=gonna be fine"); pg.wait_for_timeout(500)
    rel = pg.evaluate("chRelationships(DB.sessions[0])")
    ok(any(r["id"] == "rel:Rae>Dale" and r["trust"] < 0 for r in rel), "the lie lowered Rae's trust in Dale")
    ok(len(pg.evaluate("chHistory(DB.sessions[0],'Rae','Dale')")) >= 1, "history with evidence per direction")
    n0 = len(rel); pg.evaluate("chEvolve(DB.sessions[0])"); ok(len(pg.evaluate("chRelationships(DB.sessions[0])")) == n0 and pg.evaluate("chEvolve(DB.sessions[0]).applied") == 0, "re-running changes nothing")
    v = pg.evaluate("DB.sessions[0].turns.filter(t=>t.role==='ai').pop().voice||[]")
    ok(any("slang" in x["text"] for x in v), f"voice warning stored on the reply: {[x['text'][:40] for x in v]}")
    ok(any(x["role"] == "did" for x in pg.evaluate("chJournal(DB.sessions[0],'Dale')")), "journal lists what Dale did")
    ag = pg.evaluate("chAgenda(DB.sessions[0],'Dale',0,3)")
    ok(ag["where"] == "cove" and ag["developments"], "NPC agenda advances with story days")
    pg.reload(); pg.wait_for_selector(".cta"); ok(len(pg.evaluate("DB.sessions[0].rel2")) == n0, "relationships saved")
    r = pg.evaluate("chSetRelationship(DB.sessions[0],'Rae','Dale',{trust:50,kinds:['ally']})")
    ok(r["applied"] and pg.evaluate("chRelationships(DB.sessions[0]).find(x=>x.id==='rel:Rae>Dale').trust") == 50, "player can set a relationship")
    ok(pg.evaluate("chUndo(DB.sessions[0]).applied") and pg.evaluate("chRelationships(DB.sessions[0]).find(x=>x.id==='rel:Rae>Dale').trust") < 0, "undo restores it")
    ok(not pg.evaluate("chSetRelationship(DB.sessions[0],'Rae','Rae',{}).applied"), "invalid change rejected")
    # regeneration safety: regenerate the lie reply -> its relationship change disappears
    t_before = pg.evaluate("chRelationships(DB.sessions[0]).find(x=>x.id==='rel:Rae>Dale').trust")
    N["n"] = 0; pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    pg.click("button[aria-label='Regenerate']"); pg.wait_for_timeout(1500)
    rd = pg.evaluate("chRelationships(DB.sessions[0]).find(x=>x.id==='rel:Rae>Dale')")
    ok(not any(h["event"] for h in rd["history"] if "lie" in str(h.get("why",""))) or rd["trust"] > t_before, f"regenerating the lie removes its effect (trust {t_before} -> {rd['trust']})")
    # off-screen developments only when story time advances
    ok(pg.evaluate("chAgendaLog(DB.sessions[0]).length") == 0, "no developments without story time passing")
    pg.evaluate("DB.sessions[0].turns.filter(t=>t.role==='user').pop().worldDays=3;chAdvance(DB.sessions[0],DB.sessions[0].turns.filter(t=>t.role==='ai').pop());save()")
    ok(any("pays the smugglers" in x["text"] for x in pg.evaluate("chAgendaLog(DB.sessions[0])")), "days passing logs Dale's off-screen development")
    jr = [x["role"] for x in pg.evaluate("chJournal(DB.sessions[0],'Dale')")]
    ok("did" in jr and "feels" in jr and "intends" in jr, f"journal: did, feels, intends ({sorted(set(jr))})")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
