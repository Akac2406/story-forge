"""Story Forge memory trial: plays a scripted 40-turn story with the Phase 1 memory engine on
for that ONE test playthrough, and scores the model's EVENTS / LEARNED / SCENE metadata.

SIMULATED (no cost, no network):
    python tests/realmodel/run_trial.py --mode sim --profile clean
    python tests/realmodel/run_trial.py --mode sim --profile messy

LIVE through OpenCode Go (DeepSeek V4.1 Flash via your Cloudflare connector; uses your Go limit):
    $env:OPENCODE_API_KEY="..."; $env:STORYFORGE_CONNECTOR="https://your-connector.workers.dev"
    python tests/realmodel/run_trial.py --mode live --provider opencode --max-pct 10

LIVE through OpenRouter (real OpenRouter calls, costs money — you will be asked to confirm):
    set OPENROUTER_API_KEY=sk-or-...        (PowerShell: $env:OPENROUTER_API_KEY="sk-or-...")
    python tests/realmodel/run_trial.py --mode live --model deepseek/deepseek-v4.1-flash --max-cost 0.50
    python tests/realmodel/run_trial.py --mode live --model google/gemini-2.5-flash --max-cost 0.50

Safety:
* Runs in a fresh, throwaway browser profile on a private local port, so the real app and its saved
  stories are never opened or changed. Memory is enabled only for the test playthrough (memDevEnable);
  DB.memv2 stays false.
* The API key is read from the environment only. It is never written to disk or to the report, and
  any occurrence of it in collected text is replaced with [REDACTED].
* Live mode stops when the recorded OpenRouter cost passes --max-cost (the app's own budget pause is
  also set to the same cap).
"""
import argparse, json, os, random, re, subprocess, sys, tempfile, time, datetime, shutil
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(HERE, "..", "..", "site"))
SCEN = json.load(open(os.path.join(HERE, "scenario.json"), encoding="utf-8"))

ap = argparse.ArgumentParser()
ap.add_argument("--mode", choices=["sim", "live"], default="sim")
ap.add_argument("--profile", choices=["clean", "messy"], default="clean", help="simulated model behaviour (sim mode only)")
ap.add_argument("--model", default="deepseek/deepseek-v4.1-flash")
ap.add_argument("--provider", choices=["openrouter", "opencode"], default="openrouter", help="where live calls go; opencode always uses DeepSeek V4.1 Flash")
ap.add_argument("--max-pct", type=float, default=10.0, help="opencode: stop when the estimated 5-hour Go limit use reaches this percent")
ap.add_argument("--connector", default="", help="opencode: connector address (or set STORYFORGE_CONNECTOR)")
ap.add_argument("--turns", type=int, default=len(SCEN["turns"]))
ap.add_argument("--max-cost", type=float, default=0.50, help="live mode: stop when OpenRouter cost reaches this many US dollars")
ap.add_argument("--len", default="250", help="reply length in words (smaller is cheaper)")
ap.add_argument("--yes", action="store_true", help="live mode: skip the typed confirmation")
ap.add_argument("--port", type=int, default=8830)
ap.add_argument("--seed", type=int, default=7)
ap.add_argument("--headed", action="store_true")
args = ap.parse_args()

KEY = ""; CONN = ""
OC = args.provider == "opencode"
if OC: args.model = "deepseek-v4.1-flash (OpenCode Go)"
if args.mode == "live" and OC:
    KEY = os.environ.get("OPENCODE_API_KEY", "").strip(); CONN = (args.connector or os.environ.get("STORYFORGE_CONNECTOR", "")).strip()
    if not KEY or not CONN:
        sys.exit("OpenCode live mode needs OPENCODE_API_KEY and STORYFORGE_CONNECTOR (or --connector). Nothing was sent.")
    print(f"\nLIVE TRIAL through OpenCode Go — DeepSeek V4.1 Flash via your connector\n  turns: {args.turns} story turns + 1 opening + 2 regenerations\n"
          f"  plus background memory upkeep calls\n  reply length: ~{args.len} words\n  stops when the estimated 5-hour Go limit use reaches {args.max_pct:.0f}%\n"
          "  This uses your subscription allowance, not pay-per-use credit. OpenCode says Go is meant for coding agents,\n  so automated story traffic could be noticed; 40 turns is about one normal play session.\n")
    if not args.yes and input("Type opencode to confirm: ").strip().lower() != "opencode":
        sys.exit("Not confirmed. Nothing was sent.")
