"""ChatGPT's Quick Create screen driven end to end with a mock model and stubbed lookups: real estimates in the confirmation, locks make a
section read-only and block AI edits, staged proposals accept/reject, undo/redo, section regeneration, cancellation with a late reply,
a no-change edit shows no proposal, leaving with a pending proposal or during a request creates nothing, reviewed creation makes one story.
No network, no paid calls. Run: python tests/quick_create_ui_browser.py"""
import json, os, re, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8917
fails = []; errs = []; DIALOGS = []; HELD = []
MODE = {"hang": False, "edit": {"set": {"opening": "Rain on the windows."}}, "regen": {"value": "Snow falls on the academy."}}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
BP = {"title": "Second Term", "premise": "A second chance.", "modes": ["takeover"], "takeover": "char:ember-academy:kael-ashveil",
      "player": {"name": "Kael Ashveil", "desc": "remembers", "age": 19}, "start": {"ch": 0}, "pov": {"mode": "second"}, "romance": {"pref": "none", "pacing": "slow"},
      "characters": [{"name": "Lys", "role": "friend", "desc": "x"}], "notes": [], "gameplay": {"career": None}, "memory": {"recall": True},
      "opening": "Bells ring.", "styleProfile": {"tense": "past"}, "sources": ["f1"], "uncertain": []}
