"""Run after tools/prepare_android.py to validate the packaged offline inputs."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'android/app/src/main/assets'
pytestmark = pytest.mark.skipif(not ASSETS.exists(), reason='Android assets not built yet')


def test_native_shell_uses_local_runtime_and_disables_service_worker():
    html = (ASSETS / 'index.html').read_text()
    boot = (ASSETS / 'boot.js').read_text()
    assert "cdn:new URL('./runtime/0.9.3/', location.href).href" in html
    assert "script.src = new URL('./runtime/0.9.3/pythons.js', location.href).href" in boot
    assert 'if (false)' in boot
    assert "connect-src 'self'" in html
    assert not (ASSETS / 'stage.apk').exists()
    assert (ASSETS / 'stage.tar.gz').is_file()


def test_bundled_runtime_matches_reviewed_hashes_and_rc_initialization_order():
    lock = json.loads((ROOT / 'tools/android-runtime-lock.json').read_text())
    for name, digest in lock.items():
        if name.endswith('cpythonrc.py'):
            continue  # Reviewed source patch is checked below.
        assert hashlib.sha256((ASSETS / 'runtime' / name).read_bytes()).hexdigest() == digest
    rc = (ASSETS / 'runtime/0.9.3/cpythonrc.py').read_text()
    marker = 'from platform import window, document, ffi'
    patch = 'os.environ["PYGPI"] = str(window.location.href).rsplit("/", 1)[0] + "/runtime/"'
    assert rc.index(marker) < rc.index(patch) < rc.index('        apply_patches()')
    compile(rc, 'cpythonrc.py', 'exec')


def test_manifest_does_not_request_network_or_storage_access():
    manifest = ET.parse(ROOT / 'android/app/src/main/AndroidManifest.xml').getroot()
    assert not manifest.findall('uses-permission')
    application = manifest.find('application')
    assert application.attrib['{http://schemas.android.com/apk/res/android}usesCleartextTraffic'] == 'false'