elif args.mode == "live":
    KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not KEY:
        sys.exit("Live mode needs OPENROUTER_API_KEY in the environment. Nothing was sent.")
    n = args.turns
    print(f"\nLIVE TRIAL — real OpenRouter calls\n  model: {args.model}\n  turns: {n} story turns + 1 opening + ~5 extra (regenerations)"
          f"\n  plus background memory upkeep calls on the same model\n  reply length: ~{args.len} words\n  hard stop at: ${args.max_cost:.2f}\n")
    print("  Rough estimate: 46 requests × ~5–7k input + ~0.5k output tokens.\n"
          "  DeepSeek V4.1 Flash ≈ $0.10–0.20, Gemini 2.5 Flash ≈ $0.10–0.30, Gemini 3.1 Pro ≈ $0.80–1.50 (check current prices).\n")
    if not args.yes and input(f"Type the model id to confirm ({args.model}): ").strip() != args.model:
        sys.exit("Not confirmed. Nothing was sent.")

def redact(x):
    s = json.dumps(x) if not isinstance(x, str) else x
    if KEY: s = s.replace(KEY, "[REDACTED]")
    if CONN: s = s.replace(CONN.rstrip("/"), "[CONNECTOR]")
    s = re.sub(r"sk-or-[A-Za-z0-9_-]{8,}", "[REDACTED]", s)
    return json.loads(s) if not isinstance(x, str) else s

# ---------------- simulated model ----------------
SIM = {"turn": -1, "variant": 0, "calls": 0}
rnd = random.Random(args.seed)
def guess_kind(kws, text):
    t = (" ".join(kws) + " " + text).lower()
    for k, w in (("death", "die"), ("promise", "promise"), ("betrayal", "betray"), ("threat", "warn"), ("reveal", "confess"), ("secret", "secret"), ("item", "copy"), ("travel", "ride")):
        if w in t: return k
    return "action"
