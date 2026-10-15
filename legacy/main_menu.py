import pygame
import Level_1

# Инициализация Pygame
pygame.init()
HEIGHT = 720
WIDTH = 1280

# Настройка экрана
screen = pygame.display.set_mode((WIDTH, HEIGHT))

# Цвета
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
# Определение темно-фиолетового цвета
DARK_PURPLE = (75, 0, 130)

# Загрузка изображения фона
background_image = pygame.image.load('assets/Background/Background_cosmos.png').convert()
background_image = pygame.transform.scale(background_image, (1280, 720))  # Растягиваем до нужных размеров
background_rect = background_image.get_rect()

# Загрузка изображени логотипа
logo_image = pygame.image.load('assets/Logo/Star_Jump.png').convert_alpha()
logo_image = pygame.transform.scale(logo_image, (320, 320))  # Растягиваем до нужных размеров

# Получаем прямоугольник, который покрывает изображение
logo_rect = logo_image.get_rect()

# Устанавливаем позицию прямоугольника
logo_rect.x = WIDTH // 2 - 175
logo_rect.y = HEIGHT // 2 - 350

# Флаг для отслеживания состояния меню
menu_active = True

# Флаг для отслеживания состояния всплывающего окна
popup_active = False

class Button:
    def __init__(self, x, y, width, height, text, text_color, button_color, hover_color, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.text_color = text_color
        self.button_color = button_color
        self.hover_color = hover_color
        self.action = action
        self.hovered = False

    def draw(self, surface, outline=None):
        # Отрисовка кнопки
        color = self.hover_color if self.hovered else self.button_color
        pygame.draw.rect(surface, color, self.rect)

        # Отрисовка текста на кнопке
        font = pygame.font.Font(None, 36)
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

        # Отрисовка контура кнопки (если указан)
        if outline:
            pygame.draw.rect(surface, outline, self.rect, 2)

    def update(self, mouse_pos):
        # Обновление состояния кнопки при наведении
        self.hovered = self.rect.collidepoint(mouse_pos)

    def click(self):
        # Выполнение действия кнопки при клике
        if self.action:
            self.action()

def run_Level_1():
    Level_1.main(window=screen)

def start_game():
    global menu_active
    menu_active = False
    run = True
    run_Level_1()

def exit_game():
    pygame.quit()

def create_popup_window():
    global popup_active
    popup_active = not popup_active  # Переключение состояния всплывающего окна

# Изменение функции draw_popup_window для изменения фона на темно-фиолетовый
# и перепозиционирования окна над кнопкой INFO в правом нижнем углу
def draw_popup_window():
    # Создание поверхности для всплывающего окна
    popup_surface = pygame.Surface((230, 130))
    popup_surface.fill(DARK_PURPLE)  # Заполнение поверхности темно-фиолетовым цветом

    # Создание прямоугольника для всплывающего окна и позиционирование его над кнопкой INFO
    popup_rect = popup_surface.get_rect(bottomright=(WIDTH - 10, HEIGHT - 120))

    # Отрисовка всплывающей поверхности на экране
    screen.blit(popup_surface, popup_rect)

    # Отображение текста на всплывающем окне белым цветом
    font = pygame.font.Font(None, 24)
    text_lines = [
        'Разаработан студентом',
        'группы 1003',
        'Бекмурат Нуржан',
        'Telegram: @NurikYT305'
    ]
    # Расчет начальной позиции y для вертикального центрирования текста
    start_y = popup_rect.top + 10
    for line in text_lines:
        text_surface = font.render(line, True, WHITE)
        text_rect = text_surface.get_rect(center=(popup_rect.centerx, start_y))
        screen.blit(text_surface, text_rect)
        start_y += 30  # Переход к следующей строке

def draw_menu():
    # Отрисовка фона
    screen.blit(background_image, background_rect)
    screen.blit(logo_image, logo_rect)

    # Создание и отрисовка кнопок
    start_button = Button(WIDTH // 2 - 100, HEIGHT // 2, 200, 60, 'Старт', BLUE, WHITE, RED, start_game)
    exit_button = Button(WIDTH // 2 - 100, (HEIGHT // 2) + 100, 200, 60, 'Выход', BLUE, WHITE, RED, exit_game)
    start_button.draw(screen, BLACK)
    exit_button.draw(screen, BLACK)

    return start_button, exit_button

def add_popup_button():
    # Определение позиции и размера кнопки
    button_x = WIDTH - 100  # 200 пикселей от правого края
    button_y = HEIGHT - 100  # 100 пикселей от нижнего края
    button_width = 80
    button_height = 80

    # Создание кнопки
    popup_button = Button(button_x, button_y, button_width, button_height, 'INFO', BLUE, WHITE, RED, create_popup_window)

    # Отрисовка кнопки
    popup_button.draw(screen, BLACK)

    # Возврат кнопки для дальнейшего использования
    return popup_button

def main():
    global menu_active, popup_active
    while menu_active:
        start_button, exit_button = draw_menu()
        popup_button = add_popup_button()  # Добавление всплывающей кнопки

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if start_button.rect.collidepoint(mouse_pos):
                    start_button.click()
                elif exit_button.rect.collidepoint(mouse_pos):
                    exit_button.click()
                elif popup_button.rect.collidepoint(mouse_pos):  # Проверка нажатия всплывающей кнопки
                    popup_button.click()

        # Отрисовка всплывающего окна, если оно активно
        if popup_active:
            draw_popup_window()

        pygame.display.update()

if __name__ == '__main__':
    main()
