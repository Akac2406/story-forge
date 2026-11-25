"""Open v87 canon controls at phone and desktop widths with a simulated narrator."""
import json
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright
import menu_helper  # opens collapsible novel-menu categories for older tests (UI overhaul)


SITE = Path(__file__).resolve().parent.parent / "site"
SEED = {
    "key": "sk-or-test-fixture",
    "migrated": True,
    "rec": False,
    "wikiOn": False,
    "stories": [{
        "id": "world", "kind": "story", "title": "Harbor",
        "follow": "strict", "canon": "", "entries": [], "stats": [], "endings": [],
        "worldEra": {"era": "Medieval", "date": "1450"}
    }],
    "sessions": [{
        "id": "play", "storyId": "world", "char": {"name": "Mira"}, "note": "Stay at the harbor.",
        "turns": [{"role": "user", "text": "(OOC: from now on, keep Mira at the harbor.)"},
                  {"role": "ai", "text": "Mira waits by the dock.", "tid": "opening"}],
        "chaps": [{"i": 0, "t": "Arrival"}], "chapN": 0,
        "stats": {}, "mems": [], "sugg": [], "ended": [], "updated": 1
    }]
}


def check(browser, width, url):
    context = browser.new_context(viewport={"width": width, "height": 844}, service_workers="block")
    page = context.new_page()
    page.set_default_timeout(8000)
    errors, requests = [], []
    failing = False

    def narrator(route):
        request = route.request
        if not request.url.endswith("/chat/completions") or request.method != "POST":
            return route.fulfill(status=200, json={})
        if failing:
            return route.fulfill(status=500, body="Simulated failure")
        body = request.post_data_json
        if not body.get("stream"):
            return route.fulfill(json={"choices": [{"message": {"content": "- No update needed."}}]})
        requests.append(body)
        reply = f"Mock harbor reply {len(requests)}.\n\n[[META]]\nCANON: Lantern | drift | The lantern was extinguished.\n"
        events = [{"choices": [{"delta": {"content": reply}}]}, {"choices": [{"delta": {}, "finish_reason": "stop"}]}]
        return route.fulfill(content_type="text/event-stream", body="".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n")

    try:
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("https://**/*", lambda route: narrator(route) if "openrouter.ai/" in route.request.url else route.abort())
        page.add_init_script(f"""if (!localStorage.getItem('story-forge-v2')) localStorage.setItem('story-forge-v2', {json.dumps(json.dumps(SEED))})""")
        page.goto(url)
        page.locator("header").wait_for()
        excerpt = ('The lantern burned blue over the harbor. Twelve little fishing boats came in with the tide. '
                   '"It will rain before dawn," Mara said. The keeper pulled her coat tight. '
                   'The rain would find them on the quay, as it always did. ')
        page.evaluate("text => addRef('Fixture book', text, 'world')", excerpt * 5)
        page.evaluate("go({n:'edit',id:'world'})")
        page.get_by_role("heading", name="Style samples").wait_for()
        page.get_by_role("button", name="Suggest from attached book").click()
        page.get_by_role("button", name="Use suggestion 1").click()
        expect(page.get_by_label("Style sample 1", exact=True)).to_have_value(re.compile("lantern burned blue"))
        page.get_by_label("Style sample 1", exact=True).fill("The tide rose softly in the dark.")
        page.get_by_role("button", name="Add style sample").click()
        page.get_by_role("button", name="Add style sample").click()
        expect(page.get_by_role("button", name="Add style sample")).to_be_disabled()
        page.get_by_role("button", name="Remove sample 3").click()
        expect(page.get_by_role("button", name="Add style sample")).to_be_enabled()
        page.locator("header").get_by_role("button", name="Save", exact=True).click()
        assert page.evaluate("getStory('world').styleSamples.length") == 1
        page.evaluate("go({n:'chat',id:'play'})")

        def menu(name):
            page.get_by_role("button", name="Menu", exact=True).click()
            page.get_by_role("button", name=name, exact=False).click()

        menu("User notes")
        page.get_by_role("button", name="Add story note").click()
        page.get_by_label("Instruction").fill("Lanterns are made of glass.")
        page.get_by_label("Priority").select_option("must")
        page.get_by_label("Scope").select_option("keyword")
        page.get_by_label("Keywords", exact=True).fill("lantern")
        page.get_by_role("button", name="Save note").click()
        expect(page.get_by_label("For this story")).to_have_value("Stay at the harbor.")
        page.get_by_role("button", name="Done", exact=True).click()

        menu("Canon Bible")
        page.get_by_role("button", name="Add canon entry").click()
        page.get_by_label("Name", exact=True).fill("Lantern")
        page.get_by_label("Fact", exact=True).fill("The lighthouse lantern burns blue.")
        page.get_by_label("Lock fact and always include it").check()
        page.get_by_role("button", name="Save entry").click()
        expect(page.get_by_text("Locked", exact=False).last).to_be_visible()
        page.get_by_role("button", name="Done", exact=True).click()

        menu("Canon mode")
        page.get_by_label("Canon mode").select_option("strict")
        page.get_by_role("button", name="Done", exact=True).click()
        page.locator("#input").fill("I check the lantern.")
        page.get_by_role("button", name="Send", exact=True).click()
        expect(page.get_by_text("Mock harbor reply 1.", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Stop", exact=True)).to_have_count(0)
        prompt = requests[0]["messages"][0]["content"]
        for expected in ("The lighthouse lantern burns blue.", "Lanterns are made of glass.", "Canon mode — Strict", "1450",
                         "STYLE SAMPLES", "The tide rose softly in the dark."):
            assert expected in prompt, expected

        menu("Prompt inspector")
        expect(page.get_by_text("Protected instructions budget")).to_be_visible()
        page.get_by_text("Notes and standing directions", exact=True).click()
        expect(page.get_by_text("Lanterns are made of glass.", exact=True)).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.get_by_role("button", name="Done", exact=True).click()

        menu("Canon warnings")
        expect(page.get_by_text("The lantern was extinguished.", exact=True)).to_be_visible()
        page.get_by_role("button", name="Accept departure").click()
        expect(page.get_by_text("drift · accepted", exact=True)).to_be_visible()
        page.get_by_role("button", name="Done", exact=True).click()

        before = page.evaluate("JSON.stringify(DB.sessions[0])")
        def start_rewrite():
            page.get_by_role("button", name="Open the chapter list").click()
            page.get_by_role("button", name="Regenerate Chapter 1 · Arrival in a new branch").click()
            page.get_by_role("button", name="Regenerate in a new branch", exact=True).click()

        failing = True
        start_rewrite()
        expect(page.locator("#toast")).to_contain_text("Your original chapter is kept")
        assert page.evaluate("DB.sessions.length") == 1
        assert page.evaluate("JSON.stringify(DB.sessions[0])") == before

        failing = False
        start_rewrite()
        expect(page.locator("#toast")).to_contain_text("Chapter regenerated in a new branch.")
        assert page.evaluate("DB.sessions.length") == 2
        assert page.evaluate("JSON.stringify(DB.sessions[0])") == before
        assert page.evaluate("DB.sessions[1].turns.length") == 4
        assert not errors, errors
    finally:
        context.close()


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=SITE)) as server:
        Thread(target=server.serve_forever, daemon=True).start()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                for width in (390, 1280):
                    check(browser, width, f"http://127.0.0.1:{server.server_port}/index.html")
            finally:
                browser.close()
        server.shutdown()
    print("ERRORS: []")
