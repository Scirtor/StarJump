from __future__ import annotations

import asyncio
import math
import sys
import time

import pygame

from .assets import Assets
from .input import Input
from .storage import Storage
from .world import STEP, World

INK = (243, 238, 255)
MUTED = (188, 178, 216)
ACCENT = (191, 160, 255)
GOLD = (255, 210, 102)
PANEL = (27, 23, 48)


def time_label(seconds):
    seconds = int(seconds)
    return f'{seconds // 60:02d}:{seconds % 60:02d}'


class Game:
    def __init__(self, size=(1280, 720), storage=None, touch=False):
        pygame.init()
        pygame.display.set_caption('Star Jump')
        self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.assets = Assets()
        self.world = World()
        self.storage = storage or Storage()
        self.input = Input()
        self.touch = touch or sys.platform == 'emscripten'
        self.state = 'menu'
        self.running = True
        self.accumulator = 0.0
        self.animation = 0.0
        self.direction = 1
        self.camera = pygame.Vector2(0, 0)
        self.ui_buttons = {}
        self.last_checkpoint = -1
        self.last_coins = 0
        self.drawn_blocks = 0
        for name in ('idle', 'run', 'jump', 'double_jump', 'fall', 'hit'):
            self.assets.animation(name)
        self.assets.tile()
        self.menu_background = self.assets.image('Background/Background_cosmos.png')
        self.logo = self.assets.image('Logo/Star_Jump.png')
        self.resize(size)

    def resize(self, size):
        width, height = max(320, size[0]), max(240, size[1])
        # Bounded pixel budget: high-DPI phones never render a 4K framebuffer.
        ratio = width / height
        self.view_size = (1280, max(480, round(1280 / ratio))) if ratio >= 1 else (720, min(2160, round(720 / ratio)))
        self.surface = pygame.Surface(self.view_size).convert()
        self.input.layout(*self.view_size)
        self.touch_layers = {}
        for pressed in (False, True):
            layer = pygame.Surface((108, 108), pygame.SRCALPHA)
            pygame.draw.rect(layer, (162, 119, 239, 170) if pressed else (24, 19, 43, 155), layer.get_rect(), border_radius=24)
            pygame.draw.rect(layer, (216, 197, 250, 200), layer.get_rect(), 3, border_radius=24)
            self.touch_layers[pressed] = layer
        self.background = self.assets.background(*self.view_size)
        self.menu_scaled = pygame.transform.smoothscale(self.menu_background, self.view_size)
        logo_size = min(250, max(110, round(self.view_size[1] * .26)))
        self.logo_scaled = pygame.transform.smoothscale(self.logo, (logo_size, logo_size))
        self.overlay = pygame.Surface(self.view_size, pygame.SRCALPHA)
        self.overlay.fill((9, 7, 20, 185))
        self.output = pygame.Surface((width, height)).convert()
        self.input.clear()

    def start(self, resume=False):
        self.world.reset()
        if resume:
            self.storage.restore_world(self.world)
        else:
            self.storage.data.pop('run', None)
            self.storage.write()
        self.last_checkpoint = self.world.checkpoint
        self.last_coins = self.world.collected
        self.state = 'playing'
        self.accumulator = 0
        self.input.clear()
        self.camera.update(self.world.player.centerx - self.view_size[0] * 0.35,
                           self.world.player.centery - self.view_size[1] * 0.58)

    def pause(self):
        if self.state == 'playing':
            self.state = 'paused'
            self.storage.save_world(self.world)
        self.input.clear()
        self.accumulator = 0

    def resume(self):
        self.state = 'playing'
        self.accumulator = 0
        self.input.clear()

    def activate(self, action):
        if action == 'new':
            self.start()
        elif action == 'continue':
            self.start(resume=True)
        elif action == 'resume':
            self.resume()
        elif action == 'pause':
            self.pause()
        elif action == 'menu':
            if self.state != 'won':
                self.storage.save_world(self.world)
            self.state = 'menu'
            self.input.clear()
            self.accumulator = 0
        elif action == 'help':
            self.state = 'help'
        elif action == 'back':
            self.state = 'menu'

    def ui_at(self, pos):
        return next((action for action, rect in self.ui_buttons.items() if rect.collidepoint(pos)), None)

    def event(self, event):
        width, height = self.view_size
        if event.type == pygame.QUIT:
            if self.state in ('playing', 'paused'):
                self.storage.save_world(self.world)
            self.running = False
        elif event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMINIMIZED, pygame.WINDOWHIDDEN):
            self.pause()
        elif event.type == pygame.VIDEORESIZE:
            self.pause()
            self.window = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            self.resize(event.size)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.resume() if self.state == 'paused' else self.pause()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.state == 'menu':
                self.start(resume=bool(self.storage.data.get('run')))
            elif self.state == 'playing':
                if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w) and event.key not in self.input.keys:
                    self.input.jump_edge = True
                self.input.keys.add(event.key)
        elif event.type == pygame.KEYUP:
            self.input.keys.discard(event.key)
        elif event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            self.touch = True
            pos = (event.x * width, event.y * height)
            if event.type == pygame.FINGERDOWN:
                action = self.ui_at(pos)
                if action:
                    self.activate(action)
                    return
            if self.state == 'playing':
                self.input.finger(event.finger_id, pos, event.type != pygame.FINGERUP)
            else:
                self.input.clear()
        elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            # SDL also produces mouse events for touch; handling both doubles jumps.
            if getattr(event, 'touch', False):
                return
            ww, wh = self.window.get_size()
            pos = (event.pos[0] * width / ww, event.pos[1] * height / wh)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = self.ui_at(pos)
                if action:
                    self.activate(action)
                elif self.state == 'playing':
                    self.input.finger('mouse', pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.input.finger('mouse', pos, False)
            elif event.type == pygame.MOUSEMOTION and self.input.fingers.get('mouse'):
                self.input.finger('mouse', pos)

    def update(self, delta):
        if self.state != 'playing':
            self.accumulator = 0
            return
        # Bound catch-up after a slow frame; the game never fast-forwards after sleep.
        self.accumulator += min(delta, 0.1)
        for _ in range(6):
            if self.accumulator + 1e-10 < STEP:
                break
            command = self.input.commands()
            self.world.step(command)
            if command.left != command.right:
                self.direction = -1 if command.left else 1
            self.accumulator -= STEP
            self.animation += STEP
            if self.world.won:
                self.state = 'won'
                self.storage.finish(self.world)
                self.input.clear()
                self.accumulator = 0
                break
        if (self.world.checkpoint != self.last_checkpoint or self.world.collected != self.last_coins):
            self.last_checkpoint = self.world.checkpoint
            self.last_coins = self.world.collected
            self.storage.save_world(self.world)
        target = pygame.Vector2(self.world.player.centerx - self.view_size[0] * .35,
                                self.world.player.centery - self.view_size[1] * .58)
        if (target - self.camera).length_squared() > 1000 ** 2:
            self.camera = target
        else:
            self.camera += (target - self.camera) * (1 - math.exp(-10 * min(delta, .1)))
        self.camera.x = max(-192, min(4128 - self.view_size[0], self.camera.x))
        self.camera.y = min(816 - self.view_size[1], self.camera.y)

    def label(self, text, pos, size=28, color=INK, center=False):
        image = self.assets.text(text, size, color)
        rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
        self.surface.blit(image, rect)

    def button(self, action, text, rect, primary=False):
        self.ui_buttons[action] = rect
        pygame.draw.rect(self.surface, (119, 81, 190) if primary else PANEL, rect, border_radius=16)
        pygame.draw.rect(self.surface, ACCENT if primary else (76, 63, 103), rect, 2, border_radius=16)
        self.label(text, rect.center, 28, center=True)

    def draw_world(self):
        width, height = self.view_size
        sx, sy = round(self.camera.x), round(self.camera.y)
        view = pygame.Rect(sx, sy, width, height)
        self.surface.blit(self.background, (0, 0))
        blocks = self.world.solids.query(view)
        self.drawn_blocks = 0
        tile = self.assets.tile()
        for block in blocks:
            if view.colliderect(block):
                self.surface.blit(tile, (block.x - sx, block.y - sy))
                self.drawn_blocks += 1
        for hazard in self.world.hazards.query(view):
            r = hazard.move(-sx, -sy)
            pygame.draw.rect(self.surface, (240, 80, 85), r, border_radius=4)
            for x in range(r.left, r.right, 16):
                pygame.draw.polygon(self.surface, (255, 202, 98), [(x, r.bottom), (x + 8, r.top - 8), (x + 16, r.bottom)])
        for coin in self.world.coins.values():
            if view.colliderect(coin):
                center = (coin.centerx - sx, coin.centery - sy)
                pygame.draw.circle(self.surface, GOLD, center, 19)
                pygame.draw.circle(self.surface, (175, 106, 38), center, 14, 3)
        for i, (x, y) in enumerate(self.world.checkpoints):
            if view.inflate(100, 100).collidepoint(x, y):
                color = (137, 235, 183) if i <= self.world.checkpoint else ACCENT
                pygame.draw.line(self.surface, INK, (x - sx, y - sy), (x - sx, y - sy - 82), 4)
                pygame.draw.polygon(self.surface, color, [(x - sx, y - sy - 82), (x - sx + 38, y - sy - 66), (x - sx, y - sy - 50)])
        goal = self.world.goal.move(-sx, -sy)
        if view.colliderect(self.world.goal):
            center = goal.center
            pts = [(center[0] + math.cos(-math.pi / 2 + i * math.pi / 5) * (40 if i % 2 == 0 else 18),
                    center[1] + math.sin(-math.pi / 2 + i * math.pi / 5) * (40 if i % 2 == 0 else 18)) for i in range(10)]
            pygame.draw.polygon(self.surface, GOLD, pts)
        p = self.world.player
        name = 'idle'
        if self.world.vy < 0:
            name = 'double_jump' if self.world.jumps == 2 else 'jump'
        elif self.world.vy > 2:
            name = 'fall'
        elif self.world.vx:
            name = 'run'
        frames = self.assets.animation(name)
        image = frames[int(self.animation * 20) % len(frames)]
        if self.direction < 0:
            image = self.flipped(name, int(self.animation * 20) % len(frames))
        self.surface.blit(image, (round(p.centerx - 32 - sx), round(p.bottom - 64 - sy)))

    def flipped(self, name, index):
        # Cache flipped frames separately, once per animation frame.
        if not hasattr(self, '_flipped'):
            self._flipped = {}
        key = (name, index)
        if key not in self._flipped:
            self._flipped[key] = pygame.transform.flip(self.assets.animation(name)[index], True, False)
        return self._flipped[key]

    def hud(self):
        w, h = self.view_size
        pygame.draw.rect(self.surface, PANEL, (16, 16, w - 32, 74), border_radius=16)
        self.label(f'Монеты {self.world.collected}/{len(self.world.level["coins"])}', (34, 29), 25, GOLD)
        self.label(time_label(self.world.elapsed), (w - 210, 29), 25)
        self.button('pause', 'II', pygame.Rect(w - 88, 26, 54, 52))
        bw = max(130, min(340, w - 530))
        bx = (w - bw) // 2
        pygame.draw.rect(self.surface, (62, 51, 85), (bx, 40, bw, 12), border_radius=6)
        pygame.draw.rect(self.surface, ACCENT, (bx, 40, max(0, round(bw * self.world.progress)), 12), border_radius=6)
        if self.touch:
            actions = set(self.input.fingers.values())
            for name, rect in self.input.buttons.items():
                self.surface.blit(self.touch_layers[name in actions], rect)
            for name, rect in self.input.buttons.items():
                self.label({'left': '←', 'right': '→', 'jump': '↑'}[name], rect.center, 54, center=True)

    def render(self, present=True):
        self.ui_buttons = {}
        w, h = self.view_size
        if self.state in ('playing', 'paused', 'won'):
            self.draw_world()
            self.hud()
            if self.state != 'playing':
                self.surface.blit(self.overlay, (0, 0))
                self.ui_buttons = {}
                self.label('Пауза' if self.state == 'paused' else 'Звезда твоя!', (w // 2, h // 2 - 150), 52, center=True)
                if self.state == 'won':
                    self.label(f'{time_label(self.world.elapsed)}  ·  Монеты {self.world.collected}/6  ·  Падения {self.world.deaths}', (w // 2, h // 2 - 75), 25, center=True)
                self.button('resume' if self.state == 'paused' else 'new', 'Продолжить' if self.state == 'paused' else 'Ещё раз', pygame.Rect(w // 2 - 170, h // 2, 340, 64), True)
                self.button('menu', 'В меню', pygame.Rect(w // 2 - 170, h // 2 + 86, 340, 64))
        else:
            self.surface.blit(self.menu_scaled, (0, 0))
            self.surface.blit(self.overlay, (0, 0))
            if self.state == 'help':
                gap = min(44, max(30, round(h * .065)))
                top = max(28, (h - (96 + 7 * gap + 80)) // 2)
                self.label('Как играть', (w // 2, top), 44, center=True)
                lines = ['Доберись до звезды наверху лунной башни.', '← → или A / D — движение.', 'Пробел, W или ↑ — прыжок.', 'В воздухе можно прыгнуть ещё раз.', 'На телефоне удерживай стрелку и жми прыжок.', 'Флажки сохраняют точку возвращения.', 'Ловушки и падение вернут к последнему флажку.']
                for i, line in enumerate(lines):
                    self.label(line, (w // 2, top + 70 + i * gap), 23, center=True)
                self.button('back', 'Назад', pygame.Rect(w // 2 - 170, top + 90 + 7 * gap, 340, 64), True)
            else:
                has_run = isinstance(self.storage.data.get('run'), dict)
                logo_size = self.logo_scaled.get_width()
                title_height = 70 if h >= 660 else 0
                count = 3 if has_run else 2
                content_height = logo_size + title_height + 48 + count * 64 + (count - 1) * 16
                top = max(10, (h - 60 - content_height) // 2)
                self.surface.blit(self.logo_scaled, (w // 2 - logo_size // 2, top))
                if title_height:
                    self.label('STAR JUMP', (w // 2, top + logo_size + 32), 52, center=True)
                self.label('Лунная башня ждёт своего героя', (w // 2, top + logo_size + title_height + 16), 25, MUTED, True)
                first = top + logo_size + title_height + 48
                self.button('continue' if has_run else 'new', 'Продолжить' if has_run else 'Играть', pygame.Rect(w // 2 - 170, first, 340, 64), True)
                if has_run:
                    self.button('new', 'Новая игра', pygame.Rect(w // 2 - 170, first + 80, 340, 64))
                self.button('help', 'Как играть', pygame.Rect(w // 2 - 170, first + (160 if has_run else 80), 340, 64))
                best = self.storage.data.get('best_seconds')
                footer = 'Nurzhan Bekmurat · Scirtor'
                if isinstance(best, (int, float)):
                    footer = 'Лучшее: ' + time_label(best) + '  ·  ' + footer
                self.label(footer, (w // 2, h - 26), 20, MUTED, True)
        if present:
            pygame.transform.scale(self.surface, self.window.get_size(), self.output)
            self.window.blit(self.output, (0, 0))
            pygame.display.flip()
        return self.surface


async def main():
    size = (1280, 720)
    if sys.platform == 'emscripten':
        import platform
        stage = platform.document.getElementById('game-stage')
        size = (int(stage.clientWidth), int(stage.clientHeight))
    game = Game(size)
    clock = pygame.time.Clock()
    last = time.perf_counter()
    previous_state = None
    while game.running:
        if sys.platform != 'emscripten':
            clock.tick(60 if game.state == 'playing' else 30)
        now = time.perf_counter()
        dt, last = now - last, now
        if sys.platform == 'emscripten':
            size = (int(stage.clientWidth), int(stage.clientHeight))
            if size != game.window.get_size() and min(size) > 0:
                game.event(pygame.event.Event(pygame.VIDEORESIZE, size=size))
            if platform.window.starjumpPauseRequested:
                game.pause()
                platform.window.starjumpPauseRequested = False
            if platform.document.hidden:
                game.pause()
                await asyncio.sleep(.2)
                last = time.perf_counter()
                continue
            if game.state != previous_state:
                platform.window.starjumpSetPlaying(game.state == 'playing')
                previous_state = game.state
        for event in pygame.event.get():
            game.event(event)
        game.update(dt)
        game.render()
        if sys.platform == 'emscripten' and not getattr(game, '_web_ready', False):
            platform.window.starjumpReady()
            game._web_ready = True
        await asyncio.sleep(1 / 30 if sys.platform == 'emscripten' and game.state != 'playing' else 0)
    pygame.quit()
