"""Short loading screen shown after New Game or Resume is pressed."""

import pygame

from common.constants import SCREEN_WIDTH, SCREEN_HEIGHT, TEXT_COLOR, FONT_SIZE_BUTTON
from game.assets import load_cover_image, load_font
from game.screen_manager import Screen
from game.progress_bar import LoadingBar
from game.splash_screen import GROUP_FILE

LOADING_FILE = "loading_fight.png"
MENU_LOADING_TIME = 3.0  # seconds the bar takes to fill


class LoadingScreen(Screen):
    """Group photo with a loading bar, then it opens the screen it was asked to open.

    Use:  self.manager.get("loading").go("mode_select")
          self.manager.get("loading").go(action=some_function)
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.font = load_font(FONT_SIZE_BUTTON)
        self.photo = load_cover_image(LOADING_FILE, (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.bar = LoadingBar(self.font)
        self.target = "title"
        self.action = None
        self.timer = 0.0

    def go(self, target: str = "title", action=None) -> None:
        self.target = target
        self.action = action
        self.manager.switch("loading")

    def on_enter(self) -> None:
        self.timer = 0.0

    def update(self, dt: float) -> None:
        self.timer += min(dt, 0.1)
        if self.timer >= MENU_LOADING_TIME:
            action, target = self.action, self.target
            self.action = None  # if the action opens nothing, the next frame falls back to the title
            if action:
                action()
            else:
                self.manager.switch(target)

    def draw(self, surface: pygame.Surface) -> None:
        if self.photo:
            surface.blit(self.photo, (0, 0))
        self.bar.draw(surface, self.timer / MENU_LOADING_TIME)