"""Prompt-only creation opens a normal playthrough after a single successful request."""
import json
import socket
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlparse
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[1] / "site"
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
base = f"http://127.0.0.1:{port}"
idea = "A courier brings a sealed letter to a city that has forgotten its name."
opening = "The archivist lifts her lantern as fog closes around the city gates."
calls, errors, lookups = [], [], []
source_title = "Example Film (2010 film)"
overview = "The story takes place on a fictional island."


def mock(route):
    if route.request.url.startswith(base + "/"):
        route.continue_()
    elif route.request.url.startswith("https://en.wikipedia.org/w/api.php?"):
        title = parse_qs(urlparse(route.request.url).query).get("titles", [""])[0]
        lookups.append(title)
        route.fulfill(json={"query": {"pages": [{"title": title, "extract": overview}]}})
    elif route.request.url.startswith("https://openrouter.ai/"):
        calls.append(json.loads(route.request.post_data))
        payload = '{"title":"Missing opening"}' if len(calls) == 1 else json.dumps(
            {"title": "City Without a Name", "setting": "A walled city with lost memories.", "opening": opening})
        route.fulfill(json={"choices": [{"message": {"content": payload}}]})
    else:
        route.abort()


server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                          cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(.5)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True,
                                has_touch=True, service_workers="block")
        page.set_default_timeout(12000)
        page.route("**/*", mock)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base)
        page.wait_for_function("!!idb")
        page.evaluate("""()=>{
            DB.key='fixture';DB.migrated=true;DB.modes=[{id:'fixture/model',n:'Mock'}];
            DB.stories=[{id:'existing',title:'Existing story',kind:'story'}];
            DB.chars=[{id:'existing-avatar',name:'Existing Avatar'}];
            save();go({n:'home',tab:'create'});
        }""")
        page.get_by_role("button", name="Start with a prompt").click()
        page.get_by_role("button", name="Start story", exact=True).click()
        page.get_by_text("Enter a story idea to start.").wait_for()
        assert not calls
        prompt = page.get_by_label("Story prompt")
        prompt.fill(idea)
        page.get_by_role("button", name="Start story", exact=True).click()
        page.get_by_text("The model didn’t return a usable opening. Try again.").wait_for()
        assert prompt.input_value() == idea
        assert page.evaluate("[DB.stories.length, DB.sessions.length]") == [1, 0]

        assert not lookups
        page.get_by_label("Source title (optional)").fill(source_title)
        page.get_by_role("button", name="Start story", exact=True).click()
        page.get_by_text(opening, exact=True).wait_for()
        assert len(calls) == 2
        assert json.loads(calls[-1]["messages"][-1]["content"]) == {
            "premise": idea, "sourceTitle": source_title, "overview": overview}
        assert lookups == [source_title]
        assert page.evaluate("simpleSourceTitle('Based on: Example Film (2010 film)\\nOpen at dawn')") == source_title
        page.get_by_role("button", name="Sources", exact=True).click()
        page.get_by_role("link", name=source_title + " · Wikipedia").wait_for()
        page.get_by_label("Source title", exact=True).fill("Example Sequel")
        page.get_by_role("button", name="Find source", exact=True).click()
        page.get_by_text("Saved for future replies.").wait_for()
        page.get_by_role("button", name="Done", exact=True).click()
        assert lookups == [source_title, "Example Sequel"]
        assert page.evaluate("getStory(DB.sessions[0].storyId).simpleSource.title") == "Example Sequel"
        assert page.evaluate("""()=>{const se=DB.sessions[0];
            return buildMsgs(se,getStory(se.storyId),se.turns,'Look around')[0].content.includes('Source overview for Example Sequel:');
        }""")
        assert page.evaluate("DB.sessions[0].char.name") == ""
        assert page.evaluate("DB.sessions[0].note") == idea
        page.get_by_role("button", name="Character images", exact=True).wait_for()
        page.get_by_role("button", name="User notes", exact=True).click()
        notes = page.get_by_label("For this story")
        assert notes.input_value() == idea
        notes.fill(idea + "\nMy avatar wears a green cloak.")
        page.get_by_role("button", name="Save notes").click()

        page.wait_for_function("!saveT")
        page.reload()
        page.wait_for_function("!!idb && DB.sessions.length===1")
        assert page.evaluate("getStory('existing').title") == "Existing story"
        assert page.evaluate("DB.chars[0].name") == "Existing Avatar"
        assert "green cloak" in page.evaluate("DB.sessions[0].note")
        assert page.evaluate("getStory(DB.sessions[0].storyId).simpleSource.title") == "Example Sequel"
        page.evaluate("go({n:'story',id:DB.sessions[0].storyId})")
        page.get_by_role("button", name="Continue", exact=True).wait_for()
        page.get_by_role("button", name="Advanced setup", exact=True).click()
        page.get_by_label("Saved avatars").wait_for()
        assert len(calls) == 2
        assert not errors, errors
        browser.close()
finally:
    server.terminate()
    server.wait()
print("ERRORS: []")
