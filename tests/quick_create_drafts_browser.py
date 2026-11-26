"""Quick Create extension 4 with a mock model and stubbed lookups: cached research (reuse, refresh, not in backups), spoiler limit (facts past
the chapter are left out and the model is told the limit), coverage separate from confidence, persistent drafts (survive reload, re-validated
on load, limits), drafts in backups (replace and add-stories, never overwriting). No network, no paid calls.
Run: python tests/quick_create_drafts_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8919
fails = []; errs = []; SEEN = {"setup": ""}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
BP = {"title": "Second Term", "premise": "A second chance.", "modes": ["takeover"], "takeover": "char:ember-academy:kael-ashveil",
      "player": {"name": "Kael Ashveil", "desc": "remembers", "age": 19}, "start": {"ch": 0}, "pov": {"mode": "second"}, "romance": {"pref": "none", "pacing": "slow"},
      "characters": [], "notes": [], "opening": "Bells ring.", "sources": [], "uncertain": []}
def model(route):
    sysm = json.loads(route.request.post_data)["messages"]
    if "You set up an interactive fanfiction" in sysm[0]["content"]: SEEN["setup"] = sysm[1]["content"]; txt = json.dumps(BP)
    else: txt = "- ok"
    route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": txt}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 900, "completion_tokens": 300}}))
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "stories": [], "sessions": []}
STUBS = """window.__calls=0;searchWorks=async q=>{__calls++;return[{t:'Ember Academy',ty:'Light novel',y:2019,a:'R. Vale',src:'AniList'}]};
  wikiFind=async t=>({base:'https://ember-academy.fandom.com',name:'Ember Academy Wiki',pages:400});
  wikiSearch=async(b,q,n)=>q==='Kael Ashveil'?['Kael Ashveil']:q==='Nobody Here'?[]:['Ember Academy','Fire Trial'];
  wikiPage=async(b,t)=>t==='Kael Ashveil'?{t,x:'Kael Ashveil is a second-year student.'}:t==='Fire Trial'?{t,x:'In chapter 40 Lys dies in the fire trial.'}:{t,x:'Ember Academy is a school for fire mages.'};null"""
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
def fresh(br):
    ctx = br.new_context(); pg = ctx.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept()); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta"); pg.evaluate(STUBS); return pg
def restore(pg, d, replace):
    pg.evaluate("go({n:'settings'})"); pg.wait_for_timeout(250)
    pg.evaluate("""([d,rep])=>{const inp=[...document.querySelectorAll('input[type=file]')].find(i=>/json/.test(i.accept));
        const btn=[...document.querySelectorAll('button')].find(b=>(rep?/Replace everything/:/Add stories from a backup/).test(b.textContent));btn.click();
        const f=new File([JSON.stringify(d)],'b.json',{type:'application/json'});const dt=new DataTransfer();dt.items.add(f);inp.files=dt.files;inp.dispatchEvent(new Event('change'))}""", [d, replace])
    pg.wait_for_timeout(800)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = fresh(br); J = lambda e, *a: pg.evaluate(e, *a)
    # research cache + coverage
    r1 = J("qcResearch('Ember Academy',{characters:['Kael Ashveil','Nobody Here']})")
    cv = r1["coverage"]
    ok(r1["ok"] and not r1["cached"] and cv["characters"]["found"] == ["Kael Ashveil"] and cv["characters"]["missing"] == ["Nobody Here"] and cv["level"] == "partial", "coverage reports found and missing characters " + str(cv))
    ok(cv["confidence"]["confirmed"] == len(r1["facts"]) and cv["pages"] >= 2, "coverage and confidence are reported separately")
    r2 = J("qcResearch('ember academy',{characters:['Nobody Here','Kael Ashveil']})")
    ok(r2["cached"] and J("__calls") == 1 and len(r2["facts"]) == len(r1["facts"]), "the same research is reused from the cache (any order or case)")
    r3 = J("qcResearch('Ember Academy',{characters:['Kael Ashveil','Nobody Here'],refresh:true})"); ok(not r3["cached"] and J("__calls") == 2, "refresh fetches again")
    # spoiler limit
    sp = J("qcResearch('Ember Academy',{characters:['Kael Ashveil','Nobody Here'],maxChapter:10})")
    ok(sp["cached"] and sp["spoiler"] == {"maxChapter": 10, "removed": 1} and not any("chapter 40" in f["text"] for f in sp["facts"]), "facts past the spoiler limit are left out")
    ok(any("chapter 40" in f["text"] for f in r1["facts"]), "the cache keeps everything; the limit applies per request")
    inp = {"sourceTitle": "Ember Academy", "concept": "save Lys", "character": "I take over Kael", "maxChapter": 10}
    J("([i,f])=>qcPreview(i,{facts:f})", [inp, r1["facts"]])
    ok("SPOILER LIMIT" in SEEN["setup"] and "up to chapter 10" in SEEN["setup"] and "chapter 40" not in SEEN["setup"], "the model is told the limit and never sees later facts")
    est = J("([i,f])=>qcEstimatePreview(i,{facts:f})", [inp, r1["facts"]]); ok(est["ok"] and est["inputTokens"] > 0, "estimate uses the same spoiler-limited facts")
    # drafts
    bp = J("bp=>qcLock(bp,['opening']).blueprint", J("([i,f])=>qcPreview(i,{facts:f})", [inp, sp["facts"]])["blueprint"])
    d = J("([i,f,b])=>qcSaveDraft({name:'Ember draft',input:i,facts:f,blueprint:b})", [inp, sp["facts"], bp])
    ok(d["applied"] and J("qcDrafts()")[0]["name"] == "Ember draft" and J("qcDrafts()")[0]["maxChapter"] == 10, "draft saved with its spoiler limit")
    ok(J("([i,f,id])=>qcSaveDraft({id,name:'Ember draft 2',input:i,facts:f}).id", [inp, sp["facts"], d["id"]]) == d["id"] and len(J("qcDrafts()")) == 1, "saving with the same id updates the draft")
    J("([i,f,b,id])=>{qcSaveDraft({id,name:'Ember draft',input:i,facts:f,blueprint:b});return null}", [inp, sp["facts"], bp, d["id"]])
    pg.reload(); pg.wait_for_selector(".cta"); pg.evaluate(STUBS)
    ld = J("id=>qcLoadDraft(id)", d["id"])
    ok(ld["ok"] and ld["blueprint"]["id"] == bp["id"] and ld["blueprint"]["locked"] == ["opening"] and J("QC.cur") == bp["id"] and J("qcUndo().reason") == "nothing to undo", "a draft survives a reload and loads with its locks and a fresh history")
    ok(J("QC.ctx.input.maxChapter") == 10 and not any("chapter 40" in f["text"] for f in J("QC.ctx.facts")), "a loaded draft keeps its spoiler limit")
    c = J("bp=>qcCommit(bp)", ld["blueprint"]); ok(c["applied"] and J("DB.stories.length") == 1, "a loaded draft can be committed")
    big = J("qcSaveDraft({name:'Huge',input:{concept:'x'},blueprint:{premise:'y'.repeat(250000)}})"); ok(not big["applied"] and big["reason"] == "draft too large", "oversized drafts are refused")
    lim = J("(()=>{let r;for(let i=0;i<25;i++)r=qcSaveDraft({name:'D'+i,input:{sourceTitle:'T'}});return r})()"); ok(not lim["applied"] and "limit" in lim["reason"] and len(J("qcDrafts()")) == 20, "at most 20 drafts")
    J("id=>{qcDeleteDraft(id);return null}", J("qcDrafts()")[-1]["id"]); g = J("qcSaveDraft({name:'Gone source',universeId:'nope',input:{sourceTitle:'T'}})")
    ok(not J("async id=>(await qcLoadDraft(id)).ok", g["id"]) and "missing" in J("async id=>(await qcLoadDraft(id)).reason", g["id"]), "a draft whose imported source is gone says so")
    ok(J("id=>qcDeleteDraft(id).applied", g["id"]) and not J("id=>qcDeleteDraft(id).applied", g["id"]), "delete draft")
    # backups
    pg.evaluate("go({n:'settings'})"); pg.wait_for_timeout(250)
    with pg.expect_download() as dl: pg.click("button:has-text('Save or send a backup')")
    bk = json.loads(open(dl.value.path()).read()); N = len(J("qcDrafts()"))
    ok(N == 19 and len(bk.get("qcDrafts", {})) == N and "qcResearch" not in bk and J("Object.keys(DB.qcResearch).length") == 1, "backups include drafts but not the research cache")
    B2 = fresh(br); J2 = lambda e, *a: B2.evaluate(e, *a)
    J2("qcSaveDraft({name:'Mine',input:{sourceTitle:'Local'}});null"); mine = J2("qcDrafts()")[0]["id"]
    clash = dict(bk); clash["qcDrafts"] = dict(bk["qcDrafts"]); clash["qcDrafts"][mine] = {"id": mine, "name": "Theirs", "input": {}}
    restore(B2, clash, False)
    names = [x["name"] for x in J2("qcDrafts()")]
    ok(len(names) == N + 1 and "Mine" in names and "Theirs" not in names, "add-stories brings drafts in without overwriting this device's drafts")
    restore(B2, clash, False); ok(len(J2("qcDrafts()")) == N + 1, "adding the same backup twice duplicates no drafts")
    B3 = fresh(br); restore(B3, bk, True); ok(len(B3.evaluate("qcDrafts()")) == N and B3.evaluate("Object.keys(DB.qcResearch||{}).length") == 0, "replace-restore brings the drafts back")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
