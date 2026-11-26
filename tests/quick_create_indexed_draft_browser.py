"""Anna's v108 report: a Quick Create draft saved before the book was indexed kept the old name-only facts after loading ("source facts are
mostly character-name fragments", evidence u12/u13). With a mock model: a basic import + draft, then the book text is attached; loading the
draft uses the indexed book's passages, flags the old setup, "Generate again from the indexed book" rebuilds it from passages (the frost
curse reaches the model), and evidence shows chapters instead of ids. No network, no paid calls.
Run: python tests/quick_create_indexed_draft_browser.py"""
import json, os, re, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8926
fails = []; errs = []; SEEN = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
BOOK = "\n\n".join([
  "Chapter 1\n\nKiran Vale wakes in the northern fortress. Kiran Vale trains with the sword every morning while Elder Morn watches. Kiran Vale is quiet.",
  "Chapter 2\n\nElder Morn tells Kiran Vale about the old wars. Kiran Vale listens. Lady Seren arrives with letters from the capital for Elder Morn.",
  "Chapter 3\n\nThe frost curse spreads from Kiran Vale's left hand whenever he draws on his mana; the frost curse freezes his blood a little more each time and only fire elixirs slow it. Lady Seren sees the frost on his fingers.",
  "Chapter 4\n\nLady Seren and Kiran Vale ride south. Elder Morn stays behind. Kiran Vale hides the frost curse from the soldiers."])
def bp_from(msgs):
    user = msgs[1]["content"]; ids = re.findall(r"^\[([^\]]+)\]", user, re.M)
    return {"title": "Frost Road", "premise": "x", "modes": ["oc"], "player": {"name": "Ash", "desc": "x"}, "opening": "Snow.", "characters": [], "notes": [{"text": "note", "cite": ids[:2]}], "sources": ids[:3], "uncertain": []}
def model(route):
    b = json.loads(route.request.post_data); msgs = b["messages"]
    if "You set up an interactive fanfiction" in msgs[0]["content"]: SEEN.append(msgs[1]["content"]); txt = json.dumps(bp_from(msgs))
    else: txt = "- ok"
    route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": txt}, "finish_reason": "stop"}]}))
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "stories": [], "sessions": []}
INPUT = {"sourceTitle": "Frost Book", "concept": "I travel with Kiran Vale and learn how the frost curse works", "character": "Ash, a healer"}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept()); pg.route("https://openrouter.ai/**", model)
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    J = lambda e, *a: pg.evaluate(e, *a)
    J("t=>{window.__book=new File([t],'Frost Book.txt',{type:'text/plain'});return null}", BOOK)
    # 1. basic import (no text), generate, save a draft: the old situation
    uid = J("async()=>{const r=await ffImportPreview(__book,{mode:'basic',title:'Frost Book'});const c=await r.commit();return r.preview.universe}")
    ok(J(f"ffSourceStatus('{uid}')")["readiness"] == "basic", "a basic import has no searchable text")
    old = J(f"i=>qcPreview(i,{{universeId:'{uid}'}})", INPUT)
    print("   old sources:", old["blueprint"]["sources"])
    ok(old["blueprint"]["sources"] and all(re.match(r"^(u|person)\d+$", s) for s in old["blueprint"]["sources"]) and "freezes his blood" not in SEEN[-1], "before indexing, the setup cites only name entries")
    d = J(f"([i,b])=>qcSaveDraft({{name:'Old',input:i,universeId:'{uid}',blueprint:b}})", [INPUT, old["blueprint"]])
    # 2. attach the book text later
    at = J(f"async()=>await ffAttachSourceText('{uid}',__book)"); ok(at["ok"] and J(f"ffSourceStatus('{uid}')")["readiness"] == "searchable", "the book text is attached to the existing universe")
    # 3. loading the old draft uses the indexed book and flags the setup
    ld = J("async id=>await qcLoadDraft(id)", d["id"])
    ok(ld["ok"] and ld["stale"] and ld["issues"][0].startswith("This setup was made before"), "the old setup is flagged when the draft loads")
    ok(any(f["id"].startswith("c3.") and "frost curse" in f["text"] for f in ld["facts"]) and J("QC.ctx.facts.some(f=>/frost curse/.test(f.text))"), "the loaded draft's session uses the book's passages (frost curse, chapter 3)")
    # 4. the screen: Load draft, notice, Generate again from the indexed book
    J("(()=>{const r=document.createElement('div');r.id='qcroot';document.body.prepend(r);SFFanUI.quickCreate(r,()=>{});return null})()")
    pg.locator("#qcroot button", has_text="Load draft").click(); pg.wait_for_selector("#qcroot >> text=Generate again from the indexed book")
    pg.locator("#qcroot button", has_text="Generate again from the indexed book").click()
    ok(pg.locator("#qcroot label:has-text('Story concept') textarea").input_value() == INPUT["concept"], "generating again keeps the idea, character and preferences")
    pg.locator("#qcroot button", has_text="Generate blueprint").click(); pg.wait_for_selector("#qcroot >> text=3 · Review your blueprint")
    ok("freezes his blood" in SEEN[-1], "the new setup request gives the model the frost-curse passage")
    ok(re.search(r"= Kiran Vale \(\d+ mentions\)", SEEN[-1]) is not None, "the model is offered characters by name with mention counts")
    pg.evaluate("document.querySelectorAll('#qcroot details').forEach(d=>d.open=true);null")
    srcs = pg.locator("#qcroot .ff-panel:has(> strong:text-is('Sources'))").inner_text()
    ok("Chapter" in srcs and not re.search(r"\bc\d+\.\d+\b", srcs), "evidence shows chapters, not ids: " + srcs.replace("\n", " | ")[:160])
    ok(pg.locator("#qcroot >> text=Generate again from the indexed book").count() == 0, "the notice is gone for the new setup")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
