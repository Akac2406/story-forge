"""Quick Create extension 5 with a mock model: a failure at each persistence stage (universe, story, setup, appearance, save) and full
storage (appearance settings, and the story DB with no IndexedDB fallback) leaves stories, universes and appearance exactly as before and
keeps the session for a retry; a retry creates exactly one story; committing again (double click, re-loaded draft) returns the existing
story instead of a duplicate. No network, no paid calls. Run: python tests/quick_create_rollback_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8920
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
BP = {"title": "Second Term", "premise": "A second chance.", "modes": ["takeover"], "takeover": "char:ember-academy:kael-ashveil",
      "player": {"name": "Kael Ashveil", "desc": "remembers", "age": 19}, "start": {"ch": 0}, "pov": {"mode": "second"}, "romance": {"pref": "none", "pacing": "slow"},
      "characters": [], "notes": [], "opening": "Bells ring.", "sources": [], "uncertain": [],
      "gameplay": {"stats": [{"id": "courage", "name": "Courage", "min": 0, "max": 100, "start": 10}]}, "appearance": {"layout": "novel", "colors": {"accent": "#ff3366"}}}
def model(route):
    sysm = json.loads(route.request.post_data)["messages"][0]["content"]
    txt = json.dumps(BP) if "You set up an interactive fanfiction" in sysm else "- ok"
    route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": txt}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 900, "completion_tokens": 300}}))
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "stories": [], "sessions": []}
FACTS = [{"id": "f1", "text": "Kael Ashveil is a second-year student.", "source": {"title": "Wiki: Kael", "url": "https://ember-academy.fandom.com/wiki/Kael_Ashveil"}, "confidence": "confirmed", "charId": "char:ember-academy:kael-ashveil", "charName": "Kael Ashveil"}]
INPUT = {"sourceTitle": "Ember Academy", "concept": "save Lys", "character": "I take over Kael"}
STATE = "JSON.stringify({s:DB.stories,u:DB.universes||{},a:localStorage.getItem(apKey())})"
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept()); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    J = lambda e, *a: pg.evaluate(e, *a)
    bp = J("([i,f])=>qcPreview(i,{facts:f})", [INPUT, FACTS])["blueprint"]
    for stage in ["universe", "story", "setup", "appearance", "save"]:
        before = J(STATE); J("s=>{window.__qcFailAt=s;return null}", stage); r = J("bp=>qcCommit(bp)", bp); J("window.__qcFailAt=null;null")
        ok(not r["applied"] and stage in r["reason"] or (stage == "save" and "storage full" in r["reason"]), "failure at " + stage + " is reported: " + str(r["reason"]))
        ok(J(STATE) == before and J("QC.ctx!==null"), "failure at " + stage + " restores stories, universes and appearance, and keeps the session")
    # full storage for the appearance settings
    before = J(STATE)
    J("window.__setItem=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k===apKey()){const e=new Error('quota');e.name='QuotaExceededError';throw e}return __setItem.call(this,k,v)};null")
    r = J("bp=>qcCommit(bp)", bp); J("Storage.prototype.setItem=__setItem;null")
    ok(not r["applied"] and "storage full" in r["reason"] and J(STATE) == before, "full storage for appearance settings rolls everything back")
    # full storage for the story DB with no IndexedDB fallback
    before = J(STATE)
    J("window.__idb=idb;idb=null;window.__setItem=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k===KEY){const e=new Error('quota');e.name='QuotaExceededError';throw e}return __setItem.call(this,k,v)};null")
    r = J("bp=>qcCommit(bp)", bp); same = J(STATE) == before
    J("Storage.prototype.setItem=__setItem;idb=__idb;save();null")
    ok(not r["applied"] and "storage full" in r["reason"] and same, "full storage for the stories rolls everything back " + str(r["reason"]))
    # retry, then duplicates
    c = J("bp=>qcCommit(bp)", bp); ok(c["applied"] and J("DB.stories.length") == 1 and J("DB.stories[0].fanfic.quick.key") == bp["id"], "retry after the failures creates exactly one story")
    pv = J("([i,f])=>qcPreview(i,{facts:f})", [INPUT, FACTS])["blueprint"]; c1 = J("bp=>qcCommit(bp)", pv)
    d = J("([i,f,b])=>qcSaveDraft({name:'d',input:i,facts:f,blueprint:b})", [INPUT, FACTS, pv]); ld = J("id=>qcLoadDraft(id)", d["id"])
    again = J("bp=>qcCommit(bp)", ld["blueprint"])
    ok(c1["applied"] and again["duplicate"] and again["storyId"] == c1["storyId"] and not again["applied"] and J("DB.stories.length") == 2, "committing a re-loaded draft again returns the existing story, no duplicate")
    copy = J("bp=>qcCommit(bp,{idempotencyKey:'copy-1'})", ld["blueprint"]); ok(copy["applied"] and J("DB.stories.length") == 3, "an explicit new key makes an intentional copy")
    ok(J("Object.keys(DB.universes).filter(k=>k.startsWith('ember-academy')).length") == 3, "each created story got its own universe; failed attempts left none behind")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
