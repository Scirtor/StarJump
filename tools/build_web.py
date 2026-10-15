"""Build only the game and its used assets; never bundle legacy code or test files."""
from pathlib import Path
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / 'build' / 'stage'
STAGE.mkdir(parents=True, exist_ok=True)
for name in ('starjump', 'data'):
    shutil.copytree(ROOT / name, STAGE / name, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
shutil.copy2(ROOT / 'main.py', STAGE / 'main.py')
assets = ['FONT-LICENSE.txt', 'Background/Purple.png', 'Background/Background_cosmos.png',
          'Logo/Star_Jump.png', 'Terrain/Terrain1.png', 'ui-font.ttf']
assets += ['MainCharacters/PinkMan/' + n + '.png' for n in
           ('idle', 'run', 'jump', 'double_jump', 'fall', 'hit')]
for name in assets:
    target = STAGE / 'assets' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'assets' / name, target)
subprocess.run([sys.executable, '-m', 'pygbag', '--build', '--archive', '--no_opt',
                '--ume_block', '0', '--title', 'Star Jump', '--app_name', 'starjump',
                '--package', 'com.scirtor.starjump', str(STAGE)], check=True)
print(STAGE / 'build' / 'web')

# Keep Pygbag's compatible Python bootstrap; replace its debug-oriented HTML shell.
import hashlib
import re
import zipfile
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
pygame.init()
pygame.display.set_mode((1, 1))
web = STAGE / 'build' / 'web'
version = hashlib.sha256((web / 'stage.tar.gz').read_bytes() + b''.join(p.read_bytes() for p in sorted((ROOT / 'web').rglob('*')) if p.is_file())).hexdigest()[:12]
original = (web / 'index.html').read_text()
boot = re.search(r'<script[^>]+id="site"[^>]*>(.*?)</script>', original, re.S).group(1)
boot = boot.replace('platform.document.body.style.background = "#7f7f7f"', 'platform.document.body.style.background = "#181125"')
# The game signals readiness after its first rendered menu; no intermediate prompt.
boot = boot.replace('msg  = "Ready to start ! Please click/touch page"', 'msg  = "Нажми на экран, чтобы начать"')
(web / 'index.html').write_text((ROOT / 'web/index.html').read_text().replace('__PYGBAG_BOOT__', boot).replace('__REVISION__', version))
for name in ('boot.js', 'manifest.webmanifest'):
    shutil.copy2(ROOT / 'web' / name, web / name)
shutil.copytree(ROOT / 'web/vendor', web / 'vendor', dirs_exist_ok=True)
icons = web / 'icons'
icons.mkdir(exist_ok=True)
logo = pygame.image.load(str(ROOT / 'assets/Logo/Star_Jump.png')).convert_alpha()
for name, size in [('icon-192.png', 192), ('icon-512.png', 512), ('apple-touch-icon.png', 180)]:
    icon = pygame.Surface((size, size)); icon.fill('#181125')
    # All artwork stays inside the maskable icon safe circle.
    art = pygame.transform.smoothscale(logo, (round(size*.7), round(size*.7)))
    icon.blit(art, art.get_rect(center=icon.get_rect().center))
    pygame.image.save(icon, str(icons / name))

(web / 'sw.js').write_text((ROOT / 'web/sw.js').read_text().replace('__VERSION__', version))
release = ROOT / 'dist'
release.mkdir(exist_ok=True)
with zipfile.ZipFile(release / 'StarJump-web.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(web.rglob('*')):
        if path.is_file() and path.name not in ('favicon.png',):
            archive.write(path, path.relative_to(web))
print('Release:', release / 'StarJump-web.zip')
