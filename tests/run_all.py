"""Runs the Story Forge regression scripts.

Usage:  python tests/run_all.py [path-to-an-epub-you-own]

Each script starts its own local web server for ../app, drives the app in
Chromium with Playwright, and replaces every AI service (OpenRouter, the
OpenCode connector, wikis, AniList) with stand-in replies, so no keys are
needed and nothing is billed. A script passes when it prints "ERRORS: []".
"""
import os, sys, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = tempfile.mkdtemp(prefix="sf-tests-")
BOOK = sys.argv[1] if len(sys.argv) > 1 else ""
NEEDS_BOOK = {"imp21", "lib29"}
NEEDS_SHOTS = {"imp30", "crop30"}
import shutil
failed = []
node_tests = ("memory_phase1_unit", "scene_backup_v55", "story_setup_and_deadlines", "unknown_v43", "chapter_audio_seek")
for name in node_tests:
    if not shutil.which("node"):
        print(f"-- {name}: skipped (install Node.js to run it)")
        continue
    result = subprocess.run(["node", os.path.join(HERE, name + ".mjs")], capture_output=True, text=True)
    print(("ok  " if result.returncode == 0 else "FAIL"), name + " (node)")
    if result.returncode:
        failed.append(name)
        print((result.stdout + result.stderr)[-1500:])
names = sorted(f[:-3] for f in os.listdir(HERE) if f.endswith(".py") and f != "run_all.py")
for n in names:
    if n in NEEDS_BOOK and not BOOK:
        print(f"-- {n}: skipped (pass an EPUB path to run it)"); continue
    if n in NEEDS_SHOTS and not os.path.isdir(os.path.join(HERE, "fixtures", "shots")):
        print(f"-- {n}: skipped (put screenshots s1.png ... s10.png in tests/fixtures/shots)"); continue
    args = [sys.executable, os.path.join(HERE, n + ".py"), OUT] + ([BOOK] if n in NEEDS_BOOK else [])
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=400)
        out = r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        out = "timed out"
    ok = "ERRORS: []" in out and "Traceback" not in out
    print(("ok  " if ok else "FAIL"), n)
    if not ok:
        failed.append(n); print("\n".join(out.strip().splitlines()[-8:]))
print(f"\n{len(failed)} failed" if failed else "\nAll ran scripts passed.")
sys.exit(1 if failed else 0)
