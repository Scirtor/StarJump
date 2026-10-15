import pygame
import sys
from os import listdir
from os.path import isfile, join
pygame.init()

pygame.display.set_caption("Звездный прыжок")

WIDTH, HEIGHT = 1280, 720
FPS = 60
PLAYER_VEL = 5

WHITE = (255, 255, 255)  # Белый цвет
BLACK = (0, 0, 0)        # Черный цвет
RED = (255, 0, 0)        # Красный цвет
GREEN = (0, 255, 0)      # Зеленый цвет
BLUE = (0, 0, 255)       # Синий цвет

window = pygame.display.set_mode((WIDTH, HEIGHT))

# Шрифты
FONT = pygame.font.SysFont("arialblack", 50)

# Переменные для меню паузы
pause = False
pause_text = FONT.render("Пауза", True, WHITE)
pause_rect = pause_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))

def flip(sprites):
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def load_sprite_sheets(dir1, dir2, width, height, direction=False):
    path = join("assets", dir1, dir2)
    images = [f for f in listdir(path) if isfile(join(path, f))]

    all_sprites = {}

    for image in images:
        sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()

        sprites = []
        for i in range(sprite_sheet.get_width() // width):
            surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
            rect = pygame.Rect(i * width, 0, width, height)
            surface.blit(sprite_sheet, (0, 0), rect)
            sprites.append(pygame.transform.scale2x(surface))

        if direction:
            all_sprites[image.replace(".png", "") + "_right"] = sprites
            all_sprites[image.replace(".png", "") + "_left"] = flip(sprites)
        else:
            all_sprites[image.replace(".png", "")] = sprites

    return all_sprites


def get_block(size):
    path = join("assets", "Terrain", "Terrain1.png")
    image = pygame.image.load(path).convert_alpha()
    surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    rect = pygame.Rect(96, 0, size, size)
    surface.blit(image, (0, 0), rect)
    return pygame.transform.scale2x(surface)


class Player(pygame.sprite.Sprite):
    COLOR = (255, 0, 0)
    GRAVITY = 1
    SPRITES = load_sprite_sheets("MainCharacters", "PinkMan", 32, 32, True)
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height):
        super().__init__()
        self.progress = 0  # Добавляем атрибут progress
        self.rect = pygame.Rect(x, y, width, height)
        self.x_vel = 0
        self.y_vel = 0
        self.mask = None
        self.direction = "left"
        self.animation_count = 0
        self.fall_count = 0
        self.jump_count = 0
        self.hit = False
        self.hit_count = 0
        self.dead = False  # Добавляем атрибут для отслеживания смерти
        self.coins_collected = 0  # Инициализация счетчика монет

    def jump(self):
        self.y_vel = -self.GRAVITY * 8
        self.animation_count = 0
        self.jump_count += 1
        if self.jump_count == 1:
            self.fall_count = 0

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def make_hit(self):
        self.hit = True
        

    def move_left(self, vel):
        self.x_vel = -vel
        if self.direction != "left":
            self.direction = "left"
            self.animation_count = 0

    def move_right(self, vel):
        self.x_vel = vel
        if self.direction != "right":
            self.direction = "right"
            self.animation_count = 0

    def loop(self, fps):
        self.y_vel += min(1, (self.fall_count / fps) * self.GRAVITY)
        self.move(self.x_vel, self.y_vel)

        if self.hit:
            self.hit_count += 1
        if self.hit_count > fps * 2:
            self.hit = False
            self.hit_count = 0

        self.fall_count += 1
        self.update_sprite()

    def landed(self):
        self.fall_count = 0
        self.y_vel = 0
        self.jump_count = 0

    def hit_head(self):
        self.count = 0
        self.y_vel *= -1

    def die(self):
        self.dead = True
        self.x_vel = 0
        self.y_vel = 0

    
    def update(self):
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)
        # Предполагаем, что fire2 - это список объектов Fire
        player_collided_with_fire = False

        



    def update_sprite(self):
        sprite_sheet = "idle"
        if self.hit:
            sprite_sheet = "hit"
        elif self.y_vel < 0:
            if self.jump_count == 1:
                sprite_sheet = "jump"
            elif self.jump_count == 2:
                sprite_sheet = "double_jump"
        elif self.y_vel > self.GRAVITY * 2:
            sprite_sheet = "fall"
        elif self.x_vel != 0:
            sprite_sheet = "run"

        sprite_sheet_name = sprite_sheet + "_" + self.direction
        sprites = self.SPRITES[sprite_sheet_name]
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.sprite = sprites[sprite_index]
        self.animation_count += 1
        self.update()


    def draw(self, win, offset_x, offset_y):
        win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y - offset_y))

    def collide_with_coins(self, all_coins):
        coins_to_check = all_coins[:]  # Создаем копию списка монет
        for coin in coins_to_check:
            if pygame.sprite.collide_mask(self, coin):
                all_coins.remove(coin)  # Удаляем монетку при столкновении
                self.coins_collected += 1  # Увеличиваем счетчик монет


