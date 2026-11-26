"""Quick Create, Guided review and the AI Story Architect on a 390x844 phone screen with a mock model: nothing overflows sideways, buttons
and inputs are at least 44px tall, inputs use 16px text (no iPhone zoom), and no editor shows JSON to the player. Screenshots are saved to
the temp folder for review. No network, no paid calls. Run: python tests/quick_create_mobile_browser.py"""
import json, os, subprocess, sys, tempfile, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8923; OUT = tempfile.mkdtemp(prefix="qc-mobile-")
FX = json.load(open(os.path.join(HERE, "fixtures", "fanfic-ember.json")))
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
BP = {"title": "Second Term, a very long title that should wrap neatly on a small phone screen without overflowing", "premise": "A second chance.", "modes": ["takeover"], "takeover": "char:ember:kael",
      "player": {"name": "Kael Ashveil", "desc": "remembers everything about the first time through the academy", "age": 19}, "start": {"ch": 0}, "pov": {"mode": "second"}, "romance": {"pref": "none", "pacing": "slow"},
      "rules": {"fates": "free"}, "fates": {"char:ember:kael": "protected"}, "characters": [{"name": "Lys", "role": "friend", "desc": "x"}], "notes": [{"text": "Kael is a student", "cite": ["u0"]}],
      "opening": "Bells ring.", "sources": ["u0"], "uncertain": ["exact chapter"], "gameplay": {"stats": [{"id": "courage", "name": "Courage", "min": 0, "max": 100, "start": 10}]},
      "memory": {"mode": "on", "notes": [{"text": "Lys survives.", "who": ["Lys"]}]}, "director": {"pacing": "slow"}, "styleProfile": {"tense": "past"}, "appearance": {"layout": "novel"}}
