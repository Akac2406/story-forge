"""Offline asset manifest integrity check; does not need Playwright."""
from pathlib import Path
import re
site = Path(__file__).resolve().parent.parent / 'site'
sw = (site / 'sw.js').read_text()
files = re.findall(r'"([^"]+)"', sw.split('const APP_FILES = [', 1)[1].split('];', 1)[0])
assert 'sf-v86' in sw
for name in ('index.html', 'listen.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png'):
    assert name in files, f'not precached: {name}'
missing = [name for name in files if name != './' and not (site / name).is_file()]
assert not missing, f'missing offline assets: {missing}'
print('PASS v85 precache: %d assets present' % len(files))
print('ERRORS: []')
