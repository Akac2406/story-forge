"""Runs the 40-turn memory trial in SIMULATED mode (clean and messy) and fails if the app,
the parser, or the regenerate/branch/cancel operations misbehave. No network, no cost."""
import glob, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); RUN = os.path.join(HERE, "realmodel", "run_trial.py"); REP = os.path.join(HERE, "realmodel", "reports")
fails = []
for prof, prov in (("clean", "openrouter"), ("messy", "openrouter"), ("clean", "opencode")):
    r = subprocess.run([sys.executable, RUN, "--mode", "sim", "--profile", prof, "--provider", prov, "--port", "8831"], capture_output=True, text=True, timeout=900)
    if r.returncode: fails.append(f"{prof}: exit {r.returncode}: {r.stdout[-400:]}{r.stderr[-400:]}"); continue
    rep = json.load(open(sorted(glob.glob(os.path.join(REP, f"*sim-{prof}{'-opencode' if prov == 'opencode' else ''}.json")))[-1]))
    if prov == "opencode" and (rep.get("requests_by_host", {}).get("openrouter.ai") or not rep.get("requests_by_host", {}).get("connector")): fails.append("opencode: requests did not all go to the connector")
    s = rep["summary"]
    if not all(rep["ops"].get(k) for k in ("regen_then_back_to_v1_restores_memory", "branch_keeps_only_earlier_memory", "branch_original_untouched", "cancel_keeps_reply_and_memory")): fails.append(f"{prof}: operation failed {rep['ops']}")
    if rep["generation_failures"] or rep["parser_exceptions"] or rep["page_errors"] or not rep["integrity"]["ok"] or rep["global_flag_at_end"] is not False: fails.append(f"{prof}: failures/exceptions/integrity/global flag")
    if rep["duplicates"]: fails.append(f"{prof}: duplicates stored {rep['duplicates']}")
    if prof == "clean" and any(v["pct"] not in (None, 100) for v in s.values() if v["of"]) and s["Lists split over several lines (recovered)"]["ok"] == 0:
        bad = {k: v for k, v in s.items() if v["pct"] not in (None, 100) and k != "Lists split over several lines (recovered)"}
        if bad: fails.append(f"clean: below 100% {bad}")
    if prof == "messy" and s["No knowledge leaks"]["ok"] == s["No knowledge leaks"]["of"]: fails.append("messy: the injected leak was not detected")
    print("ok  " if not fails else "FAIL", "trial", prof, prov)
print("ERRORS:", fails); sys.exit(1 if fails else 0)
