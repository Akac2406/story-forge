"""Fanfiction contract v2 inside the app: prompt canon block, reply checks, adapter functions, import preview, export.
Simulated replies on the invented Ember fixture. No network. Run: python tests/fanfic_app_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8896
FX = json.load(open(os.path.join(HERE, "fixtures", "fanfic-ember.json")))
fails = []; errs = []; LAST = {"sys": ""}; N = {"n": 0}
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
REPLIES = ['Mira | "Again, Kael." She corrects your stance in the courtyard.\n\n[[META]]\nSCENE: Ember Academy | Mira, Kael | morning\nENDING: none',
           'Bandits seize Lys on the North Road to the academy; Lys is kidnapped while Kael watches.\n\n[[META]]\nENDING: none',
           'A quiet evening in the dormitory.\n\n[[META]]\nENDING: none']
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"):
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    LAST["sys"] = b["messages"][0]["content"] if isinstance(b["messages"][0]["content"], str) else ""
    txt = REPLIES[min(N["n"], len(REPLIES) - 1)]; N["n"] += 1
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\ndata: [DONE]\n\n")
se = dict(FX["session"]); se.update({"storyId": "ff-ember", "char": {"name": "Kael Ashveil"}, "memv2": True,
    "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "The academy gates open."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 2})
se["canon"] = dict(se["canon"]); se["canon"]["events"] = {"ev:ember:3": {"status": "prevented", "why": "Kael escorted Lys"}}
SEED = {"key": "sk-or-test", "ocKey": "dummy-oc-key-123456", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "universes": {"ember": FX["universe"]},
        "stories": [{"id": "ff-ember", "kind": "story", "title": "Kael's second chance", "setting": "The Ember Academy.", "starts": [], "stats": [], "endings": [], "entries": []},
                    {"id": "plain", "kind": "story", "title": "Plain", "setting": "A town.", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [se, {"id": "p1", "storyId": "plain", "char": {"name": "Avery"}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Hello."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
def send(pg, text):
    n0 = N["n"]; pg.fill("#input", text); pg.click("button[aria-label='Send']"); pg.wait_for_function(f"DB.sessions.find(s=>s.id==='{pg.evaluate('go.__sid||0') or ''}')||true"); pg.wait_for_timeout(900)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    ok(pg.evaluate("!!window.SFFan && typeof ffState==='function'"), "engine and adapter load")
    S = "DB.sessions.find(s=>s.id==='play-takeover')"
    ok(pg.evaluate(f"ffValidate({S}).ok"), "fixture playthrough validates in the app")
    st = pg.evaluate(f"ffState({S})")
    ok(any(e["id"] == "ev:ember:5" and e["status"] == "impossible" for e in st["events"]) and st["conflicts"], "ffState shows the butterfly effect and the protected-event conflict")
    # prompt block on a fanfiction story
    pg.evaluate("go({n:'chat',id:'play-takeover'})"); pg.wait_for_selector("#log")
    pg.fill("#input", "I practise with Mira."); pg.click("button[aria-label='Send']"); pg.wait_for_selector("text=corrects your stance"); pg.wait_for_timeout(400)
    sysm = LAST["sys"]
    ok("FANFICTION CANON" in sysm and "player controls Kael Ashveil" in sysm, "prompt carries the fanfiction canon block")
    ok("will NOT happen" in sysm and "Lys is kidnapped" in sysm.split("will NOT happen", 1)[1], "prompt tells the narrator the prevented event will not happen")
    ok("ninth form burns" not in sysm and "Dorran arranged" not in sysm.split("FANFICTION CANON", 1)[1].split("Never copy", 1)[0].replace("Knows: Dorran arranged", ""), "no future spoilers in the canon block")
    ok(pg.evaluate(f"!{S}.turns.filter(t=>t.role==='ai').pop().ffc"), "clean reply: no canon issues")
    # a reply that forces the prevented event
    pg.fill("#input", "We travel."); pg.click("button[aria-label='Send']"); pg.wait_for_selector("text=Lys is kidnapped"); pg.wait_for_timeout(400)
    iss = pg.evaluate(f"{S}.turns.filter(t=>t.role==='ai').pop().ffc||[]")
    ok(any(i["kind"] == "forced-event" for i in iss), f"reply that forces a prevented event is flagged: {[i['kind'] for i in iss]}")
    # adapter mutations: rejected changes don't touch data
    before = pg.evaluate(f"JSON.stringify({S}.canon)")
    r = pg.evaluate(f"ffSetRule({S},'nonsense','free')")
    ok(not r["applied"] and pg.evaluate(f"JSON.stringify({S}.canon)") == before, "rejected change leaves saved data unchanged")
    r = pg.evaluate(f"ffSetRule({S},'romance','locked')"); pg.reload(); pg.wait_for_selector(".cta")
    ok(r["applied"] and pg.evaluate(f"{S}.canon.rules.romance") == "locked", "rule change saved and survives reload")
    ok(pg.evaluate(f"ffUndo({S}).applied") and pg.evaluate(f"{S}.canon.rules.romance") == "free", "undo works through the adapter")
    ok(pg.evaluate(f"ffImpact({S},'ev:ember:2','prevented').some(x=>x.id==='ev:ember:4' && x.to==='impossible')"), "impact preview through the adapter")
    ok(pg.evaluate(f"ffKnows({S},'char:ember:mira').every(r=>r.id!=='fact:ember:dorran-took-lys')"), "knowledge boundary through the adapter")
    # import preview: nothing saved until commit
    n_before = pg.evaluate("Object.keys(DB.universes).length")
    prev = pg.evaluate("""async()=>{const f=new File(['Chapter 1\\nAria Venn met Tomas Reed. Aria Venn smiled. Tomas Reed nodded. Aria laughed.\\n\\nChapter 2\\nTomas Reed left. Aria Venn waited.'],'river-tales.txt',{type:'text/plain'});
        const r=await ffImportPreview(f,{title:'River Tales'});window.__c=r.commit;return {ok:r.ok,added:r.preview.added,names:r.preview.names.map(x=>x.name),saved:Object.keys(DB.universes).length}}""")
    ok(prev["ok"] and prev["added"] == [1, 2] and "Aria Venn" in prev["names"] and prev["saved"] == n_before, f"import preview indexes the text and saves nothing: {prev}")
    ok(pg.evaluate("window.__c().applied") and "river-tales" in pg.evaluate("Object.keys(DB.universes)"), "commit saves the new universe")
    ctl = pg.evaluate("""async()=>{const ac=new AbortController();ac.abort();const r=await ffImportPreview(new File(['x'],'a.txt'),{signal:ac.signal});return r}""")
    ok(ctl["ok"] is False and ctl["reason"] == "cancelled", "cancelled import does nothing")
    ok(len(pg.evaluate("ffListUniverses()")) == 2, "universe library lists both")
    # export / restore
    bk = pg.evaluate(f"JSON.stringify(ffExport({S}))")
    ok("dummy-oc-key" not in bk and "sk-or-test" not in bk, "export contains no keys")
    rp = pg.evaluate(f"ffRestorePreview(ffExport({S}))"); ok(rp['ok'], f"restore preview accepts the export: {rp['issues']}")
    # plain story untouched
    pg.evaluate("go({n:'chat',id:'p1'})"); pg.wait_for_selector("#log")
    pg.fill("#input", "Hi."); pg.click("button[aria-label='Send']"); pg.wait_for_timeout(1200)
    ok("FANFICTION CANON" not in LAST["sys"] and pg.evaluate("ffState(DB.sessions.find(s=>s.id==='p1'))") is None, "stories without se.canon are unaffected")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
