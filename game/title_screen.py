"""Title screen: background, game title, main menu buttons and version label."""

import pygame

from common.constants import (
    GAME_TITLE,
    VERSION,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BG_COLOR,
    TEXT_COLOR,
    TITLE_COLOR,
    OVERLAY_COLOR,
    BUTTON_WIDTH,
    BUTTON_HEIGHT,
    BUTTON_GAP,
    FONT_SIZE_TITLE,
    FONT_SIZE_SMALL,
)
from common.paths import resource_path
from game import save
from game.button import Button
from game.screen_manager import Screen

BACKGROUND_FILE = "assets/images/title_bg.png"


class TitleScreen(Screen):
    """Main menu shown when the game starts."""

    def __init__(self, manager):
        super().__init__(manager)
        self.title_font = pygame.font.Font(None, FONT_SIZE_TITLE)
        self.small_font = pygame.font.Font(None, FONT_SIZE_SMALL)
        self.music_on = True
        self.has_save = save.has_save()

        self.background = self._load_background()
        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill(OVERLAY_COLOR)

        self.new_game_btn = Button("New Game", self._rect(0), self.on_new_game)
        self.resume_btn = Button(
            "Resume", self._rect(1), self.on_resume, enabled=self.has_save
        )
        self.about_btn = Button("About Us", self._rect(2), self.on_about)
        self.music_btn = Button("Music: On", self._rect(3), self.on_toggle_music)
        self.quit_btn = Button("Quit", self._rect(4), self.on_quit)
        self.buttons = [
            self.new_game_btn,
            self.resume_btn,
            self.about_btn,
            self.music_btn,
            self.quit_btn,
        ]

    @staticmethod
    def _rect(index: int) -> tuple:
        """Return the rect for the button at the given vertical position."""
        x = (SCREEN_WIDTH - BUTTON_WIDTH) // 2
        y = 260 + index * (BUTTON_HEIGHT + BUTTON_GAP)
        return (x, y, BUTTON_WIDTH, BUTTON_HEIGHT)

    @staticmethod
    def _load_background():
        """Load the background image, or return None if the file is missing."""
        try:
            image = pygame.image.load(resource_path(BACKGROUND_FILE)).convert()
        except (pygame.error, FileNotFoundError):
            return None
        return pygame.transform.smoothscale(image, (SCREEN_WIDTH, SCREEN_HEIGHT))

    def on_enter(self) -> None:
        """Re-check the save file whenever this screen becomes active."""
        self.has_save = save.has_save()
        self.resume_btn.enabled = self.has_save

    # Button callbacks
    def on_new_game(self) -> None:
        self.manager.switch("mode_select")

    def on_resume(self) -> None:
        state = save.load_game()
        if state is None:
            return
        print("Resume:", state)  # Real match loading comes in a later step

    def on_about(self) -> None:
        self.manager.switch("about")

    def on_toggle_music(self) -> None:
        self.music_on = not self.music_on
        self.music_btn.text = "Music: On" if self.music_on else "Music: Off"

    def on_quit(self) -> None:
        # Placeholder state. Real match data replaces this once matches exist.
        save.save_game({"mode": "pvc", "pen": "ball_pen", "score": [0, 0], "round": 1})
        self.manager.quit()

    def handle_event(self, event: pygame.event.Event) -> None:
        for button in self.buttons:
            button.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        if self.background:
            surface.blit(self.background, (0, 0))
            surface.blit(self.overlay, (0, 0))
        else:
            surface.fill(BG_COLOR)

        title = self.title_font.render(GAME_TITLE, True, TITLE_COLOR)
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 160)))

        for button in self.buttons:
            button.draw(surface)

        version = self.small_font.render(f"v{VERSION}", True, TEXT_COLOR)
        surface.blit(
            version, version.get_rect(bottomright=(SCREEN_WIDTH - 16, SCREEN_HEIGHT - 12))
        )