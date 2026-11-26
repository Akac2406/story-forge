"""Canon follows how far the player has read (v112, Anna 2026-11-25: "it is still straying from canon").
Reference knowledge (book-analysis powers, terms, character profiles, passages) follows the playthrough's reading limit; plot events
follow the story position; book analysis done after a playthrough started still reaches it; the app suggests moving a position that
never moves by itself. Simulated replies, no network. Run: python tests/canon_reading_limit_browser.py"""
import json, os, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site")
with socket.socket() as s:
    s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
def deep(kind, ch, title, text, rev):
    return {"kind": kind, "chapter": ch, "title": title, "text": text, "aliases": [], "private": False, "rev": rev, "src": "deep", "source": {"sourceId": "src:frost", "chapter": ch}}
ENTRIES = [deep("character", 2, "Lio Vant", "Lio Vant is a quiet heir who hides his training at night.", 2),
           deep("term", 3, "Frost Seal", "The Frost Seal blocks the mana circuit in nine places and weakens as the fire ring grows.", 4),
           deep("power", 7, "Starfall Edge", "Starfall Edge splits mountains; Lio learns it in the far north.", 4)]
EVENTS = [{"id": "ev:frost:deep-a", "title": "Lio wakes the fire ring", "summary": "Lio wakes the fire ring inside the cold annex while his mother sleeps beside the hearth.", "ch": 4, "order": 4001, "who": [], "requires": [], "needs": [], "leadsTo": [], "imp": "minor", "rev": 4, "src": "deep", "source": {"sourceId": "src:frost", "chapter": 4}},
          {"id": "ev:frost:deep-b", "title": "Lio duels the northern king", "summary": "Lio duels the northern king.", "ch": 7, "order": 7001, "who": [], "requires": [], "needs": [], "leadsTo": [], "imp": "minor", "rev": 4, "src": "deep", "source": {"sourceId": "src:frost", "chapter": 7}}]
