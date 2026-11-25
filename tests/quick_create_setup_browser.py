"""Quick Create extension 3 with a mock model: a blueprint with custom gameplay, memory mode + protected notes, cinematic preset/settings,
story appearance and the extended style profile is validated by the real engines, committed, and inherited by the first playthrough.
A failure after the appearance write restores both the stories and the appearance settings. No network, no paid calls.
Run: python tests/quick_create_setup_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8918
fails = []; errs = []; SEEN = {"prompt": "", "setup": ""}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
BP = {"title": "Second Term", "premise": "A second chance.", "modes": ["takeover"], "takeover": "char:ember-academy:kael-ashveil",
      "player": {"name": "Kael Ashveil", "desc": "remembers", "age": 19}, "start": {"ch": 0}, "pov": {"mode": "second"}, "romance": {"pref": "none", "pacing": "slow"},
      "characters": [], "notes": [], "opening": "Bells ring.", "sources": ["f1"], "uncertain": [],
      "gameplay": {"career": None, "stats": [{"id": "courage", "name": "Courage", "min": 0, "max": 100, "start": 10}],
                   "quests": [{"id": "save-lys", "title": "Save Lys", "steps": ["Find her", "Stop the fire"], "reward": {"xp": 50, "courage": 5}}],
                   "milestones": [{"id": "brave", "title": "Brave", "when": {"stat": "courage", "op": ">=", "value": 50}}],
                   "rules": [{"id": "ghost", "when": {"stat": "ghost", "op": ">", "value": 1}}]},
      "memory": {"mode": "app", "recall": True, "notes": [{"text": "Lys survives the fire in this story.", "who": ["Lys"]}]},
      "appearance": {"layout": "visual-novel", "preset": "noir", "cinematic": {"lighting": "night", "overlay": "lava"}, "colors": {"accent": "#ff3366", "bg": "red"}},
      "styleProfile": {"tense": "past", "balance": "dialogue", "innerMonologue": "frequent", "humor": "dry", "suspense": "high", "rhythm": "short"}}
def model(route):
    b = json.loads(route.request.post_data); sysm = b["messages"][0]["content"]
    if b.get("stream"):
        SEEN["prompt"] = sysm
        return route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": "Bells ring.\n\n[[META]]\nENDING: none"}}]}) + "\n\ndata: [DONE]\n\n")
    if "You set up an interactive fanfiction" in sysm: SEEN["setup"] = sysm; txt = json.dumps(BP)
    else: txt = "- ok"
    route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": txt}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 900, "completion_tokens": 300}}))
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "stories": [], "sessions": []}
FACTS = [{"id": "f1", "text": "Kael Ashveil is a second-year student.", "source": {"title": "Wiki: Kael", "url": "https://ember-academy.fandom.com/wiki/Kael_Ashveil"}, "confidence": "confirmed", "charId": "char:ember-academy:kael-ashveil", "charName": "Kael Ashveil"}]
INPUT = {"sourceTitle": "Ember Academy", "concept": "save Lys", "character": "I take over Kael"}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    J = lambda e, *a: pg.evaluate(e, *a)
    pv = J("([i,f])=>qcPreview(i,{facts:f})", [INPUT, FACTS]); B = pv["blueprint"]; iss = " | ".join(pv["issues"])
    ok(pv["ok"] and "lighting: night" not in "" and "noir" in SEEN["setup"] and "innerMonologue" in SEEN["setup"], "the setup prompt lists the engines' real presets and style options")
    ok(B["gameplay"]["stats"][0]["id"] == "courage" and B["gameplay"]["milestones"][0]["id"] == "brave" and not B["gameplay"]["rules"] and "rule ghost" in iss, "gameplay validated by the engine; a rule on an unknown stat is reported")
    ok(B["memory"]["mode"] == "on" and B["memory"]["notes"][0]["text"].startswith("Lys survives") and "recall needs" in iss, "memory mode real values; recall turns structured memory on")
    ok(B["appearance"]["preset"] == "noir" and B["appearance"]["cinematic"] == {"lighting": "night"} and B["appearance"]["colors"] == {"accent": "#ff3366"} and "cinematic.overlay" in iss and "colors.bg" in iss, "appearance values checked one by one; bad ones reported")
    ok(B["styleProfile"]["innerMonologue"] == "frequent" and B["styleProfile"]["rhythm"] == "short", "extended style profile kept")
    # failure after the appearance write restores everything
    ap0 = J("localStorage.getItem(apKey())"); db0 = J("JSON.stringify({s:DB.stories,u:DB.universes||{}})")
    J("window.__qcFailAfterAppearance=true;null"); f = J("bp=>qcCommit(bp)", B)
    ok(not f["applied"] and J("localStorage.getItem(apKey())") == ap0 and J("JSON.stringify({s:DB.stories,u:DB.universes||{}})") == db0, "a failure after the appearance write restores stories and appearance")
    ok(J("bp=>SFQuick.validate(bp,qcCtx(QC.ctx.universe,QC.ctx.facts)).blueprint.appearance.preset", B) == "noir", "validating again keeps the preset")
    J("window.__qcFailAfterAppearance=false;null"); c = J("bp=>qcCommit(bp)", B); sid = c.get("storyId")
    ok(c["applied"], "commit succeeds " + str(c.get("reason")))
    ap = json.loads(J("localStorage.getItem(apKey())") or "{}")
    ok(ap.get("stories", {}).get(sid, {}).get("accent") == "#ff3366", "story appearance saved in the story scope")
    st = J("DB.stories[0]"); g = st["blueprint"]["game"]
    ok(g and g["enabled"] and "courage" in g["stats"] and any(r["id"] == "milestone:brave" for r in g["rules"]) and g["quests"][0]["id"] == "save-lys", "story keeps the built game")
    J("play(DB.stories[0],{})"); pg.wait_for_function("!busy&&DB.sessions.length===1&&DB.sessions[0].turns.length>=2", timeout=10000)
    se = J("""(()=>{const se=DB.sessions[0];const notes=SFMem2.query(memView(se),{}).filter(r=>r.id==='qcnote0');return{m:se.memv2,r:se.memRecall,g:!!(se.game&&se.game.enabled&&se.game.stats.courage),cv:se.cv&&se.cv.settings,pre:se.cv&&se.cv.preset,n:notes.map(r=>({pin:r.pin,lock:r.lock,layer:r.layer,src:r.src}))}})()""")
    ok(se["m"] is True and se["r"] is True, "first playthrough turns on structured memory and recall")
    ok(se["g"], "first playthrough starts the custom game")
    ok(se["cv"]["layout"] == "visual-novel" and se["cv"]["lighting"] == "night" and se["cv"].get("overlay") == "film-grain" and se["cv"].get("dialogueBox") == "minimal", "first playthrough uses the cinematic preset and settings " + str(se["cv"]))
    ok(se["n"] == [{"pin": True, "lock": True, "layer": "permanent", "src": "player"}], "protected notes are pinned, locked player memories " + str(se["n"]))
    ok("inner monologue" in SEEN["prompt"] and "dry humor" in SEEN["prompt"] and "short sentence rhythm" in SEEN["prompt"] and "dialogue-led" in SEEN["prompt"], "extended style reaches the narrator")
    ok("GAMEPLAY STATE" in SEEN["prompt"] and "Courage" in SEEN["prompt"], "the game reaches the narrator")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
