"""v41: metadata repair (trial setting, off by default). Stand-in model; no real requests.
Run: python tests/repair_v41.py   (prints "ERRORS: []" when everything passes)"""
import asyncio, json, os, sys, subprocess, time
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.normpath(os.path.join(HERE, "..", "site")); PORT = 8816
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
results, errs = [], []
st = {"n": 0, "repairs": 0, "mode": {}, "delay": 0, "bad": False}
def check(name, cond, info=""): results.append((name, bool(cond))); print(("ok  " if cond else "FAIL"), name, "" if cond else info)
async def model(route):
    b = json.loads(route.request.post_data); txt = json.dumps(b["messages"])
    if not b.get("stream"):
        if "write its metadata" in txt:
            st["repairs"] += 1; st["last_repair"] = b["messages"][0]["content"]
            if st["delay"]: await asyncio.sleep(st["delay"])
            body = "nonsense with no keys" if st["bad"] else "[[META]]\nEVENTS: 4 | reveal | Kevin, Mira | cellar | Kevin shows Mira the hidden ledger | none\nLEARNED: Mira: Kevin has the hidden ledger (he showed her)\nSCENE: cellar | Kevin, Mira | night\nNEXT: should be dropped | x | y\nGOAL: should be dropped"
        else: body = "- note"
        return await route.fulfill(status=200, content_type="application/json", body=json.dumps({"choices": [{"message": {"content": body}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 900, "completion_tokens": 80}}))
    st["n"] += 1; n = st["n"]; m = st["mode"].get(n, "full")
    meta = {"full": f"\n\n[[META]]\nEVENTS: 3 | action | Kevin | hall | Kevin performs deed number {n} | none\nLEARNED: none\nSCENE: hall | Kevin | day\nNEXT: a | b | c",
            "none": "", "partial": "\n\n[[META]]\nNEXT: a | b | c"}[m]
    t = f"Reply number {n}. Kevin takes Mira down to the cellar and shows her the hidden ledger." + meta
    await route.fulfill(status=200, content_type="text/event-stream", body="data: " + json.dumps({"choices": [{"delta": {"content": t}}]}) + "\n\ndata: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5, "completion_tokens": 5}}) + "\n\ndata: [DONE]\n\n")
SEED = "(f)=>{localStorage.clear();localStorage.setItem('story-forge-v2',JSON.stringify(Object.assign({key:'k',migrated:true,memv2:true,modes:[{n:'S',id:'a/b',d:''}],mode:0,stories:[{id:'s1',kind:'story',title:'Ledger Test',setting:'A hall.',entries:[],stats:[],endings:[],starts:[]}]},f)))}"
async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(args=["--no-sandbox"]); pg = await (await br.new_context(viewport={"width": 390, "height": 844})).new_page(); pg.set_default_timeout(20000)
        pg.on("pageerror", lambda e: errs.append(str(e))); await pg.route("https://openrouter.ai/**", model)
        async def start(flags):
            st.update(n=0, repairs=0, delay=0, bad=False)
            await pg.goto(f"http://127.0.0.1:{PORT}/index.html"); await pg.wait_for_selector(".cta"); await pg.evaluate(SEED, flags); await pg.reload(); await pg.wait_for_selector(".cta")
            await pg.click(".card:has-text('Ledger Test')"); await pg.fill("input[placeholder='Your character’s name']", "Anna"); await pg.click("button:text-is('Start story')"); await pg.wait_for_selector("text=Reply number 1")
        async def send(text, n):
            await pg.fill("#input", text); await pg.click("button[aria-label='Send']"); await pg.wait_for_selector(f"text=Reply number {n}")
            for _ in range(200):
                if not await pg.evaluate("busy||RPQ.size>0"): break
                await pg.wait_for_timeout(100)
        S = lambda: pg.evaluate("JSON.parse(JSON.stringify(DB.sessions[0]))")
        # off by default
        st["mode"] = {2: "none"}; await start({}); await send("I wait.", 2)
        check("off by default: no repair request when a reply has no metadata", st["repairs"] == 0)
        # on
        st["mode"] = {2: "none", 3: "partial"}; await start({"metaRepair": True}); await send("I wait.", 2)
        s = await S(); ai = s["turns"][-1]; d = s["memDiag"][-1]
        check("on: one repair request for a reply with no metadata", st["repairs"] == 1)
        check("repair prompt uses the reply as evidence and forbids invention", "only evidence" in st["last_repair"] and "Do not invent" in st["last_repair"] and "hidden ledger" in st["last_repair"])
        check("repaired event, knowledge and scene recorded in memory", any("hidden ledger" in e["text"] for e in s["mem"]["events"]) and s["mem"]["scene"]["where"] == "cellar" and any("ledger" in f["text"] for f in s["mem"]["facts"]))
        check("only EVENTS / LEARNED / SCENE kept from the repair (NEXT and GOAL dropped)", "NEXT" not in ai.get("rmt", "") and "GOAL" not in ai.get("rmt", "") and "EVENTS" in ai.get("rmt", ""), ai.get("rmt"))
        check("repaired block stored separately as rmt", "rmt" in ai and "mt" not in ai)
        check("diagnostics: native block missing, repair flagged ok with time and tokens", d["block"] is False and d.get("rp", {}).get("ok") is True and d["rp"].get("tok") == [900, 80], d)
        check("story text unchanged, nothing shown", "EVENTS" not in ai["text"] and "EVENTS:" not in await pg.inner_text("body"))
        await send("I wait again.", 3)
        check("partial native block (marker present, keys missing): no repair", st["repairs"] == 1)
        msgs = await pg.evaluate("buildMsgs(DB.sessions[0],getStory('s1'),DB.sessions[0].turns.slice(),'x')")
        repaired = [m["content"] for m in msgs if m["role"] == "assistant" and "hidden ledger | none" in m["content"]]
        check("repaired metadata appears as one delimited history example", len(repaired) == 1 and "[[META]]" in repaired[0] and "GOAL:" not in repaired[0])
        # undo works with a repaired delta
        await pg.evaluate("()=>{const se=DB.sessions[0];memDrop(se,[se.turns.length-3]);}")
        s = await S()
        check("deleting a repaired reply removes its repaired event (undo works)", not any("hidden ledger" in e["text"] for e in s["mem"]["events"]))
        # unreadable repair
        st["mode"] = {2: "none"}; await start({"metaRepair": True}); st["bad"] = True; await send("I wait.", 2)
        s = await S(); d = s["memDiag"][-1]
        check("unreadable repair: nothing recorded, reason logged, turn continues", d.get("rp", {}).get("ok") is False and d["rp"].get("why") == "unreadable" and not any("hidden ledger" in e["text"] for e in (s.get("mem") or {}).get("events", [])))
        # timeout
        st["mode"] = {2: "none"}; await start({"metaRepair": True, "repairWait": 2}); st["delay"] = 6; t0 = time.time(); await send("I wait.", 2)
        s = await S(); d = s["memDiag"][-1]
        check(f"slow repair: gives up at the deadline ({time.time()-t0:.1f}s) and the turn continues", d.get("rp", {}).get("why") == "timeout" and time.time() - t0 < 6, d.get("rp"))
        # stale: reply text changes before the repair returns
        st["mode"] = {2: "none"}; await start({"metaRepair": True}); st["delay"] = 3
        await pg.fill("#input", "I wait."); await pg.click("button[aria-label='Send']"); await pg.wait_for_selector("text=Reply number 2")
        await pg.wait_for_timeout(500); await pg.evaluate("()=>{const se=DB.sessions[0];const a=se.turns[se.turns.length-1];a.text=a.text+' (edited)'}")
        for _ in range(200):
            if not await pg.evaluate("busy||RPQ.size>0"): break
            await pg.wait_for_timeout(100)
        s = await S(); d = s["memDiag"][-1]
        check("late repair after the reply changed is discarded", d.get("rp", {}).get("why") == "stale" and not any("hidden ledger" in e["text"] for e in s["mem"]["events"]), d.get("rp"))
        # background: a slow repair doesn't block the story
        st["mode"] = {2: "none"}; await start({"metaRepair": True}); st["delay"] = 5
        t0 = time.time(); await pg.fill("#input", "I wait."); await pg.click("button[aria-label='Send']"); await pg.wait_for_selector("text=Reply number 2")
        for _ in range(80):
            if not await pg.evaluate("busy"): break
            await pg.wait_for_timeout(100)
        dt = time.time() - t0; pend = await pg.evaluate("RPQ.size")
        check(f"background: the turn finishes without waiting for the repair ({dt:.1f}s, repair pending={pend})", dt < 3 and pend == 1)
        # the player moves on before the slow repair returns: discarded, not applied to the newer turn
        st["mode"] = {2: "none", 3: "full"}
        await pg.fill("#input", "Next."); await pg.click("button[aria-label='Send']"); await pg.wait_for_selector("text=Reply number 3")
        for _ in range(200):
            if not await pg.evaluate("busy||RPQ.size>0"): break
            await pg.wait_for_timeout(100)
        s = await S(); d2 = [x for x in s["memDiag"] if x.get("rp")]
        check("player moved on before the repair returned: discarded as stale, newer turn untouched", d2 and d2[-1]["rp"].get("why") == "stale" and not any("hidden ledger" in e["text"] for e in s["mem"]["events"]), [x.get("rp") for x in d2])
        # replay helper (dry)
        st["mode"] = {2: "none", 3: "none"}; await start({}); await send("I wait.", 2); await send("Again.", 3); st["bad"] = False; st["delay"] = 0
        out = await pg.evaluate("metaRepairReplay(DB.sessions[0]).then(x=>x.map(y=>({t:y.t,ok:y.ok,has:/hidden ledger/.test(y.block||'')})))")
        s = await S()
        check("replay: repairs each missed reply without changing memory", len(out) == 2 and all(o["ok"] and o["has"] for o in out) and not any("hidden ledger" in e["text"] for e in s["mem"]["events"]), out)
        # name guard: people the reply never mentions are dropped (from the real-model review: reply 45, reply 63)
        r = await pg.evaluate("""()=>{const p=SFMemory.parseMeta('[[META]]\\nEVENTS: 3 | action | Corwin Hale, Vey Calder | yard | The sexton-coated man stepped back | Brother Aled, an unnamed man coiling rope\\nLEARNED: Vey Calder: something (seen); Ilse Varn: the yard is watched (saw it)\\nSCENE: yard | Corwin Hale, Vey Calder, unknown man, the cook | night');
          const out=repairFilter(p,'Corwin\\ncame into the yard. The sexton-coated man stepped back. The cook watched you.','Ilse Varn');
          return {who:out.events[0].who,wit:out.events[0].wit,learned:out.learned.map(l=>l.who),scene:out.scene.who,dropped:out.dropped}}""")
        check("name guard keeps people the reply names (even after a line break), and the player", r["who"] == ["Corwin Hale"] and r["learned"] == ["Ilse Varn"] and "the cook" in r["scene"] and "Corwin Hale" in r["scene"], r)
        check("name guard drops people the reply never mentions and 'unknown/unnamed' labels", "Vey Calder" not in r["scene"] and r["wit"] == [] and "unknown man" not in r["scene"] and "LEARNED:Vey Calder" in r["dropped"], r)
        r2 = await pg.evaluate("""()=>{const p=SFMemory.parseMeta('[[META]]\\nEVENTS: 3 | action | Vey Calder, Lady Orla Brannock | cellar | crates were moved | Brother Aled\\nLEARNED: none\\nSCENE: cellar | Vey Calder, Lady Orla Brannock, Brother Aled | night');
          const out=repairFilter(p,'Six crates marked in Calder colours stood by the wall. Orla had asked about them. Aled said nothing.','Ilse Varn');return {who:out.events[0].who,wit:out.events[0].wit,scene:out.scene.who}}""")
        check("name guard: a surname alone ('Calder crates') doesn't let Vey Calder through; first names after titles do", r2["who"] == ["Lady Orla Brannock"] and r2["wit"] == ["Brother Aled"] and "Vey Calder" not in r2["scene"], r2)
        # no-reasoning switch: only on helper calls to OpenCode, never on story turns
        bodies = []
        async def oc(route):
            if route.request.method == "OPTIONS": return await route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*"})
            b = json.loads(route.request.post_data); bodies.append(b)
            if not b.get("stream"): return await route.fulfill(status=200, content_type="application/json", headers={"access-control-allow-origin": "*"}, body=json.dumps({"choices": [{"message": {"content": "[[META]]\nEVENTS: none\nLEARNED: none\nSCENE: hall | Kevin | day"}}]}))
            await route.fulfill(status=200, content_type="text/event-stream", headers={"access-control-allow-origin": "*"}, body="data: " + json.dumps({"choices": [{"delta": {"content": "Reply number 1. Kevin waits."}}]}) + "\n\ndata: [DONE]\n\n")
        await pg.route("https://oc.example/**", oc)
        for mode, key, val in (("effort", "reasoning_effort", "none"), ("thinking", "thinking", {"type": "disabled"})):
            bodies.clear()
            await pg.goto(f"http://127.0.0.1:{PORT}/index.html"); await pg.wait_for_selector(".cta")
            await pg.evaluate(SEED, {"prov": "opencode", "ocKey": "k", "ocProxy": "https://oc.example", "metaRepair": True, "ocLite": mode}); await pg.reload(); await pg.wait_for_selector(".cta")
            await pg.click(".card:has-text('Ledger Test')"); await pg.fill("input[placeholder='Your character’s name']", "Anna"); await pg.click("button:text-is('Start story')"); await pg.wait_for_selector("text=Reply number 1")
            for _ in range(100):
                if not await pg.evaluate("busy||RPQ.size>0"): break
                await pg.wait_for_timeout(100)
            story = [b for b in bodies if b.get("stream")]; helper = [b for b in bodies if not b.get("stream") and "write its metadata" in json.dumps(b["messages"])]
            check(f"ocLite={mode}: repair request carries {key}, story turn does not", helper and helper[-1].get(key) == val and story and key not in story[-1], (len(helper), len(story)))
        await br.close()
asyncio.run(main()); srv.terminate()
print("ERRORS:", errs); bad = [n for n, ok in results if not ok]; print(f"{len(results)-len(bad)} passed, {len(bad)} failed"); sys.exit(1 if bad or errs else 0)
