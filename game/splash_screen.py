"""Startup screens: game logo for a few seconds, then the group photo with a loading bar."""

import pygame
from game import music

from common.constants import (
    GAME_TITLE,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BG_COLOR,
    TEXT_COLOR,
    TITLE_COLOR,
    FONT_SIZE_TITLE,
    FONT_SIZE_BUTTON,
)
from game.assets import load_image, load_cover_image, load_font
from game.screen_manager import Screen

LOGO_FILE = "Clash_of_pen_logo.png"
GROUP_FILE = "Clash_of_Pens_GP.png"

LOGO_TIME = 5.0      # seconds the logo stays on screen
LOADING_TIME = 3.0   # seconds the loading bar takes to fill
FADE_TIME = 0.6      # fade in / fade out of the logo and the photo

LOGO_MAX_SIZE = (int(SCREEN_WIDTH * 0.7), int(SCREEN_HEIGHT * 0.6))
BAR_RECT = (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT - 80, 600, 18)
BAR_BG_COLOR = (50, 52, 60)
BAR_FILL_COLOR = (255, 215, 100)


class SplashScreen(Screen):
    """Phase 1: logo. Phase 2: group photo with a loading bar. Then the title screen."""

    def __init__(self, manager):
        super().__init__(manager)
        self.title_font = load_font(FONT_SIZE_TITLE)
        self.text_font = load_font(FONT_SIZE_BUTTON)
        self.photo = load_cover_image(GROUP_FILE, (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.logo = self._load_logo()
        # Dark band at the bottom so the loading text is easy to read on any photo
        self.band = pygame.Surface((SCREEN_WIDTH, 170), pygame.SRCALPHA)
        self.band.fill((0, 0, 0, 150))
        self.phase = "logo"
        self.timer = 0.0

    @staticmethod
    def _load_logo():
        """Load the logo so it fills the whole window (keeps its shape, crops extra edges)."""
        image = load_image(LOGO_FILE)
        if image is None:
            return None
        w, h = image.get_size()
        scale = max(SCREEN_WIDTH / w, SCREEN_HEIGHT / h)
        scaled = pygame.transform.smoothscale(
            image, (max(1, round(w * scale)), max(1, round(h * scale)))
        )
        logo = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        logo.blit(scaled, ((SCREEN_WIDTH - scaled.get_width()) // 2,
                           (SCREEN_HEIGHT - scaled.get_height()) // 2))
        return logo

    def on_enter(self) -> None:
        self.phase = "logo"
        self.timer = 0.0

    def update(self, dt: float) -> None:
        self.timer += min(dt, 0.1)  # a lag spike must not eat the logo time
        if self.phase == "logo":
            if self.timer >= LOGO_TIME:
                self.phase = "loading"
                self.timer = 0.0
                music.start()
        elif self.timer >= LOADING_TIME:
            self.manager.switch("title")

    # ----- drawing -----

    def _fade(self) -> float:
        """0..1 opacity: fades in at the start of a phase, and out at the end of the logo."""
        fade = min(1.0, self.timer / FADE_TIME)
        if self.phase == "logo":
            fade = min(fade, (LOGO_TIME - self.timer) / FADE_TIME)
        return max(0.0, min(1.0, fade))

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)
        if self.phase == "logo":
            self._draw_logo(surface)
        else:
            self._draw_loading(surface)

    def _draw_logo(self, surface: pygame.Surface) -> None:
        alpha = int(255 * self._fade())
        if self.logo:
            image = self.logo.copy()
            image.set_alpha(alpha)
            surface.blit(image, image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
        else:
            text = self.title_font.render(GAME_TITLE, True, TITLE_COLOR)
            text.set_alpha(alpha)
            surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

    def _draw_loading(self, surface: pygame.Surface) -> None:
        if self.photo:
            surface.blit(self.photo, (0, 0))
            # Fade the photo in from black at the start
            cover = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            cover.set_alpha(int(255 * (1 - self._fade())))
            surface.blit(cover, (0, 0))
        surface.blit(self.band, (0, SCREEN_HEIGHT - self.band.get_height()))

        progress = min(1.0, self.timer / LOADING_TIME)
        label = self.text_font.render(f"Loading...  {int(progress * 100)}%", True, TEXT_COLOR)
        surface.blit(label, label.get_rect(midbottom=(SCREEN_WIDTH // 2, BAR_RECT[1] - 14)))

        bar = pygame.Rect(BAR_RECT)
        pygame.draw.rect(surface, BAR_BG_COLOR, bar, border_radius=9)
        if progress > 0:
            fill = bar.copy()
            fill.width = max(bar.height, int(bar.width * progress))
            pygame.draw.rect(surface, BAR_FILL_COLOR, fill, border_radius=9)
        pygame.draw.rect(surface, TEXT_COLOR, bar, width=2, border_radius=9)