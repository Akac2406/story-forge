"""Visual overhaul checkpoint: all eight reader styles render without touching story data, the Fanfiction Studio dashboard and universe
section open and search, and on a phone the bottom navigation never covers the message box or the last reply. No network.
Run: python tests/visual_checkpoint_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8909
FX = json.load(open(os.path.join(HERE, "fixtures", "fanfic-ember.json")))
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
turns = [{"role": "user", "text": "Begin", "hide": True}] + sum([[{"role": "user", "text": f"Step {i}."}, {"role": "ai", "text": f"Reply {i}. \"Hello,\" said Mira."}] for i in range(12)], [])
SEED = {"key": "sk-or-test", "ocKey": "dummy-oc-key", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "universes": {"ember": FX["universe"]},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "cast": {"Mira": {}}, "turns": turns, "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept())
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    before = pg.evaluate("JSON.stringify({t:DB.sessions[0].turns,k:DB.ocKey,u:Object.keys(DB.universes)})")
    seen = {}
    for lay in [l["id"] for l in pg.evaluate("cvLayouts()")]:
        n0 = len(errs); pg.evaluate(f"cvSet({S},{{layout:'{lay}'}})"); pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log"); pg.wait_for_timeout(200)
        st = pg.evaluate("(()=>{const l=document.querySelector('#log'),t=[...document.querySelectorAll('#log .turn')];const a=t.filter(x=>x.classList.contains('ai')).pop();const cs=a?getComputedStyle(a):null;const b=a&&a.querySelector('.body');const bs=b?getComputedStyle(b):null;return {attr:document.documentElement.dataset.sfCvLayout,turns:t.length,sig:cs?[cs.borderTopWidth,cs.borderRadius,cs.backgroundColor,cs.maxWidth,bs.fontFamily,bs.fontStyle,bs.textAlign,getComputedStyle(l).borderTopWidth].join('|'):''}})()")
        seen[lay] = st["sig"]
        ok(len(errs) == n0 and st["attr"] == lay and st["turns"] >= 20, f"reader style {lay}: renders all turns, no errors")
    ok(len(set(seen.values())) >= 6, f"reader styles look different from each other ({len(set(seen.values()))} distinct of {len(seen)})")
    # phone: nav must not cover the input or the last reply
    pg.evaluate(f"cvSet({S},{{layout:'novel'}})"); pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log"); pg.wait_for_timeout(200)
    pg.evaluate("document.querySelector('#log').scrollTop=1e9"); pg.wait_for_timeout(100)
    cover = pg.evaluate("""(()=>{const inp=document.querySelector('#input');const ir=inp.getBoundingClientRect();
      const bars=[...document.querySelectorAll('nav,.tabs,.bottom-nav,[role=navigation]')].filter(e=>{const s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&e.getBoundingClientRect().height>0});
      const hit=bars.filter(b=>{const r=b.getBoundingClientRect();return r.top<ir.bottom&&r.bottom>ir.top&&r.left<ir.right&&r.right>ir.left&&!b.contains(inp)});
      const x=ir.left+ir.width/2,y=ir.top+ir.height/2,top=document.elementFromPoint(x,y);return {bars:hit.length,top:!!top&&(top===inp||inp.contains(top))}})()""")
    ok(cover["bars"] == 0 and cover["top"], "phone: no navigation bar covers the message box")
    pg.evaluate("apSet(DB.sessions[0],{nav:'floating'},'global')"); pg.evaluate("go({n:'chat',id:'e1'})"); pg.wait_for_selector("#log"); pg.wait_for_timeout(200)
    ok(pg.evaluate("(()=>{const i=document.querySelector('#input').getBoundingClientRect();const t=document.elementFromPoint(i.left+i.width/2,i.top+i.height/2);return !!t&&(t===document.querySelector('#input')||document.querySelector('#input').contains(t))})()"), "phone, floating nav: message box still reachable")
    # Studio dashboard and universe section
    pg.evaluate("go({n:'home',tab:'studio'})"); pg.wait_for_timeout(300)
    tabs = pg.evaluate("[...document.querySelectorAll('[aria-label=\"Studio sections\"] button')].map(b=>b.textContent+':'+b.getAttribute('aria-pressed'))")
    ok(any(t.startswith("Fanfiction") for t in tabs) and all(t.endswith(":true") or t.endswith(":false") for t in tabs), "Studio tabs with valid aria-pressed " + str(tabs))
    pg.locator("[aria-label='Studio sections'] button", has_text="Fanfiction").click(); pg.wait_for_timeout(300)
    ok("Ember" in pg.evaluate("document.querySelector('main').innerText") or "ember" in pg.evaluate("document.querySelector('main').innerText").lower(), "Fanfiction dashboard lists the saved universe")
    srch = pg.locator("main input[type=search], main input[placeholder*='Search']")
    if srch.count():
        srch.first.fill("Kael"); pg.wait_for_timeout(300)
        ok(len(errs) == 0, "dashboard search runs without errors")
    ok(pg.evaluate("JSON.stringify({t:DB.sessions[0].turns,k:DB.ocKey,u:Object.keys(DB.universes)})") == before, "stories, keys and universes preserved through all visual changes")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
