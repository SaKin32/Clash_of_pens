"""Entry point for Clash of Pens."""

import sys

import pygame

from common.constants import (
    GAME_TITLE, VERSION, SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR
)
from game import settings
from game.about_screen import AboutScreen
from game.difficulty_screen import DifficultyScreen
from game.how_to_play_screen import HowToPlayScreen
from game.match_screen import MatchScreen
from game.mode_select_screen import ModeSelectScreen
from game.pen_select_screen import PenSelectScreen
from game.team_size_screen import TeamSizeScreen
from game.screen_manager import ScreenManager
from game.title_screen import TitleScreen


def main():
    pygame.init()
    settings.load()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(f"{GAME_TITLE} v{VERSION}")
    clock = pygame.time.Clock()

    manager = ScreenManager()
    manager.register("title", TitleScreen(manager))
    manager.register("mode_select", ModeSelectScreen(manager))
    manager.register("about", AboutScreen(manager))
    manager.register("difficulty_select", DifficultyScreen(manager))
    manager.register("team_size_select", TeamSizeScreen(manager))
    manager.register("pen_select", PenSelectScreen(manager))
    manager.register("how_to_play", HowToPlayScreen(manager))
    manager.register("match", MatchScreen(manager))
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