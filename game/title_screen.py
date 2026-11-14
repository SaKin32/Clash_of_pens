"""Title screen: background, game title, main menu buttons and version label."""

import pygame
from game import music

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
from game import settings
from game.assets import load_cover_image, load_font
from game.splash_screen import GROUP_FILE
from game.badge_button import BadgeButton, outlined_text
from game.button import Button
from game.music_icon import MusicIcon, ICON_SIZE
from game.screen_manager import Screen

RIGHT_MARGIN = 136  # gap between the buttons and the right edge of the window
BACKGROUND_FILE = "assets/images/title_bg.png"


class TitleScreen(Screen):
    """Main menu shown when the game starts."""

    def __init__(self, manager):
        super().__init__(manager)
        self.title_font = load_font(FONT_SIZE_TITLE)
        self.small_font = load_font(FONT_SIZE_SMALL)
        self.has_save = save.has_save()

        self.background = self._load_background()
        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill(OVERLAY_COLOR)

        self.new_game_btn = BadgeButton("New Game", self._rect(0), self.on_new_game)
        self.resume_btn = BadgeButton(
           "Resume", self._rect(1), self.on_resume, enabled=self.has_save
        )
        self.about_btn = BadgeButton("About Us", self._rect(2), self.on_about)
        self.quit_btn = Button("Quit", self._rect(3), self.on_quit)
        self.version_label = self._make_version_label()
        self.music_icon = MusicIcon((20, SCREEN_HEIGHT - 20 - ICON_SIZE), self.on_toggle_music)
        self.quit_btn = Button("Quit", self._rect(4), self.on_quit)
        self.buttons = [
            self.new_game_btn,
            self.resume_btn,
            self.about_btn,
        ]

    @staticmethod
    def _rect(index: int) -> tuple:
        """Return the rect for the button at the given vertical position."""
        x = SCREEN_WIDTH - BUTTON_WIDTH - RIGHT_MARGIN
        y = 260 + index * (BUTTON_HEIGHT + BUTTON_GAP)
        return (x, y, BUTTON_WIDTH, BUTTON_HEIGHT)

    def _make_version_label(self) -> pygame.Surface:
        """"Version 0.1.0" as white text with a black border, so it reads on any background."""
        return outlined_text(self.small_font, f"Version {VERSION}", (255, 255, 255))

    @staticmethod
    def _load_background():
        """Load the group photo as the background, or return None if the file is missing."""
        return load_cover_image(GROUP_FILE, (SCREEN_WIDTH, SCREEN_HEIGHT))


    def on_enter(self) -> None:
        """Refresh Resume and Music state whenever this screen becomes active."""
        self.has_save = save.has_save()
        self.resume_btn.enabled = self.has_save
        music.start()

    # Button callbacks
    def on_new_game(self) -> None:
        self.manager.get("loading").go("mode_select")

    def on_resume(self) -> None:
        state = save.load_game()
        if state is None:
            return

        def open_match():
            self.manager.get("match").resume_from_save(state)
            self.manager.switch("match")

        self.manager.get("loading").go(action=open_match)

    def on_about(self) -> None:
        self.manager.switch("about")

    def on_toggle_music(self) -> None:
        settings.set_music_on(not settings.is_music_on())
        music.refresh()

    def on_quit(self) -> None:
        # A match in progress is saved by the match screen itself (Save & Exit, or closing
        # the window), so quitting from the title screen leaves the existing save alone.
        self.manager.quit()

    def handle_event(self, event: pygame.event.Event) -> None:
        for button in self.buttons:
            button.handle_event(event)
        self.music_icon.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        if self.background:
            surface.blit(self.background, (0, 0))
        else:
            surface.fill(BG_COLOR)

        for button in self.buttons:
            button.draw(surface)
        self.music_icon.draw(surface)

        surface.blit(
            self.version_label,
            self.version_label.get_rect(bottomright=(SCREEN_WIDTH - 20, SCREEN_HEIGHT - 18)),
        )