"""Post-release reliability fixes (102): artwork references, stacked scene effects, rain over artwork, panel transparency, no transition replay
on re-render, stale universe import ignored, typewriter Stop keeps text, memory-step timeout is reported. No network.
Run: python tests/reliability_102_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8913
FX = json.load(open(os.path.join(HERE, "fixtures", "fanfic-ember.json")))
fails = []; errs = []; MODE = {"hang_side": False, "slow": False}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
HELD = []
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"):
        if MODE["hang_side"]: HELD.append(route); return
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "[[META]]\nEVENTS: none\nLEARNED: none\nSCENE: pier | Avery | dusk"}, "finish_reason": "stop"}]}))
    txt = ("Waves broke on the pier. " * 30) + "\n\n[[META]]\nEVENTS: none\nLEARNED: none\nSCENE: pier | Avery | dusk\nENDING: none"
    route.fulfill(status=200, content_type="text/event-stream", body="".join("data: " + json.dumps({"choices": [{"delta": {"content": txt[i:i+30]}}]}) + "\n\n" for i in range(0, len(txt), 30)) + "data: [DONE]\n\n")
SEED = {"key": "sk-or-test", "migrated": True, "repairWait": 2, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "universes": {"ember": FX["universe"]},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "x", "coverT": PNG, "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "cast": {"Mira": {"pic": PNG}}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"
def chat(pg): pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log"); pg.wait_for_timeout(250)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1000, "height": 800}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept()); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("([s,sc])=>{localStorage.clear();localStorage.setItem('story-forge-v2',s);localStorage.setItem('sf-v54-scene-presets',sc)}", [json.dumps(SEED), json.dumps({"e1": {"background": PNG}})]); pg.reload(); pg.wait_for_selector(".cta")
    # artwork references
    ok(pg.evaluate(f"cvArt({S},'story:s1')") == PNG, "story:<id> references resolve to the story cover")
    ok(pg.evaluate(f"cvSetScene({S},{{background:'art:nothing'}}).reason") == "No artwork found for that reference in this playthrough" and pg.evaluate(f"cvSetCharacter({S},'Mira',{{portrait:'cast:Nobody'}}).applied") is False, "references that show nothing are refused with a reason")
    ok(pg.evaluate(f"cvSetScene({S},{{background:'story:s1'}}).applied") and pg.evaluate(f"cvSetScene({S},{{background:null}}).applied"), "valid references save; clearing still works")
    # stacked effects + rain over artwork
    pg.evaluate(f"cvSet({S},{{layout:'visual-novel',lighting:'night',overlay:'fog'}})"); chat(pg)
    sh = pg.evaluate("getComputedStyle(document.querySelector('#log')).boxShadow")
    ok(sh.count("inset") >= 2, "night lighting and fog both apply (" + sh[:80] + ")")
    pg.evaluate(f"cvSet({S},{{overlay:'rain'}})"); chat(pg)
    bgi = pg.evaluate("getComputedStyle(document.querySelector('#log')).backgroundImage")
    ok("repeating-linear-gradient" in bgi and "url(" in bgi, "rain stays visible over scene artwork")
    # no transition replay on re-render (menu open/close)
    pg.evaluate(f"cvSet({S},{{overlay:'none',transition:'fade'}})"); chat(pg); pg.wait_for_timeout(200)
    pg.evaluate("document.querySelector('#log').classList.remove('sf-cv-scene-enter')")
    pg.evaluate(f"menuSheet({S},DB.stories[0])"); pg.wait_for_timeout(200); pg.evaluate("closeSheet(true)"); pg.evaluate("render()"); pg.wait_for_timeout(250)
    ok(not pg.evaluate("document.querySelector('#log').classList.contains('sf-cv-scene-enter')"), "opening and closing a menu does not replay the scene transition")
    pg.evaluate(f"cvSetScene({S},{{lighting:'dawn'}})"); pg.evaluate("render()"); pg.wait_for_timeout(250)
    ok(pg.evaluate("document.querySelector('#log').classList.contains('sf-cv-scene-enter')"), "a real scene change still plays the transition")
    # transparency on studio panels
    pg.evaluate(f"apSet({S},{{transparency:0.5}},'global')"); pg.evaluate(f"window.SFFanUI.director({S})"); pg.wait_for_timeout(200)
    bgc = pg.evaluate("(()=>{const p=document.querySelector('.ff-ui .ff-panel');return p?getComputedStyle(p).backgroundColor:''})()")
    ok("0.5" in bgc or ("rgba" in bgc and not bgc.endswith(", 1)")) or "color(" in bgc and " / 0.5" in bgc, "studio panels honour transparency (" + bgc + ")")
    pg.evaluate("closeSheet(true)"); pg.evaluate(f"apReset({S},'global')")
    # stale import ignored after switching universe
    pg.evaluate("window.__imp=ffImportPreview;window.__res=null;ffImportPreview=()=>new Promise(r=>{window.__res=r});null")
    pg.evaluate("(()=>{const d=document.createElement('div');d.id='wz';document.body.prepend(d);window.SFFanUI.createFanfiction(d)})()"); pg.wait_for_timeout(200)
    pg.evaluate("(()=>{const f=document.querySelector('#wz input[type=file]');const dt=new DataTransfer();dt.items.add(new File(['Chapter 1\\nx'],'a.txt'));f.files=dt.files;f.dispatchEvent(new Event('change',{bubbles:true}))})()")
    pg.locator("#wz button", has_text="Preview import").first.click(); pg.wait_for_timeout(150)
    pg.evaluate("(()=>{const s=[...document.querySelectorAll('#wz label.fld')].find(f=>f.querySelector('span')&&f.querySelector('span').textContent.includes('Source universe')).querySelector('select');s.value='ember';s.dispatchEvent(new Event('change',{bubbles:true}))})()"); pg.wait_for_timeout(150)
    pg.evaluate("window.__res({ok:true,preview:{universe:'stale',rev:1,added:{},duplicate:{},conflicts:[],names:[]},commit:()=>({ok:true,applied:true})});null"); pg.wait_for_timeout(300)
    btn = pg.locator("#wz button", has_text="Confirm source import")
    ok(btn.count() == 0 or btn.first.is_disabled(), "an import started before switching universes is ignored")
    pg.evaluate("ffImportPreview=window.__imp;document.getElementById('wz').remove();null")
    # typewriter + Stop keeps what arrived
    pg.evaluate(f"cvSet({S},{{textReveal:'typewriter',revealSpeed:5,reducedMotion:false}})"); chat(pg)
    n = pg.evaluate(f"{S}.turns.length"); pg.fill("#input", "Wait."); pg.click("button[aria-label='Send']"); pg.wait_for_timeout(400)
    stop = pg.locator("button[aria-label='Stop']")
    if stop.count(): stop.first.click()
    pg.wait_for_function("!busy", timeout=15000); pg.wait_for_timeout(300)
    saved = pg.evaluate(f"({S}.turns[{n+1}]||{{}}).text||''")
    shown = pg.evaluate("(()=>{const b=[...document.querySelectorAll('#log .turn.ai .body')].pop();return b?b.textContent:''})()")
    ok(saved.startswith("Waves broke") and saved.strip()[-20:] in shown, "Stop during a typewriter reveal keeps the reply and shows all of it")
    # memory step timeout is reported
    pg.evaluate(f"{S}.memExtract='hybrid';{S}.memv2=true;save();null"); MODE["hang_side"] = True; chat(pg)
    n = pg.evaluate(f"{S}.turns.length"); pg.fill("#input", "Look around."); pg.click("button[aria-label='Send']"); pg.wait_for_function(f"!busy&&{S}.turns.length==={n+2}", timeout=15000)
    pg.wait_for_function("document.body.innerText.includes('Memory notes for the last reply')", timeout=12000)
    ok(True, "a memory step that times out is reported to the player")
    for r in HELD:
        try: r.abort()
        except Exception: pass
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
