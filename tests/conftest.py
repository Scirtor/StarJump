import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame
import pytest

@pytest.fixture(scope='session', autouse=True)
def pygame_display():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    yield
    pygame.quit()
