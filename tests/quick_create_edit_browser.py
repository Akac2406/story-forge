"""Quick Create extensions 1-2 with a mock model: preflight estimates send nothing, cancellation keeps the previous blueprint (even when a late
reply arrives), AI edits are staged until accepted, locks are preserved by edits and regeneration, section regeneration, undo/redo scoped per
blueprint id, and the UI's keep-the-proposal path stays consistent. No network, no paid calls.
Run: python tests/quick_create_edit_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8916
fails = []; errs = []; MODE = {"hang": False, "edit": {"set": {"romance.pacing": "fast"}}, "regen": {"value": "Snow falls on the academy."}}; HELD = []; CALLS = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
BP = {"title": "Second Term", "premise": "A second chance.", "modes": ["takeover", "fixit"], "takeover": "char:ember-academy:kael-ashveil",
      "player": {"name": "Kael Ashveil", "desc": "remembers", "age": 17}, "start": {"ch": 0}, "pov": {"mode": "second"}, "romance": {"pref": "none", "pacing": "slow"},
      "characters": [{"name": "Lys", "role": "friend", "desc": "x"}], "notes": [{"text": "Kael is a student", "cite": ["f1"]}], "gameplay": {"career": None},
      "memory": {"recall": True}, "opening": "Bells ring.", "styleProfile": {"tense": "past"}, "sources": ["f1"], "uncertain": [], "locked": ["opening"], "id": "evil"}
def reply(txt): return {"status": 200, "content_type": "application/json", "body": json.dumps({"choices": [{"message": {"content": txt}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 900, "completion_tokens": 300}})}
def model(route):
    sysm = json.loads(route.request.post_data)["messages"][0]["content"]; CALLS.append(sysm[:40])
    if "You edit a fanfiction setup" in sysm: txt = json.dumps(MODE["edit"])
    elif "You rewrite ONE section" in sysm: txt = json.dumps(MODE["regen"])
    elif "You set up an interactive fanfiction" in sysm: txt = json.dumps(BP)
    else: txt = "- ok"
    if MODE["hang"]: HELD.append((route, txt)); return
    route.fulfill(**reply(txt))
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "stories": [], "sessions": []}
FACTS = [{"id": "f0", "text": "Ember Academy is a light novel.", "source": {"title": "AniList"}, "confidence": "confirmed"},
         {"id": "f1", "text": "Kael Ashveil is a second-year student.", "source": {"title": "Wiki: Kael", "url": "https://ember-academy.fandom.com/wiki/Kael_Ashveil"}, "confidence": "confirmed", "charId": "char:ember-academy:kael-ashveil", "charName": "Kael Ashveil"}]
INPUT = {"sourceTitle": "Ember Academy", "concept": "save Lys", "character": "I take over Kael"}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept()); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    J = lambda expr, *a: pg.evaluate(expr, *a)
    # (1) preflight estimates send nothing and match the real request
    est = J("([i,f])=>qcEstimatePreview(i,{facts:f})", [INPUT, FACTS])
    ok(est["ok"] and est["inputTokens"] > 0 and est["maxOutputTokens"] == 1800 and est["requests"] == 1 and not CALLS, "preview estimate is computed without any request")
    pv = J("([i,f])=>qcPreview(i,{facts:f})", [INPUT, FACTS]); bp = pv["blueprint"]
    ok(pv["ok"] and pv["estimate"]["inputTokens"] == est["inputTokens"], "estimate matches the request actually sent")
    ok(bp["id"] != "evil" and bp["id"].startswith("qc") and "locked" not in bp, "the model cannot choose the blueprint id or locks")
    n = len(CALLS); ee = J("bp=>qcEstimateEdit(bp,'make the romance faster')", bp); er = J("bp=>qcEstimateRegenerate(bp,'opening')", bp)
    ok(ee["ok"] and ee["maxOutputTokens"] == 900 and er["ok"] and er["inputTokens"] > 0 and len(CALLS) == n, "edit and regenerate estimates send nothing")
    # cancellation keeps the previous blueprint, even if the reply arrives late
    MODE["hang"] = True
    r = J("bp=>{const ac=new AbortController();const p=qcEdit(bp,'faster',{signal:ac.signal});setTimeout(()=>ac.abort(),300);return p}", bp)
    for route, txt in HELD:
        try: route.fulfill(**reply(txt))
        except Exception: pass
    HELD.clear(); MODE["hang"] = False; time.sleep(0.3)
    ok(r["reason"] == "cancelled" and J("QC.prop===null") and J("qcUndo().reason") == "nothing to undo", "a cancelled edit stages nothing and leaves history unchanged")
    MODE["hang"] = True
    r2 = J("([i,f])=>{const ac=new AbortController();const p=qcPreview(i,{facts:f,signal:ac.signal});setTimeout(()=>ac.abort(),300);return p}", [INPUT, FACTS])
    for route, txt in HELD:
        try: route.fulfill(**reply(txt))
        except Exception: pass
    HELD.clear(); MODE["hang"] = False; time.sleep(0.3)
    ok(r2["reason"] == "cancelled" and J("QC.cur") == bp["id"], "a cancelled preview keeps the previous blueprint as current")
    # (2) staged edits
    ed = J("bp=>qcEdit(bp,'make the romance faster')", bp)
    ok(ed["staged"] and ed["proposalId"] and ed["blueprint"]["romance"]["pacing"] == "fast" and J("qcUndo(QC.cur)") ["discarded"] == ed["proposalId"], "edits are staged; undo with a pending proposal discards it")
    ok(not J("id=>qcAccept(id).ok", ed["proposalId"]), "a discarded proposal cannot be accepted")
    ed = J("bp=>qcEdit(bp,'make the romance faster')", bp); rj = J("id=>qcReject(id)", ed["proposalId"])
    ok(rj["ok"] and rj["blueprint"]["romance"]["pacing"] == "slow" and J("qcUndo().reason") == "nothing to undo", "rejecting returns the previous blueprint and records nothing")
    ed = J("bp=>qcEdit(bp,'make the romance faster')", bp); ac = J("id=>qcAccept(id)", ed["proposalId"]); b1 = ac["blueprint"]
    ok(ac["ok"] and b1["romance"]["pacing"] == "fast" and b1["id"] == bp["id"], "accepting applies the change and keeps the id")
    # locks
    lk = J("bp=>qcLock(bp,['romance','sources'])", b1); b2 = lk["blueprint"]
    ok(lk["ok"] and b2["locked"] == ["romance"], "lock a section (protected sources are not lockable paths)")
    MODE["edit"] = {"set": {"romance.pacing": "slow", "opening": "Rain."}}
    e2 = J("bp=>qcEdit(bp,'slow romance and rainy opening')", b2)
    ok(not e2["ok"] and e2["reason"].startswith("locked: romance") and J("QC.prop===null"), "an AI edit touching a locked section is refused whole")
    ok("Locked paths" in J("bp=>SFQuick.editPrompt(bp,'x')[0].content", b2), "the model is told which paths are locked")
    ok(J("bp=>qcRegenerate(bp,'romance')", b2)["reason"].startswith("locked: romance"), "regenerating a locked section is refused without a request")
    MODE["edit"] = {"set": {"locked": []}}; ok(not J("bp=>qcEdit(bp,'unlock everything')", b2)["ok"], "the model cannot remove locks")
    ok(not J("bp=>qcApply(bp,{set:{'romance.pacing':'slow'}})", b2)["ok"] and J("bp=>qcApply(bp,{set:{'romance.pacing':'natural'}},{force:true}).blueprint.romance.pacing", b2) == "natural", "player's direct edit needs force on a locked path")
    J("qcUndo();null")
    # regeneration of one section, staged; locked section untouched
    rg = J("bp=>qcRegenerate(bp,'opening',{instruction:'wintry'})", b2)
    ok(rg["staged"] and [d["path"] for d in rg["diff"]] == ["opening"] and rg["blueprint"]["opening"] == "Snow falls on the academy." and rg["blueprint"]["romance"] == b2["romance"], "regenerate changes only that section")
    # UI compatibility: keeping the proposal's blueprint without qcAccept still records history
    b3 = rg["blueprint"]; ap = J("bp=>qcApply(bp,{set:{title:'Third Term'}})", b3)
    ok(ap["ok"] and J("qcUndo().blueprint.opening") == "Snow falls on the academy." and J("qcUndo().blueprint.opening") == "Bells ring.", "a kept proposal is accepted on the next change, so undo walks back through it")
    # redo
    ok(J("qcRedo().blueprint.opening") == "Snow falls on the academy." and J("qcRedo().blueprint.title") == "Third Term" and J("qcRedo().reason") == "nothing to redo", "redo walks forward again")
    J("qcUndo();null"); J("bp=>{qcApply(bp,{set:{premise:'New.'}});return null}", b3)
    ok(J("qcRedo().reason") == "nothing to redo", "a new change clears redo")
    # per-blueprint history
    old = bp["id"]; pv2 = J("([i,f])=>qcPreview(i,{facts:f})", [INPUT, FACTS])
    ok(pv2["blueprint"]["id"] != old and J("qcUndo().reason") == "nothing to undo" and J("id=>qcUndo(id).ok", old), "undo history is kept per blueprint id")
    # commit drops nothing it shouldn't; locks don't leak into the story
    c = J("bp=>qcCommit(bp)", pv2["blueprint"]); ok(c["applied"] and J("QC.prop===null&&QC.cur===null"), "commit ends the session")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
