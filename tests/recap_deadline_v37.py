"""v37: a slow chapter recap no longer holds up the next turn. Stand-in model; no real requests.
Run: python tests/recap_deadline_v37.py   (prints "ERRORS: []" when everything passes)"""
import asyncio, json, os, sys, subprocess, time
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.normpath(os.path.join(HERE, "..", "story-forge-pwa")); PORT = 8814
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
results, errs = [], []; st = {"n": 0, "delay": 0, "recaps": 0, "recap_done": 0}
def check(name, cond, info=""): results.append((name, bool(cond))); print(("ok  " if cond else "FAIL"), name, "" if cond else info)
STORY = " ".join(["The rain keeps falling on the old hall while Kevin watches the door."] * 6)
async def model(route):
    b = json.loads(route.request.post_data); txt = json.dumps(b["messages"])
    if not b.get("stream"):
        if "continuity editor" in txt:
            st["recaps"] += 1
            if st["delay"]: await asyncio.sleep(st["delay"])
            st["recap_done"] += 1
            body = "SUMMARY: Kevin watched the door in the rain.\nFACTS:\n- Kevin guards the hall\n- It is raining\n- Mira is nearby\nCONFLICTS:\n- none"
        else: body = "- note"
        return await route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": body}, "finish_reason": "stop"}]}))
    st["n"] += 1; n = st["n"]
    t = f"Reply number {n}. {STORY}\n\n[[META]]\nNEXT: I wait. | I look. | I speak."
    await route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": t}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5, "completion_tokens": 5}}) + "\n\ndata: [DONE]\n\n")
async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(args=["--no-sandbox"]); pg = await (await br.new_context(viewport={"width": 390, "height": 844})).new_page(); pg.set_default_timeout(20000)
        pg.on("pageerror", lambda e: errs.append(str(e))); await pg.route("https://openrouter.ai/**", model)
        await pg.goto(f"http://127.0.0.1:{PORT}/index.html"); await pg.wait_for_selector(".cta")
        await pg.evaluate("()=>{localStorage.clear();localStorage.setItem('story-forge-v2',JSON.stringify({key:'k',migrated:true,recWait:5,modes:[{n:'Swift',id:'a/b',d:''}],mode:0,stories:[{id:'s1',kind:'story',title:'Ledger Test',setting:'A hall.',entries:[],stats:[],endings:[],starts:[]}]}))}")
        await pg.reload(); await pg.wait_for_selector(".cta"); await pg.click(".card:has-text('Ledger Test')")
        await pg.fill("input[placeholder='Your character’s name']", "Anna"); await pg.click("button:text-is('Start story')"); await pg.wait_for_selector("text=Reply number 1")
        await pg.evaluate("()=>{DB.sessions[0].chapN=1;save()}")
        async def send(text, n):
            await pg.fill("#input", text); t0 = time.time(); await pg.click("button[aria-label='Send']"); await pg.wait_for_selector(f"text=Reply number {n}", timeout=40000); return time.time() - t0
        st["delay"] = 0; await send("I wait.", 2); await pg.wait_for_timeout(1500)
        check("fast recap: finishes normally before the next turn", st["recap_done"] >= 1)
        st["delay"] = 20; before = st["recap_done"]
        await send("I wait again.", 3); await pg.wait_for_timeout(800)   # chapter 2 recap starts after this reply
        dt = await send("I keep waiting.", 4)
        check(f"slow recap: next reply arrives within the deadline ({dt:.1f}s, recap still running)", dt < 12 and st["recap_done"] == before, (dt, st))
        late = await pg.evaluate("(DB.sessions[0].recLate||[]).length")
        check("slow recap: the deadline is recorded for diagnostics", late >= 1, late)
        dt2 = await send("I keep waiting still.", 5)
        check(f"slow recap: a later turn doesn't wait again for the same pending recap ({dt2:.1f}s)", dt2 < 3, dt2)
        # branch while the recap is still pending: the late result must not attach to the branch
        pend = await pg.evaluate("()=>{const se=DB.sessions[0];const c=chapsOf(se);const p=[];c.forEach((x,i)=>{if(!x.sum&&i<c.length-1)p.push(i)});branchAt(se,se.turns.length-1);return p}")
        await pg.wait_for_timeout(23000)
        got = await pg.evaluate("p=>{const o=chapsOf(DB.sessions[0]),b=chapsOf(DB.sessions[DB.sessions.length-1]);return [DB.sessions.length,p.map(i=>!!(o[i]&&o[i].sum)),p.map(i=>!!(b[i]&&b[i].sum))]}", pend)
        check("branch made while a recap was pending: the late recap lands on the original only", got[0] == 2 and len(pend) >= 1 and all(got[1]) and not any(got[2]), (pend, got))
        sums = await pg.evaluate("chapsOf(DB.sessions[0]).map(c=>!!c.sum)")
        check("slow recap: it still lands in the background and is saved", st["recap_done"] > before and sums.count(True) >= 2, (sums, st))
        check("no duplicate recap requests for the same chapter", st["recaps"] <= len(sums), (st["recaps"], sums))
        await br.close()
asyncio.run(main()); srv.terminate()
print("ERRORS:", errs); bad = [n for n, ok in results if not ok]; print(f"{len(results)-len(bad)} passed, {len(bad)} failed"); sys.exit(1 if bad or errs else 0)