def reply(txt): return {"status": 200, "content_type": "application/json", "body": json.dumps({"choices": [{"message": {"content": txt}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 900, "completion_tokens": 300}})}
def model(route):
    sysm = json.loads(route.request.post_data)["messages"][0]["content"]
    if "You edit a fanfiction setup" in sysm: txt = json.dumps(MODE["edit"])
    elif "You rewrite ONE section" in sysm: txt = json.dumps(MODE["regen"])
    elif "You set up an interactive fanfiction" in sysm: txt = json.dumps(BP)
    else: txt = "- ok"
    if MODE["hang"]: HELD.append((route, txt)); return
    route.fulfill(**reply(txt))
def release():
    for route, txt in HELD:
        try: route.fulfill(**reply(txt))
        except Exception: pass
    HELD.clear(); MODE["hang"] = False
def on_dialog(d):
    DIALOGS.append((d.type, d.message)); d.accept()
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "stories": [], "sessions": []}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", on_dialog); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pg.evaluate("""searchWorks=async q=>[{t:'Ember Academy',ty:'Light novel',y:2019,a:'R. Vale',src:'AniList'}];
      wikiFind=async t=>({base:'https://ember-academy.fandom.com',name:'Ember Academy Wiki',pages:400});
      wikiSearch=async(b,q,n)=>q==='Kael Ashveil'?['Kael Ashveil']:['Ember Academy'];
      wikiPage=async(b,t)=>t==='Kael Ashveil'?{t,x:'Kael Ashveil is a second-year student.'}:{t,x:'Ember Academy is a school for fire mages.'};
      window.__back=0;window.qcMount=()=>{document.getElementById('qcroot')?.remove();const r=document.createElement('div');r.id='qcroot';document.body.prepend(r);SFFanUI.quickCreate(r,()=>window.__back++)};null""")
    R = "#qcroot "
    RT = "#qcroot"
    def B(t):
        pg.evaluate("document.querySelectorAll('#qcroot details').forEach(d=>d.open=true);null")
        return pg.locator(R + "button", has_text=re.compile("^" + re.escape(t) + "$"))
    status = lambda: pg.locator(R + "[role=status]").inner_text()
    def generate():
        pg.evaluate("qcMount();null")
        pg.locator(R + "label:has-text('Source title') input").fill("Ember Academy")
        pg.locator(R + "label:has-text('Character names') input").fill("Kael Ashveil")
        B("Research source").click(); pg.wait_for_selector(RT + " >> text=Source evidence")
        pg.locator(R + "label:has-text('Story concept') textarea").fill("save Lys")
        pg.locator(R + "label:has-text('Player character') textarea").fill("I take over Kael")
        B("Generate blueprint").click(); pg.wait_for_selector(RT + " >> text=3 · Review your blueprint")
    generate()
    est = pg.evaluate("qcEstimatePreview({sourceTitle:'Ember Academy',concept:'save Lys',character:'I take over Kael',preferences:''},{facts:QC.ctx.facts})")
    conf = [m for t, m in DIALOGS if "Estimated input tokens" in m]
    ok(conf and ("Estimated input tokens: %d" % est["inputTokens"]) in conf[-1] and "Maximum output tokens: 1800" in conf[-1], "generation asks with the real estimate first")
    # lock romance
    B("Lock romance").click()
    ok(B("Unlock romance").count() == 1 and B("Regenerate romance").count() == 0 and B("Apply romance").count() == 0 and pg.evaluate("QC.hist[QC.cur].now.locked") == ["romance"], "locking makes the section read-only and hides regeneration")
    MODE["edit"] = {"set": {"romance.pacing": "fast"}}
    pg.locator(R + "textarea[placeholder='Describe what to change']").fill("faster romance"); B("Preview changes").click()
    pg.wait_for_function("document.querySelector('#qcroot [role=status]').textContent.includes('locked')")
    ok("locked: romance" in status() and pg.locator(RT + " >> text=Proposed changes").count() == 0, "an AI edit on a locked section is refused with the reason shown")
    # staged edit: reject then accept, undo, redo
    MODE["edit"] = {"set": {"opening": "Rain on the windows."}}
    pg.locator(R + "textarea[placeholder='Describe what to change']").fill("rainy opening"); B("Preview changes").click(); pg.wait_for_selector(RT + " >> text=Proposed changes")
    ok(any("Maximum output tokens: 900" in m for t, m in DIALOGS), "edit asks with the edit estimate")
    B("Reject changes").click(); ok(pg.evaluate("QC.prop===null&&QC.hist[QC.cur].now.opening") == "Bells ring.", "reject keeps the previous blueprint")
    pg.locator(R + "textarea[placeholder='Describe what to change']").fill("rainy opening"); B("Preview changes").click(); pg.wait_for_selector(RT + " >> text=Proposed changes")
    B("Accept changes").click(); ok(pg.evaluate("QC.hist[QC.cur].now.opening") == "Rain on the windows.", "accept applies the proposal")
    B("Undo last edit").click(); ok(pg.evaluate("QC.hist[QC.cur].now.opening") == "Bells ring.", "undo steps back")
    B("Redo last edit").click(); ok(pg.evaluate("QC.hist[QC.cur].now.opening") == "Rain on the windows.", "redo steps forward")
    # regenerate one section (prompt dialog accepted with empty guidance)
    B("Regenerate opening").click(); pg.wait_for_selector(RT + " >> text=Proposed changes")
    ok(any(t == "prompt" for t, m in DIALOGS), "regeneration asks for optional guidance"); B("Accept changes").click()
    now = pg.evaluate("QC.hist[QC.cur].now"); ok(now["opening"] == "Snow falls on the academy." and now["romance"]["pacing"] == "slow", "regeneration changes only that section")
    # no-change edit shows no proposal
    MODE["edit"] = {"set": {}}
    pg.locator(R + "textarea[placeholder='Describe what to change']").fill("nothing"); B("Preview changes").click()
    pg.wait_for_function("!document.querySelector('#qcroot').textContent.includes('Cancel request')")
    ok(pg.locator(RT + " >> text=Proposed changes").count() == 0 and B("Create reviewed story").count() == 1, "an edit that changes nothing shows no Accept/Reject")
    # cancel with a late reply
    MODE["edit"] = {"set": {"opening": "Late."}}; MODE["hang"] = True
    pg.locator(R + "textarea[placeholder='Describe what to change']").fill("late"); B("Preview changes").click(); B("Cancel request").click()
    release(); time.sleep(0.5)
    ok("Previous blueprint retained" in status() and pg.evaluate("QC.prop===null&&QC.hist[QC.cur].now.opening") == "Snow falls on the academy." and pg.locator(RT + " >> text=Proposed changes").count() == 0, "cancel keeps the blueprint even when the reply arrives late")
    # leaving with a pending proposal
    MODE["edit"] = {"set": {"opening": "Pending."}}
    pg.locator(R + "textarea[placeholder='Describe what to change']").fill("pending"); B("Preview changes").click(); pg.wait_for_selector(RT + " >> text=Proposed changes")
    B("‹ Fanfiction Studio").click(); ok(pg.evaluate("__back") == 1 and pg.evaluate("QC.prop===null") and pg.evaluate("DB.stories.length") == 0, "leaving with a pending proposal discards it and creates nothing")
    # leaving during a request
    generate(); MODE["hang"] = True
    pg.locator(R + "textarea[placeholder='Describe what to change']").fill("x"); B("Preview changes").click(); B("Cancel request").wait_for()
    B("‹ Fanfiction Studio").click(); release(); time.sleep(0.5)
    ok(pg.evaluate("__back") == 2 and pg.evaluate("QC.prop===null") and pg.evaluate("DB.stories.length") == 0, "leaving during a request creates nothing, and the late reply is ignored")
    # reviewed creation
    generate(); B("Create reviewed story").click(); pg.wait_for_function("DB.stories.length===1")
    ok(pg.evaluate("DB.stories.length") == 1 and pg.evaluate("DB.stories[0].fanfic.styleProfile.tense") == "past", "reviewed creation makes exactly one story")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
