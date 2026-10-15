"""Level data and broad-phase collision lookup; no display or assets on import."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import json
import math

import pygame

ROOT = Path(__file__).resolve().parent.parent
TILE = 96
STEP = 1 / 60


class SpatialGrid:
    def __init__(self, rects, cell_size=TILE):
        self.cell_size = cell_size
        self.rects = tuple(pygame.Rect(r) for r in rects)
        self.cells = defaultdict(list)
        for index, rect in enumerate(self.rects):
            for cell in self._cells(rect):
                self.cells[cell].append(index)

    def _cells(self, rect):
        size = self.cell_size
        # ceil(right / size) handles negative coordinates and open right edges.
        for x in range(math.floor(rect.left / size), math.ceil(rect.right / size)):
            for y in range(math.floor(rect.top / size), math.ceil(rect.bottom / size)):
                yield x, y

    def query(self, rect):
        found = set()
        for cell in self._cells(rect):
            found.update(self.cells.get(cell, ()))
        return tuple(self.rects[i] for i in sorted(found))


@dataclass
class Commands:
    left: bool = False
    right: bool = False
    jump: bool = False


class World:
    def __init__(self, level_path=None):
        path = level_path or ROOT / 'data' / 'level-1.json'
        self.level = json.loads(Path(path).read_text())
        self.solids = SpatialGrid(self.level['blocks'])
        self.hazards = SpatialGrid(self.level['hazards'])
        self.goal = pygame.Rect(self.level['goal'])
        self.start = self.level['spawn']
        self.checkpoints = [(3792, 336), (3216, -816), (1488, -1488)]
        self.reset()

    def reset(self):
        self.player = pygame.FRect(*self.start, 48, 60)
        self.vx = self.vy = 0.0
        self.jumps = 0
        self.fall_count = 0
        self.grounded = False
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.coins = {i: pygame.Rect(x - 20, y - 20, 40, 40)
                      for i, (x, y) in enumerate(self.level['coins'])}
        self.collected = 0
        self.elapsed = 0.0
        self.deaths = 0
        self.won = False
        self.max_height = self.player.y
        self.collision_candidates = 0
        self.checkpoint = -1

    def respawn(self):
        self.player.topleft = (self.start if self.checkpoint < 0 else
                               (self.checkpoints[self.checkpoint][0] - 24,
                                self.checkpoints[self.checkpoint][1] - 60))
        self.vx = self.vy = 0.0
        self.jumps = self.fall_count = 0
        self.grounded = False
        self.coyote = self.jump_buffer = 0.0
        self.deaths += 1

    def step(self, commands: Commands):
        if self.won:
            return
        self.elapsed += STEP
        self.collision_candidates = 0
        self.coyote = max(0, self.coyote - STEP)
        self.jump_buffer = max(0, self.jump_buffer - STEP)
        if commands.jump:
            self.jump_buffer = 0.12
        if self.jump_buffer and (self.grounded or self.coyote or self.jumps < 2):
            if self.grounded or self.coyote:
                self.jumps = 0
            self.vy = -8.0  # Original double-jump timing, now at a fixed 60 Hz.
            self.jumps += 1
            if self.jumps == 1:
                self.fall_count = 0
            self.grounded = False
            self.coyote = self.jump_buffer = 0.0
        self.vx = 5.0 * (int(commands.right) - int(commands.left))
        self.vy = min(18, self.vy + min(1, self.fall_count / 60))
        self.fall_count += 1

        # Solve axes independently, touching only nearby cells.
        self.player.x += self.vx
        for block in self.solids.query(self.player):
            self.collision_candidates += 1
            if self.player.colliderect(block):
                if self.vx > 0:
                    self.player.right = block.left
                elif self.vx < 0:
                    self.player.left = block.right
        was_grounded = self.grounded
        self.grounded = False
        self.player.y += self.vy
        for block in self.solids.query(self.player):
            self.collision_candidates += 1
            if self.player.colliderect(block):
                if self.vy >= 0:
                    self.player.bottom = block.top
                    self.vy = 0
                    self.grounded = True
                    self.jumps = self.fall_count = 0
                else:
                    self.player.top = block.bottom
                    self.vy = 0
        if not self.grounded and self.vy >= 0:
            probe = self.player.move(0, 1)
            supports = [block for block in self.solids.query(probe) if probe.colliderect(block)]
            if supports:
                self.player.bottom = min(block.top for block in supports)
                self.grounded = True
                self.vy = 0
                self.jumps = self.fall_count = 0
        if self.grounded:
            self.coyote = 0.08
        elif was_grounded:
            self.coyote = 0.08
            # Walking off an edge uses the first jump, not an extra third jump.
            self.jumps = max(1, self.jumps)
        for hazard in self.hazards.query(self.player):
            if self.player.colliderect(hazard):
                self.respawn()
                return
        if self.player.top > 1050:
            self.respawn()
            return
        for index, coin in tuple(self.coins.items()):
            if self.player.colliderect(coin):
                self.coins.pop(index)
                self.collected += 1
        self.max_height = min(self.max_height, self.player.top)
        for i, (x, y) in enumerate(self.checkpoints):
            if i > self.checkpoint and self.grounded and abs(self.player.centerx - x) < 72 and abs(self.player.bottom - y) < 2:
                self.checkpoint = i
        if self.player.colliderect(self.goal):
            self.won = True

    @property
    def progress(self):
        return max(0.0, min(1.0, (self.start[1] - self.max_height) /
                            (self.start[1] - self.goal.bottom)))
