"""One input path for keyboard, mouse and independent touchscreen fingers."""
import pygame
from .world import Commands


class Input:
    def __init__(self):
        self.keys = set()
        self.fingers = {}
        self.jump_edge = False
        self.touch_seen = False
        self.buttons = {}

    def clear(self):
        self.keys.clear()
        self.fingers.clear()
        self.jump_edge = False

    def layout(self, width, height):
        size = 108
        margin = 28
        self.buttons = {
            'left': pygame.Rect(margin, height - size - margin, size, size),
            'right': pygame.Rect(margin + size + 20, height - size - margin, size, size),
            'jump': pygame.Rect(width - size - margin, height - size - margin, size, size),
        }

    def action_at(self, pos):
        return next((name for name, rect in self.buttons.items() if rect.collidepoint(pos)), None)

    def finger(self, ident, pos, down=True):
        old = self.fingers.get(ident)
        action = self.action_at(pos) if down else None
        if action == 'jump' and old != 'jump':
            self.jump_edge = True
        if action:
            self.fingers[ident] = action
        else:
            self.fingers.pop(ident, None)

    def commands(self):
        actions = set(self.fingers.values())
        command = Commands(
            left=bool(self.keys & {pygame.K_LEFT, pygame.K_a}) or 'left' in actions,
            right=bool(self.keys & {pygame.K_RIGHT, pygame.K_d}) or 'right' in actions,
            jump=self.jump_edge)
        self.jump_edge = False
        return command
