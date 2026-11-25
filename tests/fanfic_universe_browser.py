"""Phase 8 adapters in the app: upgrade preview/upgrade/undo, promote/demote fanon, crossover, power rules, per-universe knowledge. No network.
Run: python tests/fanfic_universe_browser.py"""
import copy, json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8892
FX = json.load(open(os.path.join(HERE, "fixtures", "fanfic-ember.json")))
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
U = copy.deepcopy(FX["universe"]); U["rev"] = 2
U["records"].append({"id": "fact:ember:vol3-twist", "layer": "universe", "kind": "fact", "text": "The Warden has a twin", "who": [], "canon": "source", "rev": 2, "spoilerAt": {"ch": 45}})
V = {"v": 1, "id": "void", "name": "Voidlands", "rev": 1, "chars": {"char:void:sel": {"id": "char:void:sel", "name": "Sel Ashe"}}, "events": [],
     "records": [{"id": "fact:void:rift", "layer": "universe", "kind": "fact", "text": "Rifts open at dusk", "who": [], "canon": "source", "spoilerAt": {"ch": 1}}], "rules": {"powers": [], "world": []}}
se = dict(FX["session"]); se.update({"storyId": "ff", "char": {"name": "Kael Ashveil"}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Gates."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 2})
se["canon"] = dict(se["canon"]); se["canon"]["position"] = {"ch": 60}
x = copy.deepcopy(se); x["id"] = "x1"; x["canon"]["universes"] = [{"id": "ember", "role": "primary"}, {"id": "void", "role": "secondary"}]
x["canon"]["powers"] = [{"from": "ember", "to": "void", "rule": "translated", "scale": "normalized", "note": "Embers burn rifts shut"}]
SEED = {"key": "sk-or-test", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {}, "universes": {"ember": U, "void": V},
        "stories": [{"id": "ff", "kind": "story", "title": "Ember", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}], "sessions": [se, x]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"; X = "DB.sessions[1]"
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(); pg.set_default_timeout(15000); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("s=>{localStorage.clear();localStorage.setItem('story-forge-v2',s)}", json.dumps(SEED)); pg.reload(); pg.wait_for_selector(".cta")
    pv = pg.evaluate(f"ffUpgradePreview({S})"); ok(pv["from"] == 1 and pv["to"] == 2 and "fact:ember:vol3-twist" in pv["newRecords"], "upgrade preview shows what revision 2 adds")
    ok(not any(r["id"] == "fact:ember:vol3-twist" for r in pg.evaluate(f"ffSearch({S},'twin')")), "pinned playthrough does not see new material before upgrading")
    ok(pg.evaluate(f"ffUpgrade({S}).applied") and pg.evaluate(f"{S}.canon.rev") == 2, "upgrade applied and saved")
    ok(any(r["id"] == "fact:ember:vol3-twist" for r in pg.evaluate(f"ffSearch({S},'twin')")), "new material visible after upgrade")
    ok(pg.evaluate(f"ffUpgrade({S}).reason") == "already current" and pg.evaluate(f"ffUndo({S}).applied") and pg.evaluate(f"{S}.canon.rev") == 1, "no double upgrade; undo restores the pinned revision")
    r = pg.evaluate(f"ffPromote({S},{{id:'f77',text:'Kael keeps a burned page',who:['char:ember:kael']}})")
    ok(r["applied"] and pg.evaluate(f"(x=>x.canon==='fanon'&&x.from.session==={S}.id)(DB.universes.ember.records.find(r=>r.id==='fanon:ember:f77'))"), "promote stores fanon in the shared universe with provenance")
    ok(pg.evaluate(f"ffPromote({S},{{text:'Kael keeps a burned page'}}).reason") == "already in the universe", "no duplicate promotion")
    ok(pg.evaluate("ffDemote('ember','fanon:ember:f77').applied") and not pg.evaluate("ffDemote('ember','fact:ember:archive-fire').applied"), "demote removes fanon only")
    pg.reload(); pg.wait_for_selector(".cta")
    ok(not pg.evaluate("DB.universes.ember.records.some(r=>r.id==='fanon:ember:f77')"), "demotion persisted across reload")
    c = pg.evaluate("ffCrossover(['ember','void'])"); ok(c and c["id"] == "ember+void" and "char:void:sel" in c["chars"], "crossover view combines both universes")
    ok(pg.evaluate("ffCrossover(['ember','nope'])") is None, "crossover with a missing universe returns null")
    ok(pg.evaluate(f"ffPowerRule({X},'ember','void').rule") == "translated" and pg.evaluate(f"ffPowerRule({X},'void','ember').rule") == "separate", "power rules per direction")
    km = pg.evaluate(f"ffKnowsX({X},'char:ember:mira').map(r=>r.id)"); ks = pg.evaluate(f"ffKnowsX({X},'char:void:sel').map(r=>r.id)")
    ok("fact:void:rift" not in km and "fact:void:rift" in ks and "fact:ember:archive-fire" not in ks, "crossover knowledge stays within each character's universe")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
