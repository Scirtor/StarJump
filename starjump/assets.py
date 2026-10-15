"""Decode and scale once; no file access, masks or font creation in the frame loop."""
from functools import lru_cache
import pygame
from .world import ROOT


class Assets:
    def __init__(self):
        self.loads = 0

    @lru_cache(maxsize=32)
    def image(self, name):
        self.loads += 1
        return pygame.image.load(str(ROOT / 'assets' / name)).convert_alpha()

    @lru_cache(maxsize=16)
    def animation(self, name):
        sheet = self.image('MainCharacters/PinkMan/' + name + '.png')
        return tuple(pygame.transform.scale(sheet.subsurface((i, 0, 32, 32)), (64, 64))
                     for i in range(0, sheet.get_width(), 32))

    @lru_cache(maxsize=16)
    def font(self, size):
        return pygame.font.Font(str(ROOT / 'assets' / 'ui-font.ttf'), size)

    @lru_cache(maxsize=256)
    def text(self, text, size=28, color=(240, 238, 255)):
        return self.font(size).render(text, True, color)

    @lru_cache(maxsize=1)
    def tile(self):
        sheet = self.image('Terrain/Terrain1.png')
        # Matches the original terrain crop; shared by every block.
        return pygame.transform.scale(sheet.subsurface((96, 0, 48, 48)), (96, 96))

    @lru_cache(maxsize=4)
    def background(self, width, height):
        result = pygame.Surface((width, height)).convert()
        tile = self.image('Background/Purple.png')
        for x in range(0, width, tile.get_width()):
            for y in range(0, height, tile.get_height()):
                result.blit(tile, (x, y))
        return result
