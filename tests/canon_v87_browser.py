"""v87 canon & instruction enforcement in the real app (simulated replies, throwaway story, no network).
Run: python tests/canon_v87_browser.py   (prints "ERRORS: []" when everything passes)"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8895
fails = []; errs = []; calls = []; MODE = {"fail": False, "canon": "Itachi | drift | made him openly cruel"}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
def model(route):
    b = json.loads(route.request.post_data); calls.append(b)
    if MODE["fail"]: return route.fulfill(status=500, body="boom")
    if not b.get("stream"):
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    n = len([c for c in calls if c.get("stream")])
    txt = 'Itachi | "Reply number %d."\n\n[[META]]\nSCENE: training ground | Itachi, Sasuke | dusk\nEVENTS: none\nLEARNED: none\nCANON: %s\nENDING: none' % (n, MODE["canon"])
    route.fulfill(status=200, content_type="text/event-stream",
                  body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\ndata: [DONE]\n\n")
filler = [{"role": "user", "text": "(OOC: from now on, never use the word suddenly)"}, {"role": "ai", "text": "Understood."}]
for i in range(40): filler += [{"role": "user", "text": "I keep training. " + "x " * 400}, {"role": "ai", "text": "Training continues. " + "y " * 400}]
ENTRIES = [{"k": "Chakra", "t": "Chakra is molded with hand seals.", "lock": True, "id": "rule-chakra"}] + \
          [{"k": "Clan %d" % i, "t": "Clan lore %d. " % i + "z " * 300, "a": True} for i in range(3)] + \
          [{"k": "Itachi, Itachi Uchiha", "t": "Itachi is secretly loyal to the Leaf.", "id": "itachi"},
           {"k": "Anna", "t": "Anna is the innkeeper.", "id": "anna"}]
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "globalNote": "Keep dialogue natural.",
        "notes": [{"id": "g-must", "text": "Never let anyone heal instantly.", "pri": "must", "scope": {"type": "always"}},
                  {"id": "g-kw", "text": "Sakura carries a red scarf.", "pri": "should", "scope": {"type": "keyword", "value": "Sakura"}}],
        "stories": [{"id": "s1", "kind": "story", "title": "Leaf", "canon": "Naruto", "follow": "strict", "setting": "Konoha.", "starts": [], "stats": [], "endings": [], "entries": ENTRIES, "styleSamples": [{"id": "ss1", "text": "Rain. Always rain. He counted the drops and lost count."}]}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Ren"}, "note": "Itachi must stay mysterious.", "dead": ["Shisui"],
                      "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Leaves fall."}] + filler,
                      "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
def sysmsg(): return [c for c in calls if c.get("stream")][-1]["messages"][0]["content"]
def lastuser(): return [c for c in calls if c.get("stream")][-1]["messages"][-1]["content"]
with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    ok(pg.evaluate("promptReport(DB.sessions[0])") is None, "promptReport is null before the first build")
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    pg.fill("#input", "I ask Itachi Uchiha about the mission."); pg.click("button[aria-label='Send']"); pg.wait_for_selector("text=Reply number 1"); pg.wait_for_timeout(500)
    S = sysmsg(); U = lastuser()
    blk = S.find("=== PLAYER INSTRUCTIONS AND LOCKED CANON ===")
    ok(blk > 0 and blk < S.find("Title: Leaf"), "player instructions block sits before the story setup")
    for t in ["Never let anyone heal instantly.", "Keep dialogue natural.", "Itachi must stay mysterious.", "Chakra is molded with hand seals."]:
        ok(t in S[blk:S.find("=== END ===")], "in the protected block: " + t[:40])
    ok("Sakura carries a red scarf." not in S, "keyword-scoped note left out when its keyword is absent")
    ok("never use the word suddenly" in S[blk:S.find("=== END ===")], "standing OOC from trimmed history kept as a direction")
    ok("PRIORITY when instructions or facts conflict" in S and S.find("PRIORITY") < blk, "precedence statement before the block")
    ok("re-check" in U and "Never let anyone heal instantly." in U, "must notes echoed in the final message")
    ok("CANON:" in S[S.find("[[META]]"):], "CANON line requested in the reply format")
    si = S.find("STYLE SAMPLES")
    ok(si > 0 and si < S.find("PRIORITY") and "He counted the drops" in S and "never copy" in S[si:si+600], "style samples sent every turn, with the writing rules, marked never-copy")
    ci = S.find("Canon notes (relevant to this scene)")
    ok(ci > 0 and S.find("Itachi is secretly loyal") > ci and "Anna is the innkeeper" not in S, "relevant canon retrieved by score; unrelated entry left out")
    R = pg.evaluate("promptReport(DB.sessions[0])")
    ok(R and R["canon"]["locked"] == ["rule-chakra"] and "itachi" in R["canon"]["included"], "report: locked and included canon ids")
    ok(any(d["id"] == "anna" for d in R["canon"]["dropped"]), "report: dropped canon with reason")
    ok(any(n["id"] == "g-kw" and not n["included"] for n in R["notes"]) and any(n["id"] == "legacy-story" and n["included"] for n in R["notes"]), "report: notes included and omitted")
    ok(R["trimmedTurns"] > 0 and R["standingOoc"] == ["from now on, never use the word suddenly"], f"report: {R['trimmedTurns']} old turns trimmed, standing OOC kept")
    dv = pg.evaluate("DB.sessions[0].divergences||[]")
    ok(len(dv) == 1 and dv[0]["entry"] == "Itachi" and dv[0]["kind"] == "drift" and dv[0]["status"] == "open" and dv[0]["turn"] == len(SEED["sessions"][0]["turns"]) + 1, f"divergence recorded on the reply's turn: {dv}")
    ok("[[META" not in pg.evaluate("DB.sessions[0].turns.at(-1).text") and "CANON" not in pg.evaluate("DB.sessions[0].turns.at(-1).text"), "CANON line kept out of the story text")
    # failed regeneration keeps the original reply's records
    before = pg.evaluate("JSON.stringify(DB.sessions[0].divergences)")
    MODE["fail"] = True; pg.click("button[aria-label='Regenerate']"); pg.wait_for_timeout(1500); MODE["fail"] = False
    ok(pg.evaluate("JSON.stringify(DB.sessions[0].divergences)") == before, "failed regeneration leaves divergence records unchanged")
    # committed regeneration adds the new version's records, tagged with its turn
    MODE["canon"] = "none"; pg.click("button[aria-label='Regenerate']"); pg.wait_for_selector("text=Reply number"); pg.wait_for_timeout(800)
    ok(pg.evaluate("DB.sessions[0].divergences.length") == 1, "regenerated reply with CANON: none adds nothing")
    # dead character speaking is flagged locally
    MODE["canon"] = "none"
    pg.evaluate("DB.sessions[0].dead=['Itachi'];save()")
    pg.fill("#input", "I wait."); pg.click("button[aria-label='Send']"); pg.wait_for_timeout(1500)
    ok(any("Itachi" == d["entry"] and "dead" in d["text"] for d in pg.evaluate("DB.sessions[0].divergences")), "dead character speaking flagged without a model call")
    # branch before the divergence drops it; original untouched
    orig = pg.evaluate("JSON.stringify(DB.sessions[0])")
    pg.evaluate("branchAt(DB.sessions[0],3)"); pg.wait_for_timeout(300)
    ok(pg.evaluate("(DB.sessions.at(-1).divergences||[]).length") == 0, "branch before the divergence has none")
    ok(pg.evaluate("JSON.stringify(DB.sessions[0])") == orig, "original unchanged by branching")
    # mandatory block too large: warn and do not send
    stream = lambda: len([c for c in calls if c.get("stream")])
    n0 = stream()
    pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log")
    pg.evaluate("DB.notes.push({id:'huge',text:'Q '.repeat(15000),pri:'must',scope:{type:'always'}});save()")
    pg.fill("#input", "I look around."); pg.click("button[aria-label='Send']")
    try: pg.wait_for_function("document.getElementById('toast').textContent.includes('too long to send')", timeout=20000); shown = True
    except Exception: shown = False
    pg.wait_for_timeout(500)
    ok(shown and stream() == n0, "oversized must-notes stop the send with a clear message (no story request made)")
    ok(pg.evaluate("document.querySelector('#input').value") == "I look around.", "the player's draft is kept")
    pg.evaluate("DB.notes=DB.notes.filter(n=>n.id!=='huge');save()")
    # optional sections give way when the prompt is too big; the protected block never does
    pg.evaluate("DB.sessions[0].mems=[{t:'old',x:'M '.repeat(3000)}];DB.saver=2;save()")
    pg.evaluate("(()=>{const se=DB.sessions[0],st=DB.stories[0];se.wn='W '.repeat(20000);buildMsgs(se,st,se.turns.slice(),'test');delete se.wn})()")
    R = pg.evaluate("promptReport(DB.sessions[0])")
    ok("wiki notes" in R["trimmed"] and R["total"] <= R["cap"] and not any(s["keep"] and not s["sent"] for s in R["sections"]), f"oversized prompt trims optional sections only: {R['trimmed']}")
    br.close()
srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
