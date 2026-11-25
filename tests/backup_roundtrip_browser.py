"""Final stabilization: backup -> replace-restore and backup -> add-stories round trips keep every new feature (fanfiction universe, gameplay,
cinematic, director, character templates, appearance settings and presets) and never carry keys. No network.
Run: python tests/backup_roundtrip_browser.py"""
import json, os, subprocess, sys, time, copy
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8903
FX = json.load(open(os.path.join(HERE, "fixtures", "fanfic-ember.json")))
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
se = copy.deepcopy(FX["session"]); se.update({"storyId": "ff", "char": {"name": "Kael"}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Gates."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 2})
SEED = {"key": "sk-or-test", "ocKey": "dummy-oc-key-123456", "ocProxy": "https://connector.example.test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "universes": {"ember": FX["universe"]}, "characterTemplates": [{"name": "Coach Park", "role": "coach"}],
        "stories": [{"id": "ff", "kind": "story", "title": "Ember", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}], "sessions": [se]}
OTHER = {"key": "sk-other", "ocKey": "other-device-key", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
         "stories": [{"id": "o1", "kind": "story", "title": "Other", "setting": "y", "starts": [], "stats": [], "endings": [], "entries": []}], "sessions": []}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions.find(s=>s.storyId==='ff')"
def restore(pg, d, replace):
    pg.evaluate("go({n:'settings'})"); pg.wait_for_timeout(250)
    pg.evaluate("""([d,rep])=>{const inp=[...document.querySelectorAll('input[type=file]')].find(i=>/json/.test(i.accept));
        const btn=[...document.querySelectorAll('button')].find(b=>(rep?/Replace everything/:/Add stories from a backup/).test(b.textContent));btn.click();
        const f=new File([JSON.stringify(d)],'b.json',{type:'application/json'});const dt=new DataTransfer();dt.items.add(f);inp.files=dt.files;inp.dispatchEvent(new Event('change'))}""", [d, replace])
    pg.wait_for_timeout(800)
def fresh(br, seed):
    ctx = br.new_context(viewport={"width": 390, "height": 844}); pg = ctx.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept())
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(seed)); pg.reload(); pg.wait_for_selector(".cta"); return pg
try:
  with sync_playwright() as p:
    br = p.chromium.launch()
    A = fresh(br, SEED)
    A.evaluate(f"gmStartCareer({S},'idol');gmEnable({S},true);gmActivity({S},'vocal_lesson');cvApplyPreset({S},'noir');cvSetCharacter({S},'Mira',{{position:'left'}});dirEnable({S},true);dirSet({S},{{pacing:'fast'}})")
    A.evaluate(f"apSet({S},{{theme:'Oceanic',icons:'pixel'}},'global');apSet({S},{{icons:'neon'}},'story');apSavePreset('Night',{{theme:'Noir Detective',icons:'ink'}})")
    art = A.evaluate("""async()=>{const data=await (await fetch('icon-192.png')).blob();
      const artwork={cover:await imgShrink(data,160,.78),banner:await imgShrink(data,128,.78)};
      if(!ffSaveUniverseArtwork('ember',artwork).applied)throw Error('Could not save test artwork');
      return artwork;
    }""")
    want = A.evaluate(f"JSON.stringify({{game:{S}.game,cv:{S}.cv,dir:{S}.director,canon:{S}.canon,u:Object.keys(DB.universes),t:DB.characterTemplates.map(x=>x.name)}})")
    A.evaluate("go({n:'settings'})"); A.wait_for_timeout(250)
    with A.expect_download() as dl: A.click("button:has-text('Save or send a backup')")
    d = json.loads(open(dl.value.path()).read()); raw = json.dumps(d)
    ok(not any(x in raw for x in ["sk-or-test", "dummy-oc-key", "connector.example"]), "backup has no keys or connector address")
    ok(d.get("appearance") and d["appearance"]["settings"]["global"]["theme"] == "Oceanic" and len(d["appearance"]["presets"]) == 1, "backup includes appearance settings and presets")
    ok("ember" in d.get("universes", {}) and d["characterTemplates"][0]["name"] == "Coach Park", "backup includes the universe and character templates")
    ok(d["universes"]["ember"]["artwork"] == art, "backup contains both universe images")
    # replace on another device
    B = fresh(br, OTHER); restore(B, d, True)
    got = B.evaluate(f"JSON.stringify({{game:{S}.game,cv:{S}.cv,dir:{S}.director,canon:{S}.canon,u:Object.keys(DB.universes),t:DB.characterTemplates.map(x=>x.name)}})")
    ok(got == want, "replace-restore brings back gameplay, cinematic, director, canon, universe and templates exactly")
    ok(B.evaluate("ffUniverse('ember').artwork") == art, "replace-restore brings back both universe images")
    ok(B.evaluate("DB.ocKey") == "other-device-key" and B.evaluate("DB.key") == "sk-other", "this device's keys are kept")
    ok(B.evaluate(f"apState({S},'desktop').icons") == "neon" and B.evaluate("apPresets().length") == 1, "appearance settings and presets restored")
    B.reload(); B.wait_for_selector(".cta"); ok(B.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg').trim().toLowerCase()") == B.evaluate("SFVisualV48.palette('Oceanic')[0]").lower(), "restored theme applies after reload")
    # add stories (merge) on a device that already has its own appearance
    C = fresh(br, OTHER); C.evaluate("apSet(null,{theme:'Royal Fantasy'},'global');apSavePreset('Mine',{icons:'solid'})"); restore(C, d, False)
    ok(C.evaluate("DB.stories.length") == 2 and C.evaluate(f"!!{S}") and C.evaluate("Object.keys(DB.universes||{}).includes('ember')"), "add-stories brings the story and the universe it needs")
    ok(C.evaluate("ffUniverse('ember').artwork") == art, "add-stories restores artwork for a newly imported universe")
    ok(C.evaluate("DB.characterTemplates.some(t=>t.name==='Coach Park')"), "add-stories brings character templates")
    ok(C.evaluate("JSON.parse(localStorage.getItem('sf.visual.v48')).global.theme") == "Royal Fantasy" and C.evaluate("apPresets().length") == 2, "add-stories keeps this device's appearance and adds the backup's presets")
    ok(C.evaluate(f"ffCanonFor({S},'test').length>0") if C.evaluate("typeof ffCanonFor==='function'") else True, "merged fanfiction story still finds its canon")
    restore(C, d, False); ok(C.evaluate("DB.stories.length") == 2 and C.evaluate("apPresets().length") == 2, "adding the same backup twice duplicates nothing")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
