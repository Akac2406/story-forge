"""One vision request, direct Play, optional avatar notes, and Advanced setup."""
import json
import socket
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[1] / "site"
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
BASE = f"http://127.0.0.1:{port}"
OPENING = "A bell rings in the empty archive. The keeper sets a sealed letter on the desk."
FIXTURE = {"title": "The Silver Archive", "description": "A mystery in a forgotten archive.",
           "starts": ["The Library", "The Archive"], "selected_start": "The Archive",
           "prologue": OPENING, "characters": [{"name": "The Keeper", "role": "Archivist"}],
           "images": [{"shot": 1, "shows": "cover"}]}
calls, errors = [], []
fixture = BytesIO()
screenshot = Image.new("RGB", (360, 720), "#171832")
draw = ImageDraw.Draw(screenshot)
for stripe in range(16):
    shade = (30 + stripe * 11, 220 - stripe * 9, 80 + stripe * 5)
    draw.rectangle((stripe * 22, 100, stripe * 22 + 21, 390), fill=shade)
screenshot.save(fixture, format="PNG")


def mock(route):
    if route.request.url.startswith(BASE + "/"):
        route.continue_()
        return
    if not route.request.url.startswith("https://openrouter.ai/"):
        route.abort()
        return
    request = json.loads(route.request.post_data)
    calls.append(request)
    if not request["stream"]:
        prompt = request["messages"][0]["content"][0]["text"]
        if prompt.startswith("Describe this reference image"):
            assert "named Ash" in prompt
            route.fulfill(json={"choices": [{"message": {"content": "Silver hair and round spectacles."}}]})
            return
        data = dict(FIXTURE, prologue="") if len(calls) == 1 else FIXTURE
        route.fulfill(json={"choices": [{"message": {"content": json.dumps(data)}}]})
        return
    chunk = {"choices": [{"delta": {"content": "The keeper holds up the letter."}}]}
    final = {"choices": [{"delta": {}, "finish_reason": "stop"}]}
    route.fulfill(status=200, content_type="text/event-stream",
                  body=f"data: {json.dumps(chunk)}\n\ndata: {json.dumps(final)}\n\ndata: [DONE]\n\n")


server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                          cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(.5)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844},
                                is_mobile=True, has_touch=True, service_workers="block")
        page.set_default_timeout(12000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/*", mock)
        page.goto(BASE)
        page.wait_for_function("!!idb && !!window.SFFanUI")
        page.evaluate("""()=>{
            DB.key='fixture';DB.migrated=true;DB.modes=[{id:'fixture/model',n:'Mock'}];
            DB.chars=[{id:'saved-avatar',name:'Existing Avatar',desc:'Existing description'}];
            DB.stories=[{id:'saved-story',title:'Existing story',kind:'story',coverT:'data:image/png;base64,YQ=='}];
            save();go({n:'home',tab:'create'});
        }""")
        page.get_by_role("button", name="Make a story from screenshots").click()
        assert page.get_by_role("button", name="Simple", exact=True).get_attribute("aria-pressed") == "true"
        page.locator('input[type="file"]').set_input_files(
            {"name": "scene.png", "mimeType": "image/png", "buffer": fixture.getvalue()})
        page.get_by_role("button", name="Advanced", exact=True).click()
        page.get_by_role("button", name="Read screenshots", exact=True).wait_for()
        page.get_by_role("button", name="Simple", exact=True).click()
        page.get_by_role("button", name="Make story", exact=True).click()
        page.get_by_text("Couldn’t prepare an opening.", exact=False).wait_for()
        assert page.evaluate("DB.stories.length") == 1
        assert page.evaluate("DB.sessions.length") == 0

        page.get_by_role("button", name="Make story", exact=True).click()
        page.get_by_role("button", name="Play", exact=True).wait_for()
        assert page.get_by_label("Saved avatars").count() == 0
        assert page.evaluate("idbGet(DB.stories[0].cover).then(value=>value?.startsWith('data:image/jpeg'))")
        assert page.evaluate("document.documentElement.scrollWidth===innerWidth")
        assert len(calls) == 2
        assert all("quick, age-appropriate story setup" in req["messages"][0]["content"][0]["text"] for req in calls)

        page.get_by_role("button", name="Advanced setup", exact=True).click()
        assert page.get_by_label("Starting point").input_value() == "The Archive"
        page.get_by_label("Saved avatars").wait_for()
        page.get_by_role("button", name="Simple mode", exact=True).click()
        page.get_by_role("button", name="Character images", exact=True).click()
        page.locator('#sheetbg input[type="file"]').set_input_files(
            {"name": "keeper.png", "mimeType": "image/png", "buffer": fixture.getvalue()})
        page.get_by_label("Character name").fill("The Keeper")
        page.get_by_label("Appearance (optional)").fill("A dark green cloak with a brass clasp.")
        page.get_by_role("button", name="Save my description").click()
        page.get_by_label("Description the narrator sees").wait_for()
        assert len(calls) == 2
        page.get_by_role("button", name="Done", exact=True).click()
        page.get_by_role("button", name="Play", exact=True).click()
        page.get_by_text(OPENING, exact=True).wait_for()
        session = page.evaluate("DB.sessions[0]")
        assert session["char"]["name"] == ""
        assert session["start"] == "The Archive"
        assert len(calls) == 2
        assert page.locator("#input").get_attribute("placeholder").startswith("Describe your character")

        page.get_by_role("button", name="Character images", exact=True).click()
        page.locator('#sheetbg input[type="file"]').set_input_files(
            {"name": "avatar.png", "mimeType": "image/png", "buffer": fixture.getvalue()})
        page.get_by_label("Character name").fill("Ash")
        page.get_by_role("button", name="Describe image with AI").click()
        page.wait_for_function("getStory(DB.sessions[0].storyId).vis.some(x=>x.desc==='Silver hair and round spectacles.')")
        assert len(calls) == 3
        page.get_by_role("button", name="Done", exact=True).click()
        page.get_by_role("button", name="User notes", exact=True).click()
        notes = "My avatar is Ash, a librarian with silver hair."
        page.get_by_label("For this story").fill(notes)
        page.get_by_role("button", name="Save notes").click()
        page.locator("#input").fill("I introduce myself as Ash and ask about the letter.")
        page.get_by_role("button", name="Send", exact=True).click()
        page.get_by_text("The keeper holds up the letter.", exact=True).wait_for()
        assert len(calls) == 4
        assert "Character: The Keeper. Looks: A dark green cloak with a brass clasp." in calls[-1]["messages"][0]["content"]
        assert "Character: Ash. Looks: Silver hair and round spectacles." in calls[-1]["messages"][0]["content"]
        assert notes in calls[-1]["messages"][0]["content"]
        assert "I introduce myself as Ash" in calls[-1]["messages"][-1]["content"]
        assert "The player may define their avatar" in calls[-1]["messages"][0]["content"]
        page.wait_for_function("!busy && !saveT")
        page.reload()
        page.wait_for_function("DB.sessions.some(row=>row.simplePlay)")
        assert page.evaluate("DB.sessions.find(row=>row.simplePlay).note") == notes
        assert page.evaluate("getStory('saved-story').title") == "Existing story"
        assert page.evaluate("DB.chars[0].id") == "saved-avatar"
        assert page.evaluate("getStory(DB.sessions[0].storyId).vis.map(x=>x.name)") == ["The Keeper", "Ash"]
        assert not errors, errors
        browser.close()
finally:
    server.terminate()
    server.wait()
print("ERRORS: []")
