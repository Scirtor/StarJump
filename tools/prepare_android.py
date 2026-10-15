"""Bundle the same game plus a pinned Python/WASM runtime for offline Android.

No Android SDK license is accepted by this script. APK compilation uses an
already configured Android SDK locally, or the GitHub-hosted build environment.
"""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = 'https://pygame-web.github.io/cdn/'

def prepare(skip_web=False):
    if not skip_web:
        subprocess.run([sys.executable, str(ROOT / 'tools/build_web.py')], check=True)
    web = ROOT / 'build/stage/build/web'
    if not (web / 'stage.tar.gz').exists():
        raise SystemExit('Build the web game first.')
    cache = ROOT / 'build/android-runtime'
    lock = json.loads((ROOT / 'tools/android-runtime-lock.json').read_text())

    def download(item):
        name, digest = item
        path = cache / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            with urllib.request.urlopen(UPSTREAM + name, timeout=120) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != digest:
                raise RuntimeError(f'Upstream checksum changed: {name}; review before updating the lock.')
            path.write_bytes(data)
        return name

    with ThreadPoolExecutor(max_workers=4) as pool:
        for name in pool.map(download, lock.items()):
            print('Runtime verified:', name)

    target = ROOT / 'android/app/src/main/assets'
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(web, target)
    for name in ('stage.apk', 'sw.js', 'favicon.png'):
        (target / name).unlink(missing_ok=True)
    shutil.copytree(cache, target / 'runtime')
    rc_path = target / 'runtime/0.9.3/cpythonrc.py'
    rc = rc_path.read_text()
    # pep0723's wheel index is separate from the JavaScript interpreter CDN.
    marker = '        from platform import window, document, ffi\n'
    if marker not in rc:
        raise RuntimeError('Pygbag initialization changed; review the offline wheel-index patch.')
    rc = rc.replace(marker, '        from platform import window, document, ffi\n        os.environ["PYGPI"] = str(window.location.href).rsplit("/", 1)[0] + "/runtime/"\n', 1)
    rc_path.write_text(rc)
    html_path = target / 'index.html'
    html = html_path.read_text()
    html = html.replace("cdn:'https://pygame-web.github.io/cdn/0.9.3/'", "cdn:new URL('./runtime/0.9.3/', location.href).href")
    html = html.replace("document.getElementById('tools').hidden=false", "document.getElementById('tools').hidden=true")
    html = html.replace("document.getElementById('tools').hidden=playing", "document.getElementById('tools').hidden=true")
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="default-src \'self\' data: blob:; script-src \'self\' \'unsafe-inline\' \'unsafe-eval\'; connect-src \'self\'; img-src \'self\' data: blob:; style-src \'self\' \'unsafe-inline\'; frame-src \'self\'; worker-src \'self\' blob:">')
    # The browser shell is already part of an installed application.
    html = re.sub(r'<nav id="tools".*?</nav>', '<nav id="tools" hidden><button id="install-help" hidden></button></nav>', html, flags=re.S)
    html_path.write_text(html)
    boot_path = target / 'boot.js'
    boot = boot_path.read_text().replace("if ('serviceWorker' in navigator && window.isSecureContext)", 'if (false)')
    boot = boot.replace("script.src = 'https://pygame-web.github.io/cdn/0.9.3/pythons.js';", "script.src = new URL('./runtime/0.9.3/pythons.js', location.href).href;")
    boot_path.write_text(boot)
    icon = ROOT / 'android/app/src/main/res/drawable/game_icon.png'
    icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(web / 'icons/icon-512.png', icon)
    (target / 'RUNTIME-NOTICE.txt').write_text(
        'StarJump bundles the Pygbag 0.9.3 / CPython 3.12 WebAssembly runtime and pygame-ce 2.5.7.\n'
        'Source/runtime: https://github.com/pygame-web/pygbag and https://pygame-web.github.io/cdn/\n'
        'Upstream checksums: tools/android-runtime-lock.json. All upstream license notices in the runtime/wheel are retained.\n'
        'Local adaptation: cpythonrc.py sets PYGPI to the bundled same-origin wheel directory.\n')
    print('Offline Android assets:', target)
    return target

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-web', action='store_true')
    prepare(parser.parse_args().skip_web)
