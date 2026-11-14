"""Short loading screen shown after New Game or Resume is pressed."""

import pygame

from common.constants import SCREEN_WIDTH, SCREEN_HEIGHT, TEXT_COLOR, FONT_SIZE_BUTTON
from game.assets import load_cover_image, load_font
from game.screen_manager import Screen
from game.splash_screen import GROUP_FILE, BAR_RECT, BAR_BG_COLOR, BAR_FILL_COLOR

MENU_LOADING_TIME = 1.5  # seconds the bar takes to fill


class LoadingScreen(Screen):
    """Group photo with a loading bar, then it opens the screen it was asked to open.

    Use:  self.manager.get("loading").go("mode_select")
          self.manager.get("loading").go(action=some_function)
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.font = load_font(FONT_SIZE_BUTTON)
        self.photo = load_cover_image(GROUP_FILE, (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.band = pygame.Surface((SCREEN_WIDTH, 170), pygame.SRCALPHA)
        self.band.fill((0, 0, 0, 150))
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
        surface.blit(self.band, (0, SCREEN_HEIGHT - self.band.get_height()))

        progress = min(1.0, self.timer / MENU_LOADING_TIME)
        label = self.font.render(f"Loading...  {int(progress * 100)}%", True, TEXT_COLOR)
        surface.blit(label, label.get_rect(midbottom=(SCREEN_WIDTH // 2, BAR_RECT[1] - 14)))

        bar = pygame.Rect(BAR_RECT)
        pygame.draw.rect(surface, BAR_BG_COLOR, bar, border_radius=9)
        if progress > 0:
            fill = bar.copy()
            fill.width = max(bar.height, int(bar.width * progress))
            pygame.draw.rect(surface, BAR_FILL_COLOR, fill, border_radius=9)
        pygame.draw.rect(surface, TEXT_COLOR, bar, width=2, border_radius=9)