def sim_reply():
    k, v = SIM["turn"], SIM["variant"]; T = SCEN["turns"][k] if k >= 0 else {"a": "The story opens.", "loc": ["hall"], "present": ["Corwin"]}
    r = random.Random(args.seed * 1000 + k * 10 + v); messy = args.profile == "messy"
    loc = (T.get("loc") or SIM.setdefault("lastloc", ["hall"]))[0]; SIM["lastloc"] = [loc]
    pres = T.get("present") or ["Corwin"]
    who = "Ilse"; evs = []
    if T.get("event") or k % 3 == 0:
        kws = T.get("event") or ["moment"]
        text = f"Ilse {T['a'][2:].rstrip('.').lower()} ({kws[0]}{' v'+str(v) if v else ''})"
        evs.append([4 if T.get("event") else 2, guess_kind(kws, T["a"]), ", ".join([who] + pres[:1]), loc, text, ", ".join(pres[1:]) or "none"])
    if messy and r.random() < 0.10 and SIM.get("prev_ev"):
        evs.append(SIM["prev_ev"]); SIM["restated"] = SIM.get("restated", 0) + 1     # model restates an earlier event
    if evs: SIM["prev_ev"] = evs[0]
    learned = [f"{l['who']}: the deed shows Corwin sold the {l['kw']} rights to Vey (shown the copy)" for l in T.get("learn", [])]
    if messy and (k == 15 or r.random() < 0.05) and T.get("mustNotKnow"):
        SIM["leaks"] = SIM.get("leaks", 0) + (1 if v == 0 else 0)
        learned.append(f"{T['mustNotKnow'][0]['who']}: Corwin sold the water rights (guessed)")   # simulated knowledge leak
    def ev_line(e):
        e = list(e)
        if messy and r.random() < 0.10: e[0] = "high"
        if messy and r.random() < 0.08: e = e[:4]
        return " | ".join(str(x) for x in e)
    meta = ["CAST: none"]
    bold = messy and r.random() < 0.2
    K = (lambda s: f"**{s}:**") if bold else (lambda s: f"{s}:")
    if messy and r.random() < 0.25 and evs:
        meta.append(K("EVENTS")); meta += [f"- {ev_line(e)}" for e in evs]
    else:
        meta.append(f"{K('EVENTS')} " + ("; ".join(ev_line(e) for e in evs) if evs else "none"))
    meta.append(f"{K('LEARNED')} " + ("; ".join(learned) if learned else "none"))
    if not (messy and r.random() < 0.10):
        meta.append(f"{K('SCENE')} {loc} | {', '.join(pres)} | {'night' if k % 2 else 'day'} {k + 2}")
    meta.append("NEXT: I wait. | I look around. | I speak up.")
    body = f"Turn {k} reply{(' v' + str(v)) if v else ''}. {T['a']} The scene moves on."
    if messy and r.random() < 0.05: return body          # no META block at all
    return body + "\n\n[[META]]\n" + "\n".join(meta)
