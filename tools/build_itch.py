"""Adapt the existing web release to itch.io's embedded HTML5 hosting.

Run build_web.py first. The standalone PWA and Android APK are unchanged.
itch.io serves ZIP game assets (stage.apk), and must not receive the gzip
alternative: its CDN transparently decompresses gzip payloads. Its iframe
also should not offer installation of a standalone PWA or register a worker.
"""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def build():
    target = ROOT / 'dist/StarJump-itch.zip'
    with zipfile.ZipFile(ROOT / 'dist/StarJump-web.zip') as source, zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as output:
        for item in source.infolist():
            if item.filename in ('sw.js', 'stage.tar.gz', 'manifest.webmanifest'):
                continue
            data = source.read(item)
            if item.filename == 'boot.js':
                boot = data.decode()
                marker = "if ('serviceWorker' in navigator && window.isSecureContext)"
                assert marker in boot, 'Review the changed bootstrap before exporting.'
                data = boot.replace(marker, 'if (false /* itch.io embed: no service worker or home-screen install */)').encode()
            elif item.filename == 'index.html':
                html = data.decode().replace('<link rel="manifest" href="manifest.webmanifest">', '')
                html = html.replace("document.getElementById('tools').hidden=false", "document.getElementById('tools').hidden=true")
                html = html.replace("document.getElementById('tools').hidden=playing", "document.getElementById('tools').hidden=true")
                data = html.encode()
            output.writestr(item.filename, data)
    with zipfile.ZipFile(target) as archive:
        assert {'index.html', 'stage.apk'} <= set(archive.namelist())
        assert not any(name.endswith('.gz') for name in archive.namelist())
    print(target)


if __name__ == '__main__':
    build()
