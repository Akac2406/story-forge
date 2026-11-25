"""Test-only helper (UI overhaul, ChatGPT's collapsible novel menu): older tests click menu items directly.
Importing this module makes every new Playwright page open all novel-menu categories as soon as the drawer appears,
so those tests can still reach every control. It does not change the app. Use: `import menu_helper` after importing Playwright."""
from playwright.sync_api import Browser, BrowserContext
OPEN_ALL = """(()=>{const go=()=>document.querySelectorAll('details.story-tools').forEach(d=>{if(d.hasAttribute('name'))d.removeAttribute('name');d.open=true});
new MutationObserver(go).observe(document,{childList:true,subtree:true});document.addEventListener('DOMContentLoaded',go)})()"""
def _wrap(orig):
    def new_page(self, *a, **k):
        p = orig(self, *a, **k)
        p.add_init_script(OPEN_ALL)
        return p
    return new_page
if not getattr(Browser.new_page, "_sf_menu", False):
    Browser.new_page = _wrap(Browser.new_page); Browser.new_page._sf_menu = True
    BrowserContext.new_page = _wrap(BrowserContext.new_page); BrowserContext.new_page._sf_menu = True
