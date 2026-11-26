"""ChatGPT's Quick Create screens for extensions 3-6, driven end to end with a mock model and stubbed lookups: spoiler limit and coverage in
the research panel, refresh, structured gameplay and style editors, drafts saved and loaded across a reload, reviewed creation, and the
AI Story Architect (preview with refused list, apply, stale preview, history, undo). No network, no paid calls.
Run: python tests/quick_create_ui2_browser.py"""
import json, os, re, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8922
fails = []; errs = []; MODE = {"change": {}}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
BP = {"title": "Second Term", "premise": "A second chance.", "modes": ["takeover"], "takeover": "char:ember-academy:kael-ashveil", "player": {"name": "Kael Ashveil", "desc": "x", "age": 19},
      "start": {"ch": 0}, "pov": {"mode": "second"}, "romance": {"pref": "none", "pacing": "slow"}, "characters": [], "notes": [], "opening": "Bells ring.", "sources": [], "uncertain": [],
      "gameplay": {"stats": [{"id": "courage", "name": "Courage", "min": 0, "max": 100, "start": 10}]}, "styleProfile": {"tense": "past"}}
def model(route):
    b = json.loads(route.request.post_data); sysm = b["messages"][0]["content"]
    if b.get("stream"):
        return route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": "Bells ring.\n\n[[META]]\nENDING: none"}}]}) + "\n\ndata: [DONE]\n\n")
    if "You set up an interactive fanfiction" in sysm: txt = json.dumps(BP)
    elif "REST of an interactive fanfiction story" in sysm: txt = json.dumps(MODE["change"])
    elif "You edit a fanfiction setup" in sysm: txt = json.dumps(MODE.get("edit") or {"set": {}})
    else: txt = "- ok"
    route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": txt}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 900, "completion_tokens": 300}}))
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "stories": [], "sessions": []}
STUBS = """window.__calls=0;searchWorks=async q=>{__calls++;return[{t:'Ember Academy',ty:'Light novel',y:2019,a:'R. Vale',src:'AniList'}]};
  wikiFind=async t=>({base:'https://ember-academy.fandom.com',name:'Ember Academy Wiki',pages:400});
  wikiSearch=async(b,q,n)=>q==='Kael Ashveil'?['Kael Ashveil']:['Ember Academy','Fire Trial'];
  wikiPage=async(b,t)=>t==='Kael Ashveil'?{t,x:'Kael Ashveil is a second-year student.'}:t==='Fire Trial'?{t,x:'In chapter 40 Lys dies in the fire trial.'}:{t,x:'Ember Academy is a school for fire mages.'};
  window.__back=0;window.qcMount=()=>{document.getElementById('qcroot')?.remove();const r=document.createElement('div');r.id='qcroot';document.body.prepend(r);SFFanUI.quickCreate(r,()=>window.__back++)};null"""
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept()); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta"); pg.evaluate(STUBS)
    J = lambda e, *a: pg.evaluate(e, *a); R = "#qcroot "; RT = "#qcroot"
    def B(t, root=R):
        pg.evaluate("document.querySelectorAll('#qcroot details').forEach(d=>d.open=true);null")
        return pg.locator(root + "button", has_text=re.compile("^" + re.escape(t) + "$"))
    lab = lambda t, tag="input": pg.locator(R + "label:has-text('" + t + "') " + tag).first
    J("qcMount();null")
    lab("Source title").fill("Ember Academy"); lab("Read up to chapter").fill("10"); lab("Read up to chapter").dispatch_event("change")
    lab("Character names").fill("Kael Ashveil"); B("Research source").click(); pg.wait_for_selector(RT + " >> text=Source evidence")
    txt = pg.locator(RT).inner_text()
    ok("Chapter limit: 10 · Excluded: 1" in txt and "Coverage: " in txt and "confirmed" in txt and "chapter 40" not in txt, "research panel shows the spoiler limit, coverage and confidence; later facts hidden")
    B("Refresh research").click(); pg.wait_for_function("__calls===2"); pg.wait_for_selector(RT + " >> text=Fresh")
    ok(J("__calls") == 2, "refresh research fetches again")
    lab("Story concept", "textarea").fill("save Lys"); lab("Player character", "textarea").fill("I take over Kael")
    B("Generate blueprint").click(); pg.wait_for_selector(RT + " >> text=3 · Review your blueprint")
    ok(J("QC.ctx.input.maxChapter") == 10, "the spoiler limit reaches generation")
    # open sections survive a redraw (Apply) and closed ones stay closed
    pg.evaluate("document.querySelectorAll('#qcroot details').forEach(d=>d.open=false);null")
    pg.locator(R + "details[data-qc-section='Gameplay'] > summary").click()
    pg.evaluate("[...document.querySelectorAll('#qcroot button')].find(b=>b.textContent==='Apply gameplay').click();null"); pg.wait_for_timeout(200)
    ok(J("document.querySelector(\"#qcroot details[data-qc-section='Gameplay']\").open") and not J("document.querySelector(\"#qcroot details[data-qc-section='Canon']\").open"), "an open section stays open after Apply; closed sections stay closed")
    # structured gameplay editor: add a stat
    B("Add Stat").click()
    exact = lambda t: pg.locator(R + "label").filter(has_text=re.compile("^" + t + "$")).locator("input")
    exact("ID").last.fill("wisdom"); exact("Name").last.fill("Wisdom"); B("Apply gameplay").click()
    ok([s["id"] for s in J("QC.hist[QC.cur].now.gameplay.stats")] == ["courage", "wisdom"], "structured gameplay editor adds a stat through the engine")
    pg.evaluate("document.querySelectorAll('#qcroot details').forEach(d=>d.open=true);null"); pg.locator(R + "details[data-qc-section='Source style'] label").filter(has_text=re.compile("^Humor")).locator("select").select_option("dry"); B("Apply styleProfile").click()
    ok(J("QC.hist[QC.cur].now.styleProfile.humor") == "dry", "structured style editor applies a choice")
    # unapplied typing survives an unrelated redraw; create and draft save wait until it is applied or discarded
    pg.evaluate("document.querySelectorAll('#qcroot details').forEach(d=>d.open=true);null")
    op = pg.locator(R + "details[data-qc-section='Story'] textarea").nth(2); op.fill("Snow on the bell tower.")
    B("Lock romance").click(); pg.evaluate("document.querySelectorAll('#qcroot details').forEach(d=>d.open=true);null")
    ok(pg.locator(R + "details[data-qc-section='Story'] textarea").nth(2).input_value() == "Snow on the bell tower.", "unapplied typing survives an unrelated redraw")
    B("Create reviewed story").click(); ok("Apply or discard" in J("document.querySelector('#qcroot [role=status]').textContent") and J("DB.stories.length") == 0, "create waits until unapplied edits are applied or discarded")
    B("Discard unapplied edits").click(); pg.evaluate("document.querySelectorAll('#qcroot details').forEach(d=>d.open=true);null")
    ok(pg.locator(R + "details[data-qc-section='Story'] textarea").nth(2).input_value() == "Bells ring.", "discard restores the blueprint's value")
    B("Unlock romance").click()
    # skipped parts of an AI edit are shown with the proposal
    window_edit = {"set": {"opening": "Rain."}, "skipped": [{"request": "rename Kael", "reason": "the player is fixed"}]}
    MODE["edit"] = window_edit
    pg.locator(R + "textarea[placeholder='Describe what to change']").fill("rainy opening and rename Kael"); B("Preview changes").click(); pg.wait_for_selector(RT + " >> text=Proposed changes")
    ok("Skipped request: rename Kael — the player is fixed" in pg.locator(RT).inner_text(), "skipped parts of an AI edit are shown with the proposal")
    B("Reject changes").click()
    # draft save, reload, load
    lab("Draft name").fill("Ember draft"); B("Save draft").click()
    ok(J("qcDrafts().length") == 1 and J("qcDrafts()[0].maxChapter") == 10 and J("qcDrafts()[0].hasBlueprint"), "save draft from the screen")
    pg.reload(); pg.wait_for_selector(".cta"); pg.evaluate(STUBS); J("qcMount();null")
    B("Load draft").click(); pg.wait_for_selector(RT + " >> text=3 · Review your blueprint")
    ok([s["id"] for s in J("QC.hist[QC.cur].now.gameplay.stats")] == ["courage", "wisdom"] and J("QC.ctx.input.maxChapter") == 10, "a draft loads after a reload with its edits and spoiler limit")
    B("Create reviewed story").click(); pg.wait_for_function("DB.stories.length===1")
    ok(J("DB.stories[0].blueprint.game.stats.wisdom") is not None and J("DB.stories[0].fanfic.styleProfile.humor") == "dry", "reviewed creation keeps the structured edits")
    # Guided Creation: one step at a time, typing kept between steps, Create only on the last step
    J("(()=>{document.getElementById('qcroot')?.remove();const r=document.createElement('div');r.id='qcroot';document.body.prepend(r);SFFanUI.quickCreate(r,()=>{},true);return null})()")
    lab("Source title").fill("Ember Academy"); lab("Character names").fill("Kael Ashveil"); B("Research source").click(); pg.wait_for_selector(RT + " >> text=Source evidence")
    ok(pg.locator(R + "label:has-text('Story concept') textarea").first.is_hidden(), "guided setup shows one step at a time")
    B("Next: Your vision").click(); lab("Story concept", "textarea").fill("save Lys"); lab("Player character", "textarea").fill("I take over Kael")
    B("Generate blueprint").click(); pg.wait_for_selector(RT + " >> text=Guided review · Step 1 of 9")
    ok(J("[...document.querySelectorAll('#qcroot details[data-qc-section]')].map(d=>d.dataset.qcSection)") == ["Story"] and B("Create reviewed story").count() == 0, "review shows only the current section, no Create yet")
    pg.locator(R + "details[data-qc-section='Story'] textarea").nth(2).fill("Guided snow.")
    B("Next section").click(); pg.wait_for_selector(RT + " >> text=Step 2 of 9"); B("Previous section").click(); pg.wait_for_selector(RT + " >> text=Step 1 of 9")
    ok(pg.locator(R + "details[data-qc-section='Story'] textarea").nth(2).input_value() == "Guided snow.", "typing is kept when moving between steps")
    for i in range(8): B("Next section").click()
    pg.wait_for_selector(RT + " >> text=Step 9 of 9"); ok(B("Create reviewed story").count() == 1 and B("Next section").count() == 0, "Create appears on the last step")
    B("Create reviewed story").click(); ok("Apply or discard" in J("document.querySelector('#qcroot [role=status]').textContent"), "guided create waits for the unapplied step-1 edit")
    B("Discard unapplied edits").click(); B("Create reviewed story").click(); pg.wait_for_function("DB.stories.length===2")
    ok(J("DB.stories.length") == 2, "guided creation creates the story")
    # AI Story Architect
    J("play(DB.stories.find(x=>x.blueprint&&x.blueprint.game&&x.blueprint.game.stats.wisdom),{})"); pg.wait_for_function("!busy&&DB.sessions.length===1&&DB.sessions[0].turns.length>=2", timeout=10000)
    J("(()=>{const se=DB.sessions[0];se.game=SFGame.change(se.game,'courage',5).game;save();window.SFFanUI.storyChanges(se);return null})()")
    pg.wait_for_selector("text=AI Story Architect")
    MODE["change"] = {"set": {"romance.pacing": "fast", "takeover": "char:ember-academy:lys", "gameplay.stats.0.value": 99}}
    pg.locator("textarea[placeholder='Describe what should change in future chapters']").fill("faster romance")
    pg.locator("button", has_text="Preview story changes").click(); pg.wait_for_selector("text=Proposed changes")
    sheet = pg.locator("text=Refused changes").locator("xpath=..").inner_text()
    ok("romance.pacing" in sheet and "takeover: already played" in sheet and "gameplay.stats.0" in sheet, "the preview shows the diff and the refused list")
    pg.locator("button", has_text="Apply approved changes").click(); pg.wait_for_selector("text=Changes saved.")
    ok(J("DB.sessions[0].canon.romance.pacing") == "fast" and J("DB.sessions[0].game.stats.courage.value") == 15 and J("DB.sessions[0].canon.mode.takeover") == "char:ember-academy:kael-ashveil", "apply changes the future only")
    ok(J("qcChangeHistory(DB.sessions[0]).length") == 1 and pg.locator("summary", has_text="faster romance").count() == 1, "the change appears in the history")
    # stale preview
    MODE["change"] = {"set": {"rules.fates": "free"}}
    pg.locator("textarea[placeholder='Describe what should change in future chapters']").fill("free fates")
    pg.locator("button", has_text="Preview story changes").click(); pg.wait_for_selector("text=Proposed changes")
    J("ffSetRule(DB.sessions[0],'romance','free');null"); pg.locator("button", has_text="Apply approved changes").click()
    pg.wait_for_selector("text=preview again"); ok(J("DB.sessions[0].canon.rules.fates") != "free", "a stale preview is refused and says to preview again")
    J("ffUndo(DB.sessions[0]);null")
    pg.locator("button", has_text="Undo last story change").click(); pg.wait_for_selector("text=Change undone.")
    ok(J("DB.sessions[0].canon.romance.pacing") != "fast" and J("qcChangeHistory(DB.sessions[0]).length") == 0, "undo from the screen restores the setting")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
