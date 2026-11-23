"""v64: test copies (deploy previews, pinned deploy links) show a notice linking to the real app; the real app does not.
Hostnames are simulated by routing them to the local files. Run: python tests/test_copy_banner_v64.py"""
import os, sys, mimetypes
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.join(HERE, "..", "site")
fails = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
def local(route):
    path = route.request.url.split("/", 3)[3].split("?")[0] or "index.html"
    f = os.path.join(APP, path)
    if not os.path.isfile(f): return route.fulfill(status=404, body="")
    route.fulfill(status=200, body=open(f, "rb").read(), content_type=mimetypes.guess_type(f)[0] or "text/plain")
HOSTS = {"celebrated-brigadeiros-580c41.netlify.app": False, "deploy-preview-3--celebrated-brigadeiros-580c41.netlify.app": True,
         "6b03489a2ca6c1ad3d9b8f36--celebrated-brigadeiros-580c41.netlify.app": True, "main--celebrated-brigadeiros-580c41.netlify.app": True,
         "some-other-site.netlify.app": False}
errs = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for host, want in HOSTS.items():
        ctx = b.new_context(viewport={"width": 390, "height": 844}, service_workers="block"); pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.route("https://" + host + "/**", local)
        pg.goto("https://" + host + "/index.html"); pg.wait_for_selector(".cta")
        has = pg.locator("#testcopy").count() == 1
        ok(has == want, f"{host}: notice {'shown' if want else 'not shown'}")
        if want:
            ok(pg.locator("#testcopy a").get_attribute("href") == "https://celebrated-brigadeiros-580c41.netlify.app/", "  links to the real app")
            ok(pg.evaluate("document.documentElement.scrollWidth") <= 390, "  fits a phone screen")
        ctx.close()
    b.close()
ok(not errs, "no page errors " + str(errs[:2]))
print("ERRORS:", fails); sys.exit(1 if fails else 0)
