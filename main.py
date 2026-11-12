"""Entry point for Clash of Pens."""

import sys

import pygame

from common.constants import (
    GAME_TITLE, VERSION, SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR, TEXT_COLOR
)
from game.button import Button
from game.screen_manager import Screen, ScreenManager


class TestScreen(Screen):
    """Temporary screen to verify Button and ScreenManager."""

    def __init__(self, manager):
        super().__init__(manager)
        self.font = pygame.font.Font(None, 48)
        self.clicks = 0
        cx = SCREEN_WIDTH // 2
        self.buttons = [
            Button("Click me", (cx - 150, 300, 300, 70), self.on_click),
            Button("Disabled", (cx - 150, 390, 300, 70), enabled=False),
            Button("Quit", (cx - 150, 480, 300, 70), manager.quit),
        ]

    def on_click(self):
        self.clicks += 1

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def draw(self, surface):
        text = self.font.render(f"Clicks: {self.clicks}", True, TEXT_COLOR)
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 220)))
        for button in self.buttons:
            button.draw(surface)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(f"{GAME_TITLE} v{VERSION}")
    clock = pygame.time.Clock()

    manager = ScreenManager()
    manager.register("test", TestScreen(manager))
    manager.switch("test")

    while manager.running:
        dt = clock.tick(FPS) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                manager.quit()
            else:
                manager.current.handle_event(event)

        manager.current.update(dt)
        screen.fill(BG_COLOR)
        manager.current.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()