def model(route):
    b = json.loads(route.request.post_data); sysm = b["messages"][0]["content"]
    if b.get("stream"):
        return route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": "Bells ring.\n\n[[META]]\nENDING: none"}}]}) + "\n\ndata: [DONE]\n\n")
    txt = json.dumps(BP) if "You set up an interactive fanfiction" in sysm else json.dumps({"set": {"romance.pacing": "fast"}})
    route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": txt}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 900, "completion_tokens": 300}}))
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "universes": {"ember": FX["universe"]}, "stories": [], "sessions": []}
# Overflow: any visible element inside the screen extending past the viewport. Small: visible buttons/inputs/selects under 44px tall.
CHECK = """root=>{const R=document.querySelector(root);const W=document.documentElement.clientWidth;const vis=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'};
  const over=[...R.querySelectorAll('*')].filter(vis).filter(e=>e.getBoundingClientRect().right>W+1).map(e=>e.tagName+':'+(e.textContent||e.value||'').slice(0,30));
  const small=[...R.querySelectorAll('button,select,input:not([type=checkbox]):not([type=radio]),summary')].filter(vis).filter(e=>e.getBoundingClientRect().height<43.5).map(e=>e.tagName+':'+(e.textContent||e.value||'').slice(0,30)+':'+Math.round(e.getBoundingClientRect().height));
  const tiny=[...R.querySelectorAll('input,textarea,select')].filter(vis).filter(e=>parseFloat(getComputedStyle(e).fontSize)<16).length;
  const json=[...R.querySelectorAll('textarea,input')].filter(vis).filter(e=>/^\\s*[\\[{]/.test(e.value)).map(e=>e.value.slice(0,40));
  const jsonText=/"[a-zA-Z]+":/.test(R.innerText);
  const stray=[...R.querySelectorAll('*')].filter(vis).flatMap(e=>[...e.childNodes]).filter(n=>n.nodeType===3&&/^\s*(null|undefined|NaN|\[object Object\])\s*$/.test(n.textContent)).length;
  return{stray,over:over.slice(0,8),small:small.slice(0,8),tiny,json,jsonText,pageOverflow:document.documentElement.scrollWidth>W+1}}"""
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pg = ctx.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept()); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    J = lambda e, *a: pg.evaluate(e, *a)
    def mount(guided):
        J("g=>{document.getElementById('qcroot')?.remove();const r=document.createElement('div');r.id='qcroot';r.className='ff-ui';document.body.prepend(r);SFFanUI.quickCreate(r,()=>{},g);return null}", guided)
    def check(name, root="#qcroot"):
        pg.evaluate("document.querySelectorAll('#qcroot details').forEach(d=>d.open=true);null")
        r = J(CHECK, root); pg.screenshot(path=os.path.join(OUT, name + ".png"), full_page=True)
        ok(not r["over"] and not r["pageOverflow"], name + ": nothing overflows sideways " + str(r["over"]))
        ok(not r["small"], name + ": tap targets at least 44px " + str(r["small"]))
        ok(r["tiny"] == 0, name + ": inputs use 16px text")
        ok(r["stray"] == 0, name + ": no stray null/undefined text")
        return r
    mount(False); pg.locator("#qcroot label:has-text('Imported universe') select").select_option("ember")
    J("(()=>{const d=document.createElement('div');d.id='probe';d.style.width='600px';d.textContent='wide';const b=document.createElement('button');b.textContent='tiny';b.style.cssText='min-height:0;height:20px';document.querySelector('#qcroot').append(d,b);return null})()")
    pr = J(CHECK, "#qcroot"); ok(pr["over"] and pr["small"], "the checks detect a forced overflow and a small button (sanity) " + str(pr["over"][:1]) + str(pr["small"][:1]))
    J("document.getElementById('probe').remove();[...document.querySelectorAll('#qcroot button')].find(b=>b.textContent==='tiny').remove();null"); check("setup")
    pg.locator("#qcroot label:has-text('Story concept') textarea").fill("save Lys"); pg.locator("#qcroot label:has-text('Player character') textarea").fill("Kael")
    pg.locator("#qcroot button", has_text="Generate blueprint").click(); pg.wait_for_selector("#qcroot >> text=3 · Review your blueprint")
    r = check("review"); ok(not r["json"] and not r["jsonText"], "review: no JSON shown to the player " + str(r["json"]))
    mount(True); pg.locator("#qcroot label:has-text('Imported universe') select").select_option("ember"); pg.locator("#qcroot button", has_text="Next: Your vision").click()
    pg.locator("#qcroot label:has-text('Story concept') textarea").fill("save Lys"); pg.locator("#qcroot label:has-text('Player character') textarea").fill("Kael")
    pg.locator("#qcroot button", has_text="Generate blueprint").click(); pg.wait_for_selector("#qcroot >> text=Guided review · Step 1 of 9")
    for i in range(9):
        r = check("guided-step-" + str(i + 1)); ok(not r["json"] and not r["jsonText"], "guided step " + str(i + 1) + ": no JSON shown")
        if i < 8: pg.locator("#qcroot button", has_text="Next section").click()
    pg.locator("#qcroot button", has_text="Create reviewed story").click(); pg.wait_for_function("DB.stories.length===1")
    J("play(DB.stories[0],{})"); pg.wait_for_function("!busy&&DB.sessions.length===1&&DB.sessions[0].turns.length>=2", timeout=10000)
    J("document.getElementById('qcroot')?.remove();window.SFFanUI.storyChanges(DB.sessions[0]);null"); pg.wait_for_selector("text=AI Story Architect")
    J("(()=>{const s=[...document.querySelectorAll('.ff-ui')].find(x=>x.textContent.includes('AI Story Architect'));s.id='qcarch';s.querySelectorAll('details').forEach(d=>d.open=true);return null})()")
    r = J(CHECK, "#qcarch"); pg.screenshot(path=os.path.join(OUT, "architect.png"), full_page=True)
    ok(not r["over"] and not r["pageOverflow"], "architect: nothing overflows sideways " + str(r["over"]))
    ok(not r["small"], "architect: tap targets at least 44px " + str(r["small"]))
    ok(not r["json"], "architect: no JSON in editors " + str(r["json"]))
    br.close()
finally:
    srv.terminate()
print("Screenshots:", OUT)
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