RECORDS = [{"id": "fact:frost:deep-" + str(i), "kind": e["kind"], "title": e["title"], "text": e["text"], "ch": e["chapter"], "spoilerAt": {"ch": e["chapter"]}, "confidence": "uncertain", "canon": "source", "private": False, "knownBy": [], "rev": e["rev"], "src": "deep", "source": e["source"]} for i, e in enumerate(ENTRIES) if e["kind"] != "character"]
U = {"v": 1, "id": "frost", "name": "Frost Book", "rev": 4, "created": 1, "updated": 1, "revisions": [], "sources": [], "aliases": {}, "chars": {}, "events": EVENTS, "records": RECORDS,
     "conflicts": [], "rules": {}, "indexMode": "deep", "deep": {"v": 1, "sources": {"src:frost": {"done": [2, 3, 4, 5, 6, 7], "failed": []}}, "entries": ENTRIES}}
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "universes": {"frost": U}, "stories": [], "sessions": []}
N = {"stream": 0}
def model(route):
    b = json.loads(route.request.post_data)
    if not b.get("stream"):
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": "- ok"}, "finish_reason": "stop"}]}))
    N["stream"] += 1
    route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": "Snow falls.\n\n[[META]]\nENDING: none"}}]}) + "\n\ndata: [DONE]\n\n")
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(service_workers="block"); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept()); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta"); pg.wait_for_function("!!window.SFFanUI")
    J = lambda e, *a: pg.evaluate(e, *a)
    J("(()=>{const r=ffCreateStory('frost',{modes:['oc'],player:{name:'Mira',desc:'Twin sister born with the Frost Seal'},title:'Twin'});window.__st=r.storyId;return null})()")
    J("play(getStory(__st),{name:'Mira'})"); pg.wait_for_function("!busy&&DB.sessions.length===1&&DB.sessions[0].turns.length>=2")
    SE = "DB.sessions[0]"
    # the playthrough was pinned before the book analysis (rev 2): position chapter 1
    J(f"(()=>{{const se={SE};se.canon=Object.assign({{}},se.canon,{{rev:2,position:{{ch:1,order:0}}}});save();return null}})()")
    before = J(f"ffCanonFor({SE})")
    ok(J(f"ffReadTo({SE})") == 1, "with no reading limit set, book knowledge stops at the story position")
    ok("Frost Seal" not in before and "Starfall" not in before, "nothing past the position is used yet")
    ok(J(f"ffSetReadTo({SE},5).applied") and J(f"ffReadTo({SE})") == 5, "the reading limit can be set")
    ok(J(f"ffSetReadTo({SE},5).reason") == "unchanged" and not J(f"ffSetReadTo({SE},-1).applied"), "unchanged and bad values are refused")
    J(f"(()=>{{{SE}.turns.push({{role:'ai',text:'Mira asks about the Frost Seal and the mana circuit.'}});return null}})()")
    after = J(f"ffCanonFor({SE})")
    ok("blocks the mana circuit in nine places" in after, "a power/rule from a chapter the player has read reaches the narrator")
    ok("Frost Seal" in after, "book analysis made after the playthrough was pinned (rev 4 > 2) is used")
    ok("Starfall" not in after and "northern king" not in after, "nothing past the reading limit is used")
    ok("read the source up to chapter 5" in after and "Story position: source chapter 1" in after, "the prompt separates reading limit and story position")
    ok("Lio wakes the fire ring" in after, "an event the player has read is listed as upcoming, not as happened")
    # passages follow the reading limit
    J("window.__opts=null;window.__ffs=ffSearchSource;ffSearchSource=async(id,q,o)=>{__opts=o;return[]};null")
    J(f"ffSourcePrompt({SE},getStory({SE}.storyId),{SE}.turns,'look')")
    ok(J("__opts&&__opts.maxChapter") == 5 and J("__opts&&__opts.rev") is None, "book passages search up to the reading limit, newest text")
    J("ffSearchSource=__ffs;null")
    # position suggestion: the reply describes the chapter 4 event
    ok(J(f"ffPositionHint({SE})") is None, "no suggestion while the story does not describe a later event")
    J(f"(()=>{{{SE}.turns.push({{role:'ai',text:'In the cold annex Mira watches Lio wake the fire ring while their mother sleeps beside the hearth.'}});return null}})()")
    h = J(f"ffPositionHint({SE})")
    ok(h and h["ch"] == 4, "a later book event the story describes is suggested as the new position: " + json.dumps(h))
    ok(J(f"ffPositionNudge({SE})") and J(f"{SE}.posHint") == 4 and J(f"ffPositionNudge({SE})") is None, "the suggestion is shown once")
    ok(J(f"{SE}.canon.position.ch") == 1, "the position itself does not move without the player")
    # Fanfiction Studio shows and saves the reading limit; saving a chapter moves the event order with it
    J(f"SFFanUI.studio({SE})"); pg.wait_for_selector("text=Book knowledge")
    inp = pg.locator("label:has-text('Read up to chapter') input, input[placeholder='1']").first
    inp.fill("6"); pg.click("text=Save reading progress"); pg.wait_for_timeout(200)
    ok(J(f"{SE}.canon.readTo") == 6, "Fanfiction Studio saves the reading limit")
    # a story-level reading limit (from Quick Create) applies when the playthrough has none
    J(f"(()=>{{delete {SE}.canon.readTo;getStory({SE}.storyId).fanfic.readTo=3;return null}})()")
    ok(J(f"ffReadTo({SE})") == 3, "Quick Create's spoiler limit is the default reading limit")
    # a real reply still works and nothing is sent outside the mock
    J(f"go({{n:'chat',id:{SE}.id}})"); J("send('Mira looks at the snow.');null"); pg.wait_for_function("!busy"); pg.wait_for_timeout(300)
    ok(N["stream"] >= 2, "a reply goes through with the new canon block")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
