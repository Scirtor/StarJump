"""Repeatable uncapped desktop/dummy-video comparison, both unprofiled."""
import importlib.util
import json
import os
from pathlib import Path
import statistics
import platform
import sys
import time
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT));os.chdir(ROOT)
import pygame
from starjump.app import Game
from starjump.storage import Storage
from starjump.world import STEP
FRAMES=300
class Finished(Exception): pass
spec=importlib.util.spec_from_file_location('original',ROOT/'legacy/Level_1.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
legacy_frames=0
class UncappedClock:
    def tick(self,*args):
        global legacy_frames
        if legacy_frames >= FRAMES: raise Finished
        legacy_frames+=1
clock=pygame.time.Clock
old_times=[]
for _ in range(3):
    legacy_frames=0
    pygame.time.Clock=UncappedClock
    start=time.perf_counter()
    try:legacy.main(legacy.window)
    except Finished:pass
    old_times.append(time.perf_counter()-start)
pygame.time.Clock=clock
new_times=[]
for _ in range(3):
    start=time.perf_counter()
    game=Game(storage=Storage(ROOT/'build/benchmark-save.json'))
    game.start()
    for _ in range(FRAMES):game.update(STEP);game.render()
    new_times.append(time.perf_counter()-start)
result={'machine':platform.machine(),'system':platform.system(),'python':platform.python_version(),'pygame':pygame.version.ver,'frames':FRAMES,'repeats':3,'environment':'Same process, pygame-ce 2.5.8, SDL dummy video, uncapped, unprofiled. Stationary start scene. Both timings include game/level construction and 300 presented frames. Not mobile FPS.',
'original_seconds':old_times,'new_seconds':new_times,'original_median':statistics.median(old_times),'new_median':statistics.median(new_times),'visible_blocks':game.drawn_blocks,'total_blocks':len(game.world.solids.rects),'image_loads_new':game.assets.loads,'collision_candidates':game.world.collision_candidates}
print(json.dumps(result,indent=2))
(ROOT/'build/benchmark.json').write_text(json.dumps(result,indent=2))
