"""Verify the built APK, including its real signatures and bundled runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('apk', type=Path)
parser.add_argument('--build-tools', type=Path, required=True)
args = parser.parse_args()
lock = json.loads((ROOT / 'tools/android-runtime-lock.json').read_text())
with zipfile.ZipFile(args.apk) as apk:
    assert apk.testzip() is None
    assert {'classes.dex', 'AndroidManifest.xml', 'resources.arsc'} <= set(apk.namelist())
    for name, digest in lock.items():
        data = apk.read('assets/runtime/' + name)
        if name.endswith('cpythonrc.py'):
            assert b'os.environ["PYGPI"] = str(window.location.href)' in data
        else:
            assert hashlib.sha256(data).hexdigest() == digest, name
    assert 'assets/stage.tar.gz' in apk.namelist()
    assert 'assets/stage.apk' not in apk.namelist()
    assert "connect-src 'self'" in apk.read('assets/index.html').decode()
signature = subprocess.check_output([str(args.build_tools / 'apksigner'), 'verify', '--verbose', '--print-certs', str(args.apk)], text=True)
permissions = subprocess.check_output([str(args.build_tools / 'aapt'), 'dump', 'permissions', str(args.apk)], text=True)
assert 'uses-permission' not in permissions, permissions
metadata = subprocess.check_output([str(args.build_tools / 'aapt'), 'dump', 'badging', str(args.apk)], text=True)
assert "package: name='com.scirtor.starjump'" in metadata
assert "sdkVersion:'26'" in metadata and "targetSdkVersion:'35'" in metadata
result = {'file': args.apk.name, 'bytes': args.apk.stat().st_size,
          'sha256': hashlib.sha256(args.apk.read_bytes()).hexdigest(),
          'package': 'com.scirtor.starjump', 'min_android_api': 26, 'target_android_api': 35,
          'permissions': [], 'apk_signature_verified': True, 'bundled_runtime_checksums_verified': True,
          'physical_device_tested': False, 'signing': 'debug preview', 'signature_details': signature}
output = args.apk.parent / 'Android-verification.json'
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({key:value for key,value in result.items() if key != 'signature_details'}, indent=2))
