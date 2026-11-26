"""Memory recall on by default for new playthroughs (Anna, 2026-11-25), with ChatGPT's checks: no extra requests, prompt overhead within the
recall cap, relevant memories recalled, playthroughs isolated, every way of starting a playthrough (story, fanfiction wizard, Quick Create
default and explicit off, character chat), existing playthroughs unchanged, and the Settings switch. Simulated replies, no network.
Run: python tests/memory_default_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8925
FX = json.load(open(os.path.join(HERE, "fixtures", "fanfic-ember.json")))
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
N = {"stream": 0, "other": 0}; LAST = {"sys": ""}; EVENTS = {"next": []}
BP = {"title": "Second Term", "premise": "x", "modes": ["takeover"], "takeover": "char:ember:kael", "player": {"name": "Kael", "desc": "x"}, "opening": "Bells.", "characters": [], "notes": [], "sources": [], "uncertain": []}
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"):
        N["other"] += 1; sysm = b["messages"][0]["content"]
        txt = json.dumps(dict(BP, memory={"recall": False}) if "NO-RECALL" in json.dumps(b["messages"]) else BP) if "You set up an interactive fanfiction" in sysm else "- ok"
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": txt}, "finish_reason": "stop"}]}))
    N["stream"] += 1; LAST["sys"] = b["messages"][0]["content"] if isinstance(b["messages"][0]["content"], str) else ""
    ev = EVENTS["next"].pop(0) if EVENTS["next"] else "Rae looks around the harbor"
    txt = ('Rae | "Reply %d."\n\n[[META]]\nEVENTS: 3 | action | Rae | harbor | %s | none\nLEARNED: none\nSCENE: harbor | Rae | night\nENDING: none') % (N["stream"], ev)
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\ndata: [DONE]\n\n")
STORY = {"id": "s1", "kind": "story", "title": "Harbor", "setting": "A harbor town.", "starts": [], "stats": [], "endings": [], "entries": []}
CHAR = {"id": "c1", "kind": "character", "title": "Rae", "setting": "Rae, a harbor deputy.", "starts": [], "stats": [], "endings": [], "entries": []}
OLD = {"id": "e0", "storyId": "s1", "char": {"name": "Avery"}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "universes": {"ember": FX["universe"]}, "stories": [STORY, CHAR], "sessions": [OLD]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept()); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    J = lambda e, *a: pg.evaluate(e, *a)
    def start(story_expr, name="Avery"):
        ids0 = J("DB.sessions.map(s=>s.id)"); J(f"play({story_expr},{{name:'{name}'}})")
        pg.wait_for_function("ids=>!busy&&DB.sessions.some(s=>!ids.includes(s.id)&&s.turns.length>=2)", arg=ids0, timeout=10000)
        return J("ids=>DB.sessions.find(s=>!ids.includes(s.id)).id", ids0)
    def send(sid, text):
        J(f"go({{n:'chat',id:'{sid}'}})"); pg.wait_for_selector("#input"); n0 = N["stream"]
        pg.fill("#input", text); pg.click("button[aria-label='Send']"); pg.wait_for_function(f"!busy&&document.body.innerText.includes('Reply {n0+1}.')"); pg.wait_for_timeout(300)
    se = lambda sid, expr: J(f"(()=>{{const se=DB.sessions.find(s=>s.id==='{sid}');return {expr}}})()")
    # 1. a new story playthrough gets recall + structured memory; no extra requests
    EVENTS["next"] = ["Rae hides the brass key under the pier"]
    A = start("DB.stories.find(s=>s.id==='s1')")
    ok(se(A, "se.memRecall===true&&se.memv2===true"), "a new playthrough has memory recall on by default")
    EVENTS["next"] = ["Dale sharpens the old sword in the forge", "Rae waits by the lighthouse"]
    send(A, "I walk to the forge."); other0 = N["other"]; send(A, "Where did Rae put the key?")
    ok(N["other"] == other0, "recall adds no extra model requests (" + str(N["other"] - other0) + " extra)")
    rec = LAST["sys"].split("Relevant memories from earlier", 1)
    ok(len(rec) == 2 and "brass key" in rec[1][:3000], "relevance: asking about the key recalls the brass-key memory")
    sysA = LAST["sys"]; recall_len = len(rec[1].split("\n\n", 2)[0] + rec[1].split("\n\n", 2)[1]) if len(rec) == 2 else 0
    # 2. isolation: another playthrough of the same story never sees A's memories
    EVENTS["next"] = ["Mira lights a lantern on the wall"]
    B = start("DB.stories.find(s=>s.id==='s1')", "Blake")
    EVENTS["next"] = ["Mira climbs the wall"]; send(B, "Where is the key?")
    ok("brass key" not in LAST["sys"] and "sword" not in LAST["sys"], "isolation: a second playthrough of the same story never recalls the first one's memories")
    # 3. overhead: compare with the same story and the default switched off
    J("DB.memRecallDefault=false;save();null")
    EVENTS["next"] = ["Rae hides the brass key under the pier"]; C = start("DB.stories.find(s=>s.id==='s1')", "Casey")
    ok(se(C, "!se.memRecall&&!se.memv2"), "with the Settings switch off, a new playthrough has no recall")
    EVENTS["next"] = ["Dale sharpens the old sword in the forge", "Rae waits by the lighthouse"]; send(C, "I walk to the forge."); send(C, "Where did Rae put the key?")
    over = len(sysA) - len(LAST["sys"])
    print("   prompt overhead of memory + recall:", over, "characters (~" + str(over // 4) + " tokens); recall section", recall_len, "characters")
    ok(0 < over <= 8000, "overhead stays within the recall cap plus the notes instructions (" + str(over) + " chars)")
    J("DB.saver=2;save();null"); J("DB.memRecallDefault=true;save();null"); send(A, "And the key again?")
    r2 = LAST["sys"].split("Relevant memories from earlier", 1)
    ok(len(r2) == 2 and len(r2[1].split("\n\n")[0] + r2[1].split("\n\n")[1]) <= 2600, "the money-saving setting shrinks the recall section")
    J("DB.saver=0;save();null")
    # 4. existing playthrough unchanged
    ok(se("e0", "!('memRecall' in se)&&!('memv2' in se)"), "an existing playthrough keeps its settings")
    send("e0", "Hello?"); ok("Relevant memories from earlier" not in LAST["sys"] and se("e0", "!('memRecall' in se)"), "an existing playthrough still runs without recall after a new turn")
    # 5. every way of starting a playthrough
    J("(()=>{const r=ffCreateStory('ember',{modes:['oc'],player:{name:'Mira',desc:'x'},title:'Ember OC'});window.__ff=r.storyId;return null})()")
    F = start("getStory(__ff)", "Mira"); ok(se(F, "se.memRecall===true&&!!se.canon"), "fanfiction wizard story: new playthrough has recall and canon")
    bp = J("qcPreview({sourceTitle:'Ember',concept:'x',character:'Kael'},{universeId:'ember'})")["blueprint"]
    ok(bp["memory"]["recall"] is True, "Quick Create: recall defaults to on in the setup")
    c = J("bp=>qcCommit(bp)", bp); Q = start(f"getStory('{c['storyId']}')", "Kael"); ok(se(Q, "se.memRecall===true"), "Quick Create story: new playthrough has recall")
    bp2 = J("qcPreview({sourceTitle:'Ember',concept:'NO-RECALL',character:'Kael'},{universeId:'ember'})")["blueprint"]
    c2 = J("bp=>qcCommit(bp)", bp2); Q2 = start(f"getStory('{c2['storyId']}')", "Kael"); ok(bp2["memory"]["recall"] is False and se(Q2, "!se.memRecall"), "Quick Create setup with recall turned off: the playthrough respects it")
    Ch = start("DB.stories.find(s=>s.id==='c1')", "Avery"); ok(se(Ch, "!se.memRecall"), "character chat: no recall (it doesn't use it)")
    # 6. Settings switch exists and the player can turn recall off per story
    J("go({n:'settings'})"); pg.wait_for_timeout(300)
    ok(pg.locator("label:has-text('Recall relevant memories in new stories') input").count() == 1, "Settings has the default switch")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
