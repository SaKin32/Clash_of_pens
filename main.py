"""Entry point for Clash of Pens."""

import sys

import pygame

from common.constants import (
    GAME_TITLE, VERSION, SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR
)
from game.about_screen import AboutScreen
from game.mode_select_screen import ModeSelectScreen
from game.screen_manager import ScreenManager
from game.title_screen import TitleScreen


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(f"{GAME_TITLE} v{VERSION}")
    clock = pygame.time.Clock()

    manager = ScreenManager()
    manager.register("title", TitleScreen(manager))
    manager.register("mode_select", ModeSelectScreen(manager))
    manager.register("about", AboutScreen(manager))
    manager.switch("title")

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