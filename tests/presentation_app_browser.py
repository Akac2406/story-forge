"""Cinematic (cv*) and appearance (ap*) adapters in the app: validated, stored, presentation only, v48 stays in sync, presets clean. No network.
Run: python tests/presentation_app_browser.py"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site"); PORT = 8900
fails = []; errs = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
SEED = {"key": "sk-or-test", "ocKey": "dummy-oc-key-123456", "migrated": True, "modes": [{"n": "Swift", "id": "a/b", "d": ""}], "mode": 0, "chars": [], "found": {},
        "stories": [{"id": "s1", "kind": "story", "title": "Harbor", "setting": "x", "starts": [], "stats": [], "endings": [], "entries": []}],
        "sessions": [{"id": "e1", "storyId": "s1", "char": {"name": "Avery"}, "cast": {"Rae": {"pic": PNG}, "June": {}}, "turns": [{"role": "user", "text": "Begin", "hide": True}, {"role": "ai", "text": "Fog."}], "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1}]}
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
S = "DB.sessions[0]"
try:
  with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 900}); pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"http://127.0.0.1:{PORT}/index.html"); pg.wait_for_selector(".cta")
    pg.evaluate("([s,sc])=>{localStorage.clear();localStorage.setItem('story-forge-v2',s);localStorage.setItem('sf-v54-scene-presets',sc)}", [json.dumps(SEED), json.dumps({"e1": {"background": PNG, "caption": "Harbor at dawn"}})]); pg.reload(); pg.wait_for_selector(".cta")
    before = pg.evaluate(f"JSON.stringify([{S}.turns,{S}.mem||null,{S}.cast])")
    ok(len(pg.evaluate("cvLayouts()")) >= 8 and len(pg.evaluate("cvPresets()")) >= 8, "layouts and presets listed")
    ok(pg.evaluate(f"cvState({S}).settings.layout") == "novel" and pg.evaluate(f"{S}.cv") is None, "default classic novel; nothing stored until changed")
    ok(pg.evaluate(f"cvApplyPreset({S},'classic-vn').applied") and pg.evaluate(f"cvState({S}).layout.id") == "visual-novel", "preset applied")
    sc = pg.evaluate(f"cvScene({S})"); ok(sc["background"] == "v54:e1" and sc["caption"] == "Harbor at dawn" and pg.evaluate(f"cvArt({S},'v54:e1')") == PNG, "scene reuses v54 artwork by reference")
    ok("artwork reference" in pg.evaluate(f"cvSetScene({S},{{background:'{PNG}'}}).reason"), "image data is never stored in presentation")
    cast = pg.evaluate(f"cvCast({S})"); rae = [c for c in cast if c["name"] == "Rae"][0]
    ok(rae["portrait"] == "cast:Rae" and pg.evaluate(f"cvArt({S},'cast:Rae')") == PNG and [c for c in cast if c["name"] == "June"][0]["portrait"] is None, "cast portraits by reference")
    ok(pg.evaluate(f"cvSetCharacter({S},'Rae',{{expression:'happy',position:'left'}}).applied") and [c for c in pg.evaluate(f"cvCast({S})") if c["name"] == "Rae"][0]["position"] == "left", "character presentation saved")
    ok(pg.evaluate(f"JSON.stringify([{S}.turns,{S}.mem||null,{S}.cast])") == before, "story text, memory and cast untouched")
    ok(pg.evaluate(f"cvReset({S}).applied") and pg.evaluate(f"cvState({S}).settings.layout") == "novel", "reset presentation")
    pg.reload(); pg.wait_for_selector(".cta"); ok(pg.evaluate(f"JSON.stringify({S}.cv)") == json.dumps({"settings": {}, "scene": {}, "cast": {}, "preset": None}, separators=(",", ":")), "presentation persists")
    # appearance
    th = pg.evaluate("apThemes()"); ok(len(th) >= 30 and th[0]["palette"] and len(pg.evaluate("apLayouts()")) >= 16 and len(pg.evaluate("apFormats()")) >= 8 and len(pg.evaluate("apIcons()")) >= 12, "catalogs: 30 themes with palettes, 16 layouts, 8 formats, 12+ icon families")
    ok(pg.evaluate(f"apSet({S},{{theme:'Oceanic',icons:'pixel'}},'global').applied") and pg.evaluate("JSON.parse(localStorage.getItem('sf.visual.v48')).global.theme") == "Oceanic", "global appearance written to v48 storage")
    pg.wait_for_timeout(100); bg = pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()")
    ok(bg.lower() == pg.evaluate("SFVisualV48.palette('Oceanic')[0]").lower(), "v48 reloaded and applied the theme (" + bg + ")")
    ok(pg.evaluate(f"apSet({S},{{theme:'Nope'}},'global').reason") == "unknown theme", "unknown theme rejected")
    pg.evaluate(f"apSet({S},{{icons:'neon'}},'story');apSet({S},{{spacing:'compact'}},'desktop')")
    ok(pg.evaluate(f"apState({S},'desktop').icons") == "neon" and pg.evaluate(f"apState({S},'desktop').spacing") == "compact" and pg.evaluate(f"apState({S},'mobile').spacing") == "cozy", "story and device scopes")
    pg.evaluate("SFVisualV48.useAppTheme()")
    ok(pg.evaluate("JSON.parse(localStorage.getItem('sf.visual.v48')).stories.s1.icons") == "neon", "v48's own saves keep adapter changes (no stale overwrite)")
    r = pg.evaluate(f"apSavePreset('Night',Object.assign({{}},apState({S},'desktop'),{{ocKey:'x'}}))"); pid = r["id"]
    ok(r["applied"] and "ocKey" not in json.dumps(pg.evaluate("apPresets()")), "preset saved without unrelated keys")
    ex = pg.evaluate(f"apExportPreset('{pid}')"); ok(ex["format"] == "story-forge-appearance" and "dummy" not in json.dumps(ex), "export clean")
    ok(pg.evaluate("d=>apImportPreview(d).ok", ex) and pg.evaluate("d=>apImport(d).applied", ex) and len(pg.evaluate("apPresets()")) == 2, "import adds a preset")
    ok(pg.evaluate(f"apApplyPreset({S},'{pid}','mobile').applied") and pg.evaluate(f"apState({S},'mobile').icons") == "neon", "apply preset to a scope")
    ok(pg.evaluate(f"apReset({S},'story').applied") and pg.evaluate(f"apState({S},'desktop').icons") == "pixel", "reset story scope falls back to global")
    ok(pg.evaluate(f"apDeletePreset('{pid}').applied") and len(pg.evaluate("apPresets()")) == 1, "delete preset")
    ok(pg.evaluate("DB.ocKey") == "dummy-oc-key-123456" and pg.evaluate("DB.key") == "sk-or-test", "credentials untouched")
    br.close()
finally:
    srv.terminate()
ok(not errs, "no page errors " + str(errs[:3]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