CORS = {"access-control-allow-origin": "*", "access-control-allow-headers": "authorization, content-type, x-opencode-session", "access-control-allow-methods": "POST, OPTIONS"}
def sim_route(route):
    if route.request.method == "OPTIONS": return route.fulfill(status=204, headers=CORS)
    b = json.loads(route.request.post_data); SIM["calls"] += 1
    if not b.get("stream"):
        return route.fulfill(status=200, content_type="application/json", headers=CORS, body=json.dumps({"choices": [{"message": {"content": "- noted"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 50, "completion_tokens": 5, "cost": 0.0001}}))
    txt = sim_reply()
    body = "data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5000, "completion_tokens": 400, "cost": 0.002}}) + "\n\ndata: [DONE]\n\n"
    route.fulfill(status=200, content_type="text/event-stream", headers=CORS, body=body)

# ---------------- helpers ----------------
def low(x): return str(x or "").lower()
def first(n): return low(n).split()[0] if n else ""
def has_kw(text, kws): t = low(text); return any(low(k) in t for k in kws)
def knows(mem, who, kw):
    ch = next((c for n, c in (mem.get("chars") or {}).items() if first(n) == first(who)), None)
    if not ch: return False
    pool = {f["id"]: f["text"] for f in (mem.get("facts") or []) + (mem.get("secrets") or [])}
    return any(low(kw) in low(pool.get(i, "")) for i in ch.get("knows", []))
def overlap(a, b):
    A = set(w for w in re.sub(r"[^a-z0-9 ]", " ", low(a)).split() if len(w) > 2); B = set(w for w in re.sub(r"[^a-z0-9 ]", " ", low(b)).split() if len(w) > 2)
    return len(A & B) / min(len(A), len(B)) if A and B else 0

port = args.port
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
report = {"mode": args.mode.upper(), "model": args.model if args.mode == "live" else f"simulated ({args.profile})", "started": datetime.datetime.now().isoformat(timespec="seconds"),
          "turns": [], "ops": {}, "errors": [], "generation_failures": 0}
page_errors = []
try:
    with sync_playwright() as p:
        br = p.chromium.launch(headless=not args.headed, args=["--no-sandbox"])
        ctx = br.new_context(viewport={"width": 390, "height": 844})      # fresh, throwaway profile
        pg = ctx.new_page(); pg.set_default_timeout(180000)
        pg.on("pageerror", lambda e: page_errors.append(str(e)))
        HOSTS = {}
        def _req(r):
            from urllib.parse import urlparse
            h = urlparse(r.url).hostname or ""
            if h in ("127.0.0.1", "localhost") or r.method == "OPTIONS": return
            h = "openrouter.ai" if h.endswith("openrouter.ai") else ("connector" if (CONN and CONN.split("//")[-1].split("/")[0] == h) or h == "sim-connector.example" else h)
            HOSTS[h] = HOSTS.get(h, 0) + 1
        pg.on("request", _req)
        if args.mode == "sim": pg.route("https://openrouter.ai/**", sim_route); pg.route("https://sim-connector.example/**", sim_route)
        pg.goto(f"http://127.0.0.1:{port}/index.html"); pg.wait_for_selector(".cta")
        st = SCEN["story"]
        seed = {"migrated": True, "memv2": False, "modes": [{"n": "Trial", "id": args.model, "d": "", "p": "", "t": 0.8}], "mode": 0, "saver": 0,
                "budget": args.max_cost if (args.mode == "live" and not OC) else 0, "budgetStop": args.mode == "live" and not OC,
                **({"prov": "opencode", "ocProxy": CONN if args.mode == "live" else "sim-connector.example"} if OC else {}),
                "stories": [{"id": "trial-story", "kind": "story", "title": SCEN["title"], "setting": st["setting"], "style": st["style"], "lore": st["lore"], "entries": st["entries"], "stats": [], "endings": [], "starts": [], "follow": "strict"}],
                "sessions": [{"id": "trial", "storyId": "trial-story", "start": "", "follow": "strict", "char": {"name": SCEN["player"]["name"], "desc": SCEN["player"]["desc"], "trait": ""},
                              "turns": [], "temp": "", "mems": [], "note": "", "stats": {}, "upto": 0, "len": args.len, "sugg": [], "ending": None, "ended": [], "people": {}, "think": 0, "wstyle": "default", "wcustom": "", "goal": "", "updated": int(time.time() * 1000)}]}
        pg.evaluate("d=>{localStorage.clear();localStorage.setItem('story-forge-v2',JSON.stringify(d))}", seed)
        pg.reload(); pg.wait_for_selector(".cta")
        pg.evaluate("([k,oc])=>{if(oc)DB.ocKey=k;else DB.key=k;save()}", [KEY if args.mode == "live" else "sim-key", OC])
        report["dev_enable"] = pg.evaluate("memDevEnable('trial')")
        report["global_flag_after_enable"] = pg.evaluate("DB.memv2")
        SE = "DB.sessions.find(s=>s.id==='trial')"
        def S(): return pg.evaluate(f"JSON.parse(JSON.stringify({SE}))")
        def cost(): return pg.evaluate("(DB.use&&DB.use.c)||0")
        def go_pct(): return pg.evaluate("(()=>{const g=ocPct();return{h:+g.h.toFixed(2),w:+g.w.toFixed(2),m:+g.m.toFixed(2)}})()")
        def wait_done(n_before):
            pg.wait_for_function(f"()=>!busy&&{SE}.turns.length>={n_before}", timeout=240000); pg.wait_for_timeout(300)
        pg.evaluate("go({n:'chat',id:'trial'})"); pg.wait_for_selector("text=Ready when you are.")
        SIM["turn"] = -1; SIM["variant"] = 0
        n0 = S()["turns"].__len__(); pg.click(".hint button.primary"); wait_done(n0 + 2)
        last_ai = lambda s: max(i for i, t in enumerate(s["turns"]) if t["role"] == "ai")
        for k, T in enumerate(SCEN["turns"][: args.turns]):
            if args.mode == "live" and OC and go_pct()["h"] >= args.max_pct:
                report["stopped_early"] = f"estimated 5-hour Go use reached {args.max_pct:.0f}% before turn {k + 1}"; break
            if args.mode == "live" and not OC and cost() >= args.max_cost:
                report["stopped_early"] = f"cost cap ${args.max_cost:.2f} reached before turn {k + 1}"; break
            SIM["turn"] = k; SIM["variant"] = 0
            before = S(); nb = len(before["turns"])
            pg.fill("#input", T["a"]); pg.click("button[aria-label='Send']")
            try: wait_done(nb + 2)
            except Exception as e:
                report["generation_failures"] += 1; report["errors"].append(f"turn {k + 1}: no reply ({str(e)[:120]})"); continue
            s = S(); ai = last_ai(s)
            if not s["turns"][ai]["text"].strip(): report["generation_failures"] += 1
            mem = s.get("mem") or {}; diag = (s.get("memDiag") or [{}])[-1]
            scene = mem.get("scene") or {}
            evs = [e for e in mem.get("events", []) if e.get("src") == "meta" and e.get("t") == ai]
            row = {"turn": k + 1, "action": T["a"], "diag": {kk: diag.get(kk) for kk in ("block", "keys", "ev", "ln", "sc", "multi", "issues", "err")},
                   "meta": redact(diag.get("meta", ""))[:900], "scene": scene, "events": [e["text"] for e in evs], "kinds": [e["kind"] for e in evs], "checks": {}}
            if T.get("loc"): row["checks"]["scene_location"] = has_kw(scene.get("where", ""), T["loc"])
            if T.get("present"): row["checks"]["scene_present"] = all(any(first(w) == first(x) for w in scene.get("who", [])) for x in T["present"])
            if T.get("event"): row["checks"]["event_recorded"] = any(has_kw(e["text"] + " " + e["kind"], T["event"]) for e in evs)
            for L in T.get("learn", []): row["checks"][f"learned:{L['who']}"] = knows(mem, L["who"], L["kw"])
            for L in T.get("mustNotKnow", []): row["checks"][f"no_leak:{L['who']}"] = not knows(mem, L["who"], L["kw"])
            # ---- operations ----
            if T.get("op") == "regen":
                base = json.dumps({x: mem.get(x) for x in ("events", "facts", "chars", "scene")}, sort_keys=True)
                for v in (1, 2):
                    SIM["variant"] = v; pg.click("button[aria-label='Regenerate']"); wait_done(nb + 2)
                for _ in (1, 2): pg.click("button[aria-label='Previous version']"); pg.wait_for_timeout(300)
                m2 = S().get("mem") or {}
                report["ops"]["regen_then_back_to_v1_restores_memory"] = json.dumps({x: m2.get(x) for x in ("events", "facts", "chars", "scene")}, sort_keys=True) == base
                report["ops"]["regen_versions"] = len(S()["turns"][ai].get("vs", []))
            if T.get("op") == "branch":
                s = S(); cut_ai = sorted(i for i, t in enumerate(s["turns"]) if t["role"] == "ai")[-3]
                orig = json.dumps(s["mem"], sort_keys=True)
                pg.evaluate(f"branchAt({SE},{cut_ai})"); pg.wait_for_timeout(500)
                b = pg.evaluate("JSON.parse(JSON.stringify(DB.sessions[DB.sessions.length-1]))")
                ok_cut = all(e["t"] <= cut_ai for e in b["mem"]["events"] if e.get("src") == "meta")
                same_prefix = sorted(e["id"] for e in b["mem"]["events"]) == sorted(e["id"] for e in s["mem"]["events"] if e.get("src") != "meta" or e["t"] <= cut_ai)
                report["ops"]["branch_keeps_only_earlier_memory"] = ok_cut and same_prefix
                report["ops"]["branch_original_untouched"] = json.dumps(S()["mem"], sort_keys=True) == orig
                pg.evaluate("go({n:'chat',id:'trial'})"); pg.wait_for_timeout(400)
            if T.get("op") == "cancel":
                core = lambda s: json.dumps({x: s.get(x) for x in ("turns", "mem", "stats", "facts")}, sort_keys=True)
                b0 = core(S()); n_calls = SIM["calls"]
                if OC:   # the budget pause applies only to OpenRouter, so cancel through the missing-key path (also stops before any request)
                    pg.evaluate("()=>{window.__k=DB.ocKey;DB.ocKey='';save()}"); pg.click("button[aria-label='Regenerate']"); pg.wait_for_timeout(1200); pg.evaluate("()=>{DB.ocKey=window.__k;save()}")
                else:
                    pg.evaluate("()=>{window.__b=[DB.budget,DB.budgetStop];DB.budget=0.0000001;DB.budgetStop=true;view.overOK=0;DB.spLog=(DB.spLog||[]).concat([[Date.now(),0.000001]]);save()}")
                    pg.click("button[aria-label='Regenerate']"); pg.wait_for_timeout(1200)
                report["ops"]["cancel_keeps_reply_and_memory"] = core(S()) == b0 and (args.mode == "live" or SIM["calls"] == n_calls)
                if not OC: pg.evaluate("()=>{DB.budget=window.__b[0];DB.budgetStop=window.__b[1];view.overOK=0;save()}")
            row["cost_so_far"] = round(cost(), 5) if (args.mode == "live" and not OC) else None
            if OC: row["go_pct"] = go_pct()
            report["turns"].append(row); print(f"turn {k + 1:>2}: " + " ".join(f"{c}={'ok' if v else 'MISS'}" for c, v in row["checks"].items()) + (f"  issues={row['diag']['issues']}" if row["diag"].get("issues") else ""))
        # ---- whole-run analysis ----
        s = S(); mem = s.get("mem") or {}
        evs = [e for e in mem.get("events", []) if e.get("src") == "meta"]
        dups = []
        for i in range(len(evs)):
            for j in range(i + 1, len(evs)):
                if abs(evs[i]["t"] - evs[j]["t"]) <= 6 and overlap(evs[i]["text"], evs[j]["text"]) >= 0.6:
                    dups.append([evs[i]["text"][:80], evs[j]["text"][:80]])
        report["duplicates"] = dups
        report["integrity"] = pg.evaluate(f"SFMemory.integrity({SE}.mem)")
        report["requests_by_host"] = HOSTS
        report["global_flag_at_end"] = pg.evaluate("DB.memv2")
        report["total_cost_usd"] = round(cost(), 4) if (args.mode == "live" and not OC) else 0
        if OC: report["go_limit_used_pct_estimated"] = go_pct(); report["provider"] = "OpenCode Go"
        report["page_errors"] = [redact(e)[:200] for e in page_errors]
        br.close()
finally:
    srv.terminate()

# ---------------- summary ----------------
T = report["turns"]
def rate(f):
    xs = [f(r) for r in T]; xs = [x for x in xs if x is not None]
    return (sum(1 for x in xs if x), len(xs))
def chk(prefix):
    xs = [v for r in T for c, v in r["checks"].items() if c.startswith(prefix)]
    return (sum(1 for x in xs if x), len(xs))
summ = {
    "META block present": rate(lambda r: r["diag"].get("block")),
    "EVENTS key present": rate(lambda r: (r["diag"].get("keys") or {}).get("EVENTS")),
    "LEARNED key present": rate(lambda r: (r["diag"].get("keys") or {}).get("LEARNED")),
    "SCENE key present": rate(lambda r: (r["diag"].get("keys") or {}).get("SCENE")),
    "SCENE well-formed": rate(lambda r: r["diag"].get("sc")),
    "EVENT entries well-formed": (sum((r["diag"].get("ev") or {}).get("valid", 0) for r in T), sum((r["diag"].get("ev") or {}).get("total", 0) for r in T)),
    "LEARNED entries well-formed": (sum((r["diag"].get("ln") or {}).get("valid", 0) for r in T), sum((r["diag"].get("ln") or {}).get("total", 0) for r in T)),
    "Lists split over several lines (recovered)": rate(lambda r: r["diag"].get("multi")),
    "Scene location correct": chk("scene_location"), "Expected characters present": chk("scene_present"),
    "Expected event recorded": chk("event_recorded"), "Expected knowledge recorded": chk("learned:"), "No knowledge leaks": chk("no_leak:"),
}
report["summary"] = {k: {"ok": a, "of": b, "pct": round(100 * a / b) if b else None} for k, (a, b) in summ.items()}
if args.mode == "sim": report["simulated_faults_injected"] = {"restated_events": SIM.get("restated", 0), "knowledge_leaks": SIM.get("leaks", 0)}
report["parser_exceptions"] = sum(1 for r in T if r["diag"].get("err"))
stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S"); tag = (("opencode-deepseek" if OC else args.model.replace("/", "_")) if args.mode == "live" else "sim-" + args.profile + ("-opencode" if OC else ""))
out = os.path.join(HERE, "reports", f"{stamp}-{tag}"); os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(redact(report), open(out + ".json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
L = [f"# Memory trial — {report['mode']}", "",
     ("**SIMULATED RUN — no real model was called.** Replies came from a scripted stand-in (profile: %s). These numbers test the app and parser, not any model." % args.profile) if args.mode == "sim"
     else (f"**LIVE RUN — real calls through OpenCode Go** (DeepSeek V4.1 Flash via your connector). Estimated Go limit used: {report.get('go_limit_used_pct_estimated')}." if OC
           else f"**LIVE RUN — real OpenRouter calls** to `{args.model}`. Total recorded cost: ${report['total_cost_usd']}."),
     "", f"Started {report['started']} · turns played: {len(T)} of {args.turns}" + (f" · stopped early: {report['stopped_early']}" if report.get("stopped_early") else ""),
     f"Memory enabled for the test playthrough only: {report.get('dev_enable')} · global flag stayed off: {report.get('global_flag_at_end') is False}",
     f"Requests by destination: {report.get('requests_by_host')}" + (" — no OpenRouter requests" if OC and not report.get('requests_by_host', {}).get('openrouter.ai') else ""), "",
     "| Check | Result |", "|---|---|"]
for k, v in report["summary"].items(): L.append(f"| {k} | {v['ok']}/{v['of']}" + (f" ({v['pct']}%)" if v["pct"] is not None else "") + " |")
L += ["", "| Operation | Result |", "|---|---|"] + [f"| {k} | {v} |" for k, v in report["ops"].items()]
if args.mode == "sim": L += ["", f"Simulated faults injected on purpose: {report['simulated_faults_injected']}"]
L += ["", f"Possible duplicate events (same 6 turns, ≥60% word overlap): **{len(report['duplicates'])}**", f"Parser exceptions: **{report['parser_exceptions']}** · generation failures: **{report['generation_failures']}** · page errors: **{len(report['page_errors'])}** · memory integrity: **{report['integrity'].get('ok')}**", ""]
iss = [(r["turn"], i) for r in T for i in (r["diag"].get("issues") or [])]
if iss:
    L += ["## Malformed or missing metadata (first 15)", ""] + [f"- turn {t}: {i}" for t, i in iss[:15]] + [""]
miss = [(r["turn"], c) for r in T for c, v in r["checks"].items() if not v]
if miss:
    L += ["## Missed expectations (first 20)", ""] + [f"- turn {t}: {c}" for t, c in miss[:20]] + [""]
open(out + ".md", "w", encoding="utf-8").write(redact("\n".join(L)))
print("\n" + "\n".join(L[:30])); print(f"\nReport: {out}.md")
sys.exit(1 if report["page_errors"] or report["parser_exceptions"] else 0)
