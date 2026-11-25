"""Quick Create extension 6 with a mock model: previewing and applying changes to a playthrough already in progress. The view lists what
can change and what is frozen; the start of the story, past events and recorded outcomes can't change; gameplay and protected memories
can only be added to; nothing changes before apply; apply is atomic and never touches turns; a stale preview is refused; undo restores.
No network, no paid calls. Run: python tests/quick_create_change_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8921
FX = json.load(open(os.path.join(HERE, "fixtures", "fanfic-ember.json")))
fails = []; errs = []; MODE = {"change": {}}; SEEN = {"change": ""}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
BP = {"title": "Second Term", "premise": "A second chance.", "modes": ["takeover"], "takeover": "char:ember:kael", "player": {"name": "Kael Ashveil", "desc": "x", "age": 19},
      "start": {"ch": 0}, "pov": {"mode": "second"}, "romance": {"pref": "none", "pacing": "slow"}, "characters": [], "notes": [], "opening": "Bells ring.", "sources": [], "uncertain": [],
      "gameplay": {"stats": [{"id": "courage", "name": "Courage", "min": 0, "max": 100, "start": 10}], "quests": [{"id": "q1", "title": "First", "steps": ["a"]}]},
      "memory": {"mode": "on", "notes": [{"text": "Lys survives the fire.", "who": ["Lys"]}]}, "director": {"pacing": "slow"}, "styleProfile": {"tense": "past"}}
def model(route):
    b = json.loads(route.request.post_data); sysm = b["messages"][0]["content"]
    if b.get("stream"):
        return route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": "Bells ring.\n\n[[META]]\nENDING: none"}}]}) + "\n\ndata: [DONE]\n\n")
    if "You set up an interactive fanfiction" in sysm: txt = json.dumps(BP)
    elif "REST of an interactive fanfiction story" in sysm: SEEN["change"] = sysm + b["messages"][1]["content"]; txt = json.dumps(MODE["change"])
    else: txt = "- ok"
    route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": txt}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 900, "completion_tokens": 300}}))
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "universes": {"ember": FX["universe"]}, "stories": [], "sessions": []}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
SE = "DB.sessions[0]"
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept()); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    J = lambda e, *a: pg.evaluate(e, *a)
    pv = J("qcPreview({sourceTitle:'Ember',concept:'x',character:'Kael'},{universeId:'ember'})"); c = J("bp=>qcCommit(bp)", pv["blueprint"]); ok(c["applied"], "story created " + str(c.get("reason")))
    J("play(DB.stories[0],{})"); pg.wait_for_function("!busy&&DB.sessions.length===1&&DB.sessions[0].turns.length>=2", timeout=10000)
    J(f"(()=>{{const se={SE};se.canon=SFFan.setPosition(se.canon,{{ch:6,order:2}}).canon;se.game=SFGame.change(se.game,'courage',15).game;save();return null}})()")
    v = J(f"qcStoryView({SE})")
    ok(v["frozen"]["pastEvents"] == ["ev:ember:1", "ev:ember:2"] and "ev:ember:3" in v["frozen"]["upcomingEvents"] and v["gameplay"]["stats"][0]["value"] == 25, "the view separates past and upcoming events and shows current values")
    ok(v["memory"]["notes"] == [{"text": "Lys survives the fire.", "who": ["Lys"]}] and v["memory"]["mode"] == "on" and v["director"]["pacing"] == "slow", "the view shows protected memories and settings")
    T0 = J(f"JSON.stringify({SE}.turns)"); P0 = J(f"JSON.stringify(qcSeParts({SE}))")
    # AI change with mixed allowed / frozen / past parts
    MODE["change"] = {"set": {"romance.pacing": "fast", "rules.fates": "free", "takeover": "char:ember:lys", "locks": [{"kind": "event", "id": "ev:ember:1"}, {"kind": "event", "id": "ev:ember:3"}],
        "gameplay.stats.0.value": 90, "gameplay.stats.1": {"id": "wisdom", "name": "Wisdom", "min": 0, "max": 100, "start": 5},
        "gameplay.quests.1": {"id": "q2", "title": "Second", "steps": ["b"]}, "memory.notes.1": {"text": "Kael keeps his memories.", "who": ["Kael"]},
        "director.pacing": "fast", "styleProfile.humor": "dry", "appearance.cinematic.lighting": "night", "appearance.colors.accent": "#ff3366"}, "remove": ["memory.notes.0"]}
    est = J(f"qcEstimateChange({SE},'faster romance')"); ok(est["ok"] and est["maxOutputTokens"] == 900, "change has a preflight estimate")
    pr = J(f"qcChangePreview({SE},'faster romance, free fates, lock the trial, add wisdom')")
    paths = [x["path"] for x in pr["changes"]]; refused = " | ".join(x["path"] + ": " + x["reason"] for x in pr["refused"])
    ok("ev:ember:1" in SEEN["change"] and "never change what already happened" in SEEN["change"].lower(), "the model is told what is frozen")
    ok(pr["staged"] and "romance.pacing" in paths and "rules.fates" in paths and "director.pacing" in paths and "styleProfile.humor" in paths and "appearance.cinematic.lighting" in paths and "appearance.story.accent" in paths, "allowed changes are previewed " + str(paths))
    ok(any(x["path"] == "locks" and "already happened: ev:ember:1" in x["reason"] for x in pr["refused"]) and any(l == {"kind": "event", "id": "ev:ember:3"} for l in J(f"qcStoryView({SE})").get("locks", [])) is False, "a lock on a past event is refused; preview changes nothing yet")
    ok("takeover" in refused and "already played" in refused, "the start of the story can't change")
    ok("gameplay.stats.0" in refused and "memory.notes" in refused, "current values and protected memories can't be edited or removed " + refused)
    ok(J(f"JSON.stringify(qcSeParts({SE}))") == P0 and J(f"JSON.stringify({SE}.turns)") == T0, "nothing changes before apply")
    # protected memories: a pure add is allowed
    MODE["change"] = {"set": {"memory.notes.1": {"text": "Kael keeps his memories.", "who": ["Kael"]}, "gameplay.stats.1": {"id": "wisdom", "name": "Wisdom", "min": 0, "max": 100, "start": 5}, "gameplay.quests.1": {"id": "q2", "title": "Second", "steps": ["b"]},
        "romance.pacing": "fast", "locks": [{"kind": "event", "id": "ev:ember:3"}], "director.pacing": "fast", "styleProfile.humor": "dry", "appearance.cinematic.lighting": "night", "appearance.colors.accent": "#ff3366"}}
    pr = J(f"qcChangePreview({SE},'add things')"); ok(pr["staged"] and not pr["refused"], "a clean change has nothing refused " + str(pr["refused"]))
    # stale preview
    J(f"{SE}.memRecall=!{SE}.memRecall;null"); st = J(f"id=>qcChangeApply({SE},id)", pr["proposalId"]); J(f"{SE}.memRecall=!{SE}.memRecall;if(!{SE}.memRecall)delete {SE}.memRecall;null")
    ok(not st["applied"] and "changed since" in st["reason"], "a preview made stale by another change is refused")
    # failure rolls back
    pr = J(f"qcChangePreview({SE},'add things')"); ap0 = J("localStorage.getItem(apKey())")
    J("window.__qcChangeFail=true;null"); f = J(f"id=>qcChangeApply({SE},id)", pr["proposalId"]); J("window.__qcChangeFail=false;null")
    ok(not f["applied"] and J(f"JSON.stringify(qcSeParts({SE}))") == P0 and J("localStorage.getItem(apKey())") == ap0 and not J(f"({SE}.qcChanges||[]).length"), "a failed apply restores the playthrough and appearance")
    # apply
    pr = J(f"qcChangePreview({SE},'add things')"); a = J(f"id=>qcChangeApply({SE},id)", pr["proposalId"])
    v2 = J(f"qcStoryView({SE})")
    ok(a["applied"] and v2["romance"]["pacing"] == "fast" and {"kind": "event", "id": "ev:ember:3"} in v2["locks"] and v2["director"]["pacing"] == "fast" and v2["styleProfile"]["humor"] == "dry" and v2["appearance"]["cinematic"]["lighting"] == "night", "apply changes the rest of the story")
    ok([s["id"] for s in v2["gameplay"]["stats"]] == ["courage", "wisdom"] and v2["gameplay"]["stats"][0]["value"] == 25 and [q["id"] for q in v2["gameplay"]["quests"]] == ["q1", "q2"], "gameplay is added to; current values are kept")
    ok([n["text"] for n in v2["memory"]["notes"]] == ["Lys survives the fire.", "Kael keeps his memories."], "a new protected memory is added")
    ok(J(f"JSON.stringify({SE}.turns)") == T0 and v2["frozen"]["pastEvents"] == ["ev:ember:1", "ev:ember:2"] and J(f"{SE}.canon.mode.takeover") == "char:ember:kael", "turns, past events and the start are untouched")
    ok(J("JSON.parse(localStorage.getItem(apKey())).stories[DB.sessions[0].storyId].accent") == "#ff3366", "story appearance applied")
    ok(len(J(f"qcChangeHistory({SE})")) == 1, "the change is in the history")
    # undo
    u = J(f"qcChangeUndo({SE})"); ok(u["applied"] and J(f"JSON.stringify(qcSeParts({SE}))") == P0 and J("localStorage.getItem(apKey())") == ap0, "undo restores the playthrough and appearance")
    ok(J(f"qcChangeUndo({SE}).reason") == "nothing to undo", "nothing left to undo")
    # manual patch path + undo refused after later edits
    m = J(f"qcChangePreviewPatch({SE},{{set:{{'rules.romance':'free'}}}})"); J(f"id=>{{qcChangeApply({SE},id);return null}}", m["proposalId"])
    J(f"ffSetRule({SE},'fates','locked');null"); ok("changed since" in J(f"qcChangeUndo({SE}).reason"), "undo is refused once the story changed after the change")
    ok(J(f"qcChangePreviewPatch({SE},{{set:{{'rules.romance':'free'}}}}).reason") == "no change", "a change that changes nothing stages nothing")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
