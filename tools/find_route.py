"""Find a real input-only route through the unchanged level (no teleports)."""
import copy
import heapq
import itertools
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from starjump.world import World, Commands

world = World()
route = []
for _ in range(90):
    world.step(Commands()); route.append([0, False])
queue = []
counter = itertools.count()
heapq.heappush(queue, (world.player.bottom, next(counter), world, route))
seen = set()
best = world.player.bottom
best_route = route
count = 0
while queue and count < 5000:
    _, _, world, route = heapq.heappop(queue)
    key = (round(world.player.centerx / 40), round(world.player.bottom), world.checkpoint)
    if key in seen: continue
    seen.add(key); count += 1
    if world.player.bottom < best:
        best = world.player.bottom; best_route = route
        print('HEIGHT',key,flush=True)
        Path('build/best-route.json').write_text(json.dumps(route,separators=(',',':')))
    if count % 100 == 0: print(count, len(queue), key, flush=True)
    for dx in (-384,-288,-192,-96,0,96,192,288,384):
        for second, turn in itertools.product((-1, 12, 24, 36, 48), (0, 32, 44)):
            child = copy.copy(world); child.player = world.player.copy(); child.coins = world.coins.copy()
            steps = []
            target = world.player.centerx + dx
            for tick in range(140):
                if turn and tick == turn: target = world.player.centerx - dx
                move = 0 if abs(target-child.player.centerx) < 3 else (1 if target > child.player.centerx else -1)
                jump = tick == 0 or tick == second
                child.step(Commands(left=move < 0, right=move > 0, jump=jump))
                steps.append([move,jump])
                if child.won:
                    result = route + steps
                    Path('tests/completion-route.json').write_text(json.dumps(result, separators=(',',':')))
                    print('WON', len(result), 'frames', child.deaths, 'deaths', count, 'nodes', flush=True)
                    sys.exit(0)
                if child.deaths != world.deaths: break
                if tick > 5 and child.grounded:
                    k = (round(child.player.centerx / 40), round(child.player.bottom), child.checkpoint)
                    if k not in seen:
                        heapq.heappush(queue,(child.player.bottom, next(counter),child,route+steps))
                    break
print('NO ROUTE',count,flush=True)
sys.exit(1)