class Object(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, name=None):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.width = width
        self.height = height
        self.name = name

    def draw(self, win, offset_x, offset_y):
        win.blit(self.image, (self.rect.x - offset_x, self.rect.y - offset_y))


class Block(Object):
    def __init__(self, x, y, size):
        super().__init__(x, y, size, size)
        block = get_block(size)
        self.image.blit(block, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)


class Fire(Object):
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, "fire")
        self.fire = load_sprite_sheets("Traps", "Platforms", width, height)
        self.image = self.fire["Brown Off"][0]
        self.mask = pygame.mask.from_surface(self.image)
        self.animation_count = 0
        self.animation_name = "off"

    def on(self):
        self.animation_name = "on"

    def off(self):
        self.animation_name = "off"

    def loop(self):
        sprites = self.fire[self.animation_name]
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.image = sprites[sprite_index]
        self.animation_count += 1

        self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.image)

        if self.animation_count // self.ANIMATION_DELAY > len(sprites):
            self.animation_count = 0


# Класс для стрелки
class Arrow(Object):
    def __init__(self, x, y, size):
        super().__init__(x, y, size, size)
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        # Определение точек для стрелки, направленной влево
        points = [(size, 0), (0, size // 2), (size, size)]
        # Рисование стрелки белым цветом
        pygame.draw.polygon(self.image, WHITE, points)
        self.mask = pygame.mask.from_surface(self.image)

# Функция для отрисовки стрелки
    def draw_arrow(window, arrow, offset_x, offset_y):
        arrow.draw(window, offset_x, offset_y)

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y, radius):
        super().__init__()
        self.image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        pygame.draw.circle(self.image, (255, 215, 0), (radius, radius), radius)
        pygame.draw.circle(self.image, (255, 140, 0), (radius, radius), radius, 3)
        self.mask = pygame.mask.from_surface(self.image)

    def draw(self, win, offset_x, offset_y):
        win.blit(self.image, (self.rect.x - offset_x, self.rect.y - offset_y))

    def collide(self, all_coins, offset_x, offset_y):
        for coin in all_coins[:]:  # Используем срез списка для безопасного удаления во время итерации
            if pygame.sprite.collide_mask(self, coin):
                all_coins.remove(coin)  # Удаляем монетку при столкновении
                self.coins_collected += 1  # Увеличиваем счетчик монет
        

def get_background(name):
    image = pygame.image.load(join("assets", "Background", name))
    _, _, width, height = image.get_rect()
    tiles = []

    for i in range(WIDTH // width + 1):
        for j in range(HEIGHT // height + 1):
            pos = (i * width, j * height)
            tiles.append(pos)

    return tiles, image

def create_coins_above_platform(platform_blocks, coin_radius, coins_spacing, coins_per_block):
    coins = []
    for block in platform_blocks:
        # Создаем временный прямоугольник для проверки пересечения с другими блоками
        temp_rect = pygame.Rect(block.rect.centerx - coin_radius, block.rect.top - coin_radius - coins_spacing, coin_radius * 2, coin_radius * 2)
        # Проверяем, не пересекается ли временный прямоугольник с другими блоками
        collision = any(temp_rect.colliderect(other_block.rect) for other_block in platform_blocks if other_block is not block)
        # Если нет пересечения, создаем монеты
        if not collision:
            for i in range(coins_per_block):
                coin_x = block.rect.centerx
                coin_y = block.rect.top - coin_radius - coins_spacing - (coin_radius * 2 + coins_spacing) * i
                coins.append(Coin(coin_x, coin_y, coin_radius))
    return coins


# Обновление функции отрисовки для включения стрелки
def draw(window, background, bg_image, player, objects, offset_x, offset_y):
    for tile in background:
        window.blit(bg_image, tile)

    for obj in objects:
        obj.draw(window, offset_x, offset_y)

    player.draw(window, offset_x, offset_y)




def handle_vertical_collision(player, objects, dy):
    collided_objects = []
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            if dy > 0:
                player.rect.bottom = obj.rect.top
                player.landed()
            elif dy < 0:
                player.rect.top = obj.rect.bottom
                player.hit_head()

            collided_objects.append(obj)

    return collided_objects

def draw_text (text, text_font, text_color, x_text, y_text):
    img = FONT.render(text, True, text_color)
    window.blit(img, (x_text, y_text))

def collide(player, objects, dx):
    player.move(dx, 0)
    player.update()
    collided_object = None
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            collided_object = obj
            break

    player.move(-dx, 0)
    player.update()
    return collided_object



def handle_move(player, objects):
    keys = pygame.key.get_pressed()

    player.x_vel = 0
    collide_left = collide(player, objects, -PLAYER_VEL * 2)
    collide_right = collide(player, objects, PLAYER_VEL * 2)

    if keys[pygame.K_LEFT] and not collide_left:
        player.move_left(PLAYER_VEL)
    if keys[pygame.K_RIGHT] and not collide_right:
        player.move_right(PLAYER_VEL)
    if keys[pygame.K_a] and not collide_left:
        player.move_left(PLAYER_VEL)
    if keys[pygame.K_d] and not collide_right:
        player.move_right(PLAYER_VEL)
        

    

    vertical_collide = handle_vertical_collision(player, objects, player.y_vel)
    to_check = [collide_left, collide_right, *vertical_collide]
    for obj in to_check:
        if obj and obj.name == "fire":
            player.make_hit()

def draw_level_progress_bar(window, offset_y, max_offset_y):
    # Устанавливаем начальные и конечные значения для offset_y
    start_offset_y = 30
    end_offset_y = max_offset_y  # -2150 для вашего случая

    # Рассчитываем процент прохождения уровня
    progress_percentage = abs((offset_y - start_offset_y) / (end_offset_y - start_offset_y))

    # Устанавливаем размеры и позицию прогресс бара
    bar_width = 300
    bar_height = 30
    bar_x = (window.get_width() - bar_width) // 2  # Центрируем прогресс бар
    bar_y = 25  # Отступ сверху

    # Рисуем фон прогресс бара
    pygame.draw.rect(window, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height))

    # Рисуем заполнение прогресс бара в зависимости от процента прохождения
    pygame.draw.rect(window, (0, 255, 0), (bar_x, bar_y, bar_width * progress_percentage, bar_height))

    # Обновляем экран
    pygame.display.flip()




# Функция для создания эффекта размытия на поверхности
def blur_surf(surface, amt):
    if amt < 1.0:
        raise ValueError("amt must be greater than 1.0")
    scale = 1.0/float(amt)
    surf_size = surface.get_size()
    scale_size = (int(surf_size[0]*scale), int(surf_size[1]*scale))
    surf = pygame.transform.smoothscale(surface, scale_size)
    surf = pygame.transform.smoothscale(surf, surf_size)
    return surf

# Функция для создания эффекта размытия на поверхности
def blur_surface(surface, amt):
    if amt < 1.0:
        raise ValueError("amt must be greater than 1.0")
    scale = 1.0 / float(amt)
    surf_size = surface.get_size()
    scale_size = (int(surf_size[0] * scale), int(surf_size[1] * scale))
    surf = pygame.transform.smoothscale(surface, scale_size)
    surf = pygame.transform.smoothscale(surf, surf_size)
    return surf

def draw_text_centered(surface, text, font, color, button_rect):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=button_rect.center)
    surface.blit(text_surface, text_rect)

# Функция для отрисовки счетчика монет
def draw_coin_counter(window, coins_collected, font, color, x, y):
    text = f"Монеты: {coins_collected}"
    text_surface = font.render(text, True, color)
    window.blit(text_surface, (x, y))

def show_pause_menu(window, pause_text, pause_rect, continue_button, exit_button, font):
    # Создаем поверхность для размытия
    blurred_surf = blur_surface(window, 2)
    window.blit(blurred_surf, (0, 0))
    window.blit(pause_text, pause_rect)

    # Отрисовка кнопок
    pygame.draw.rect(window, (123, 123, 123), continue_button)  # Зеленая кнопка "Продолжить"
    pygame.draw.rect(window, (123, 123, 123), exit_button)     # Красная кнопка "Выход"

    # Центрирование текста на кнопках
    draw_text_centered(window, "Продолжить", font, WHITE, continue_button)
    draw_text_centered(window, "Выход", font, WHITE, exit_button)
    pygame.display.update()

    


def restart_level():
    # Создание нового экземпляра игрока
    player = Player(100, 500, 50, 50)
    player.make_hit
    return player

def main(window):
    clock = pygame.time.Clock()
    background, bg_image = get_background("Purple.png")

    block_size = 96

    arrow_size = 50  # Размер стрелки
    platform16_arrow = Arrow(block_size * 16, HEIGHT - block_size * 25+10 - arrow_size, arrow_size)
    platform16_arrow_2 = Arrow(block_size * 16+15, HEIGHT - block_size * 25+10 - arrow_size, arrow_size)


    player = Player(100, 500, 50, 50)
    fire2 = [Fire(i * block_size + 15, HEIGHT - 2 * block_size - block_size * j, 32, 8)
                 for i in range(block_size * 12 // block_size, block_size * 14 // block_size)
                 for j in range(-block_size * 2 // block_size, -block_size //  block_size)]
    fire3 = [Fire(i * block_size + 15, HEIGHT - 2 * block_size - block_size * j + 20, 32, 8)
                 for i in range(block_size * 18 // block_size, block_size * 20 // block_size)
                 for j in range(block_size * 21 // block_size, block_size * 22 //  block_size)]
    floor = [Block(i * block_size, HEIGHT - 2 * block_size - block_size * j, block_size)
             for i in range(0 // block_size, block_size * 8 // block_size)
             for j in range(-block_size * 2 // block_size, 0 //  block_size)]
    floor2 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 14 // block_size, block_size * 20 // block_size)
             for j in range(block_size * 2 // block_size, block_size * 3 //  block_size)]
    floor3 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 14 // block_size, block_size * 41 // block_size)
             for j in range(0 // block_size, block_size * 2 //  block_size)]
    floor4 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 22 // block_size, block_size * 32 // block_size)
             for j in range(block_size * 2 // block_size, block_size * 4 //  block_size)]
    floor5 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 8 // block_size, block_size * 12 // block_size)
             for j in range(0 // block_size, block_size * 3 //  block_size)]
    floor6 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 37 // block_size, block_size * 41 // block_size)
             for j in range(block_size * 2 // block_size, block_size * 4 //  block_size)]
    floor7 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 39 // block_size, block_size * 41 // block_size)
             for j in range(block_size * 4 // block_size, block_size * 5 //  block_size)]
    platform1 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 33 // block_size, block_size * 37 // block_size)
             for j in range(block_size * 6 // block_size, block_size * 7 //  block_size)]
    platform2 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 27 // block_size, block_size * 31 // block_size)
             for j in range(block_size * 6 // block_size, block_size * 7 //  block_size)]
    platform3 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 23 // block_size, block_size * 27 // block_size)
             for j in range(block_size * 7 // block_size, block_size * 8 //  block_size)]
    col1 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 21 // block_size, block_size * 22 // block_size)
             for j in range(block_size * 8 // block_size, block_size * 10 //  block_size)]
    col2 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 20 // block_size, block_size * 21 // block_size)
             for j in range(block_size * 10 // block_size, block_size * 14 //  block_size)]
    roof = [Block(i * block_size, HEIGHT - 2 * block_size - block_size * j, block_size)
             for i in range(block_size * 3 // block_size, block_size * 41 // block_size)
             for j in range(block_size * 25 // block_size, block_size * 26 //  block_size)]
    platform4 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 21 // block_size, block_size * 23 // block_size)
             for j in range(block_size * 13 // block_size, block_size * 14 //  block_size)]
    platform5 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 28 // block_size, block_size * 32 // block_size)
             for j in range(block_size * 11 // block_size, block_size * 12 //  block_size)]
    platform6 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 23 // block_size, block_size * 26 // block_size)
             for j in range(block_size * 10 // block_size, block_size * 11 //  block_size)]
    platform7 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 31 // block_size, block_size * 35 // block_size)
             for j in range(block_size * 13 // block_size, block_size * 14 //  block_size)]
    platform8 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 36 // block_size, block_size * 39 // block_size)
             for j in range(block_size * 14 // block_size, block_size * 15 //  block_size)]
    col3 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 38 // block_size, block_size * 39 // block_size)
             for j in range(block_size * 15 // block_size, block_size * 18 //  block_size)]
    col4 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 37 // block_size, block_size * 38 // block_size)
             for j in range(block_size * 17 // block_size, block_size * 20 //  block_size)]
    platform10 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 29 // block_size, block_size * 35 // block_size)
             for j in range(block_size * 16 // block_size, block_size * 17 //  block_size)]
    platform11 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 21 // block_size, block_size * 27 // block_size)
             for j in range(block_size * 17 // block_size, block_size * 18 //  block_size)]
    col5 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 21 // block_size, block_size * 22 // block_size)
             for j in range(block_size * 18 // block_size, block_size * 20 //  block_size)]
    col6 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 20 // block_size, block_size * 21 // block_size)
             for j in range(block_size * 20 // block_size, block_size * 23 //  block_size)]
    platform14 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 20 // block_size, block_size * 26 // block_size)
             for j in range(block_size * 23 // block_size, block_size * 24 //  block_size)]
    platform12 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 24 // block_size, block_size * 28 // block_size)
             for j in range(block_size * 20 // block_size, block_size * 21 //  block_size)]
    platform13 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 28 // block_size, block_size * 31 // block_size)
             for j in range(block_size * 21 // block_size, block_size * 22 //  block_size)]
    platform15 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 18 // block_size, block_size * 20 // block_size)
             for j in range(block_size * 22 // block_size, block_size * 23 //  block_size)]
    platform16 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 15 // block_size, block_size * 18 // block_size)
             for j in range(block_size * 23 // block_size, block_size * 24 //  block_size)]
    platform17 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 9 // block_size, block_size * 12 // block_size)
             for j in range(block_size * 23 // block_size, block_size * 24 //  block_size)]
    platform18 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 5 // block_size, block_size * 7 // block_size)
             for j in range(block_size * 23 // block_size, block_size * 24 //  block_size)]
    platform19 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 2 // block_size, block_size * 5 // block_size)
             for j in range(block_size * 24 // block_size, block_size * 25 //  block_size)]
    col7 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(0 // block_size, block_size // block_size)
             for j in range(block_size * 24 // block_size, block_size * 30 //  block_size)]
    col10 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(block_size * 41 // block_size, block_size * 43 // block_size)
             for j in range(block_size // block_size, block_size * 28 //  block_size)]
    col9 = [Block(i * block_size, HEIGHT - block_size * j, block_size)
             for i in range(-block_size * 2 // block_size, 0 // block_size)
             for j in range(0 // block_size, block_size * 30 //  block_size)]
    objects = [*floor, *floor2, *floor3, *floor4, *floor5, *floor6, *floor7, *platform1, *platform2, *platform3, *platform4, *platform5, 
               *platform6, *platform7, *platform8, *platform10, *platform11, *platform14, *platform12, *platform13, *platform15, *platform16,
               *platform17, *platform18, *platform19, *fire3, platform16_arrow, platform16_arrow_2, 
               *col1, *col2, *col3, *col4, *col5, *col6, *col7, *col9, *col10, *fire2, *roof, 
               Block(block_size * 31, HEIGHT - block_size * 12, block_size),
               Block(block_size * 2, HEIGHT - block_size * 26, block_size),
               Block(block_size, HEIGHT - block_size * 29, block_size)]

    offset_x = 0
    offset_y = 0
    scroll_area_width = 200
    scroll_area_height = 250

    run = True
    pause = False

    pause_text = FONT.render("ПАУЗА", True, WHITE)
    pause_rect = pause_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))

    # Создаем монетки
    coin_radius = 20  # Радиус монетки
    coins_spacing = 5  # Расстояние между монеткой и блоком
    coins_per_block = 1
    # Пример платформ, где нужно добавить монеты
    additional_platforms = [floor2]

# Создаем монеты для каждой платформы и объединяем их в один список
    all_coins = []
    for platform in additional_platforms:
        platform_coins = create_coins_above_platform(platform, coin_radius, coins_spacing, coins_per_block)
        all_coins.extend(platform_coins)
    

    while run:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break
            
            # В основном цикле игры
            continue_button = pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2, 400, 100)
            exit_button = pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2 + 150, 400, 100)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and player.jump_count < 2:
                    player.jump()
                if event.key == pygame.K_ESCAPE:
                    pause = not pause
                    if pause == True:
                        show_pause_menu(window, pause_text, pause_rect, continue_button, exit_button, FONT)
                        # В цикле обработки событий
                    

        if pause:
            if event.type == pygame.MOUSEBUTTONDOWN:
                        if continue_button.collidepoint(event.pos):
                        # Код для продолжения игры
                            pause = False
                        elif exit_button.collidepoint(event.pos):
                        # Код для выхода из игры
                            pygame.quit()
                            sys.exit()
            continue  # Пропускаем остальную часть цикла, если игра на паузе

        else:
            clock.tick(FPS)
            player.loop(FPS)
            handle_move(player, objects)
            draw(window, background, bg_image, player, objects, offset_x, offset_y)

            for coin in all_coins:
                coin.draw(window, offset_x, offset_y)
            

            # Проверяем столкновение игрока с монетками
            player.collide_with_coins(all_coins)

            # Отрисовываем счетчик монет
            draw_coin_counter(window, player.coins_collected, FONT, WHITE, WIDTH - 350, 10)

            # В функции main или в другом месте, где происходит отрисовка экрана
            draw_level_progress_bar(window, offset_y, 2150)
            if player.hit:
                player = Player(100, 500, 50, 50)
                offset_x = 0
                offset_y = 0

            if ((player.rect.right - offset_x >= WIDTH - scroll_area_width) and player.x_vel > 0) or (
                (player.rect.left - offset_x <= scroll_area_width) and player.x_vel < 0):
                    offset_x += player.x_vel
            if ((player.rect.top - offset_y >= HEIGHT - scroll_area_height) and player.y_vel > 0):
                offset_y += player.y_vel
            elif((player.rect.bottom - offset_y <= scroll_area_height) and player.y_vel < 0):
                offset_y += player.y_vel


            pass
        pygame.display.update()
        
    pygame.quit()


if __name__ == "__main__":
    main(window)
