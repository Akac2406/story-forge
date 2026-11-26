"""Quick Create review when the AI omits sections (ChatGPT fd03a08): every editable section is shown with defaults, all canon rules and
Director settings are available, takeover and fates use named pickers, defaults do not count as unapplied edits, and applying an added
section saves it through validation. Mock model, no network. Run: python tests/quick_create_fields_browser.py"""
import json, subprocess, sys, time
fails=[]
def ok(c,m):
    print(("PASS " if c else "FAIL ")+m)
    if not c: fails.append(m)
from playwright.sync_api import sync_playwright
import os
HERE=os.path.dirname(os.path.abspath(__file__));APP=os.path.join(HERE,"..","site"); PORT=8924
BP={"title":"T","premise":"P","modes":["takeover"],"takeover":"char:ember-academy:kael-ashveil","player":{"name":"Kael","desc":"x"},"opening":"O","characters":[],"notes":[],"sources":["f1"],"uncertain":[],"rules":{"fates":"free"},"director":{"pacing":"slow"}}
def model(route):
    sysm=json.loads(route.request.post_data)["messages"][0]["content"]
    route.fulfill(status=200,content_type="application/json",body=json.dumps({"choices":[{"message":{"content":json.dumps(BP)},"finish_reason":"stop"}]}))
srv=subprocess.Popen([sys.executable,"-m","http.server",str(PORT),"--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
try:
  with sync_playwright() as p:
    br=p.chromium.launch();pg=br.new_page();pg.on("dialog",lambda d:d.accept());pg.route("https://openrouter.ai/**",model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html");pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}",json.dumps({"key":"sk-or-test","migrated":True,"modes":[{"n":"S","id":"a/b","d":""}],"mode":0,"chars":[],"found":{},"stories":[],"sessions":[]}));pg.reload();pg.wait_for_selector(".cta")
    F=[{"id":"f1","text":"Kael Ashveil is a second-year student at the academy.","source":{"title":"Wiki"},"confidence":"confirmed","charId":"char:ember-academy:kael-ashveil","charName":"Kael Ashveil"}]
    pg.evaluate("""f=>{window.__F=f;const r=document.createElement('div');r.id='qcroot';document.body.prepend(r);SFFanUI.quickCreate(r,()=>{});return null}""",F)
    # drive: set research facts directly via the screen's research step is complex; use preview through the screen's Generate with facts from a stubbed research
    pg.evaluate("""searchWorks=async q=>[{t:'Ember Academy',ty:'Light novel'}];wikiFind=async t=>({base:'https://e.fandom.com',name:'W'});wikiSearch=async(b,q)=>q==='Kael Ashveil'?['Kael Ashveil']:['Ember Academy'];wikiPage=async(b,t)=>({t,x:t==='Kael Ashveil'?'Kael Ashveil is a second-year student at the academy.':'Ember Academy is a school for fire mages on a mountain.'});null""")
    pg.locator("#qcroot label:has-text('Source title') input").fill("Ember Academy");pg.locator("#qcroot label:has-text('Character names') input").fill("Kael Ashveil")
    pg.locator("#qcroot button",has_text="Research source").click();pg.wait_for_selector("#qcroot >> text=Source evidence")
    pg.locator("#qcroot label:has-text('Story concept') textarea").fill("c");pg.locator("#qcroot label:has-text('Player character') textarea").fill("k")
    pg.locator("#qcroot button",has_text="Generate blueprint").click();pg.wait_for_selector("#qcroot >> text=3 · Review your blueprint")
    pg.evaluate("document.querySelectorAll('#qcroot details').forEach(d=>d.open=true);null")
    r=pg.evaluate("""(()=>{const R=document.querySelector('#qcroot');const strong=[...R.querySelectorAll('.ff-panel > strong')].map(s=>s.textContent);
      const take=[...R.querySelectorAll('select')].find(s=>[...s.options].some(o=>o.value==='char:ember-academy:kael-ashveil'));
      const ruleSelects=[...R.querySelectorAll('details[data-qc-section="Canon"] select')].length;
      const dirInputs=[...R.querySelectorAll('details[data-qc-section="Director"] label')].map(l=>l.firstChild&&l.firstChild.textContent);
      return{sections:strong,takeoverShown:take?[...take.options].find(o=>o.value==='char:ember-academy:kael-ashveil').text:null,ruleSelects,dirLabels:dirInputs,hasRomance:strong.some(s=>/romance/i.test(s)),hasFates:strong.some(s=>/fate/i.test(s)),hasLocks:strong.some(s=>/lock/i.test(s)),hasPov:strong.some(s=>/point of view/i.test(s)),hasStart:strong.some(s=>/start/i.test(s))}})()""")
    ok(all(r[k] for k in ["hasRomance","hasFates","hasLocks","hasPov","hasStart"]), "omitted sections are shown: romance, fates, locks, point of view, start")
    ok(r["ruleSelects"]>=14, "all canon rule categories are editable ("+str(r["ruleSelects"])+" selects)")
    ok(len(r["dirLabels"])>=10 and "Humor" in r["dirLabels"], "all Director settings are editable")
    ok(r["takeoverShown"]=="Kael Ashveil", "takeover shows the character's name")
    ok(pg.locator("#qcroot button",has_text="Discard unapplied edits").count()==0, "shown defaults are not counted as unapplied edits")
    pg.evaluate("document.querySelectorAll('#qcroot details').forEach(d=>d.open=true);null")
    sel=pg.locator("#qcroot .ff-panel:has(> strong:text-is('Romance')) select").first; sel.select_option("slow") if sel.count() and "slow" in sel.inner_text() else None
    pg.locator("#qcroot button",has_text="Apply romance").click(); pg.wait_for_timeout(200)
    ok(pg.evaluate("QC.hist[QC.cur].now.romance!==undefined"), "applying an added romance section saves it through validation")
    pg.evaluate("document.querySelectorAll('#qcroot details').forEach(d=>d.open=true);null")
    pg.locator("#qcroot button",has_text="Apply rules").click(); pg.wait_for_timeout(200)
    ok(len(pg.evaluate("Object.keys(QC.hist[QC.cur].now.rules||{})"))>=14, "applying rules saves every category")
    pg.evaluate("document.querySelectorAll('#qcroot details').forEach(d=>d.open=true);null")
    pg.locator("#qcroot button",has_text="Apply director").click(); pg.wait_for_timeout(200)
    st=pg.evaluate("document.querySelector('#qcroot [role=status]').textContent")
    ok("applied" in st.lower() and pg.evaluate("Object.keys(QC.hist[QC.cur].now.director||{}).length")>=8, "applying the Director saves its settings: "+st)
    pg.locator("#qcroot button",has_text="Create reviewed story").click(); pg.wait_for_function("DB.stories.length===1")
    ok(pg.evaluate("DB.stories[0].fanfic.canon.rules&&Object.keys(DB.stories[0].fanfic.canon.rules).length")>=14, "the created story has the edited rules")
    br.close()
finally: srv.terminate()
print('ERRORS:',fails);sys.exit(1 if fails else 0)
