"""A small versioned save that works locally and in the browser sandbox."""
import json
import math
import sys
from pathlib import Path

KEY = 'starjump.save.v1'


class Storage:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path.home() / '.local/share/starjump/save.json'
        self.data = {}
        try:
            if sys.platform == 'emscripten':
                import platform
                raw = platform.window.localStorage.getItem(KEY)
            else:
                raw = self.path.read_text() if self.path.exists() else None
            value = json.loads(str(raw)) if raw else {}
            self.data = value if isinstance(value, dict) else {}
            best = self.data.get('best_seconds')
            if not isinstance(best, (int, float)) or not math.isfinite(best) or best < 0:
                self.data.pop('best_seconds', None)
        except (OSError, ValueError, TypeError, AttributeError):
            self.data = {}

    def write(self):
        try:
            raw = json.dumps(self.data, ensure_ascii=False)
            if sys.platform == 'emscripten':
                import platform
                platform.window.localStorage.setItem(KEY, raw)
            else:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temp = self.path.with_suffix('.tmp')
                temp.write_text(raw)
                temp.replace(self.path)
            return True
        except (OSError, ValueError, TypeError, AttributeError):
            return False

    def save_world(self, world):
        self.data['run'] = {'checkpoint': world.checkpoint, 'collected_ids': sorted(set(range(len(world.level['coins']))) - set(world.coins)),
                            'elapsed': world.elapsed, 'deaths': world.deaths,
                            'max_height': world.max_height}
        return self.write()

    def restore_world(self, world):
        run = self.data.get('run')
        if not isinstance(run, dict):
            return False
        try:
            checkpoint = int(run.get('checkpoint', -1))
            if checkpoint < -1 or checkpoint >= len(world.checkpoints):
                return False
            elapsed = float(run.get('elapsed', 0))
            height = float(run.get('max_height', world.player.top))
            ids = run.get('collected_ids', [])
            if not math.isfinite(elapsed) or not math.isfinite(height) or not isinstance(ids, list) or len(ids) > len(world.level['coins']):
                return False
            world.checkpoint = checkpoint
            world.respawn()
            world.deaths = max(0, int(run.get('deaths', 0)))
            world.elapsed = max(0, elapsed)
            world.max_height = max(world.goal.top, min(world.start[1], height))
            for index in ids:
                world.coins.pop(int(index), None)
            world.collected = len(world.level['coins']) - len(world.coins)
            return True
        except (ValueError, TypeError, OverflowError):
            world.reset()
            return False

    def finish(self, world):
        old = self.data.get('best_seconds')
        if not isinstance(old, (int, float)) or world.elapsed < old:
            self.data['best_seconds'] = round(world.elapsed, 2)
        self.data.pop('run', None)
        return self.write()
