"""Mode selection screen: Player vs Computer, Player vs Player (Single / Team Match), Online."""

import pygame
from game import music

from common.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BG_COLOR,
    HEADING_COLOR,
    FONT_SIZE_HEADING,
    FONT_SIZE_SMALL,
    VERSION,
    BUTTON_HEIGHT,
    BUTTON_GAP,
    MODE_BUTTON_WIDTH,
)
from game import settings
from game import setup as game_setup
from game.assets import load_font, load_cover_image
from game.badge_button import BadgeButton, outlined_text
from game.icon_button import IconButton
from game.music_icon import MusicIcon, ICON_SIZE
from game.screen_manager import Screen

BACK_ICON_FILE = "back.png"
BACK_ICON_POSITION = (20, 20)  # top-left corner of the window


class ModeSelectScreen(Screen):
    """Lets the player choose how to play. Player vs Player opens a second list (Single / Team Match)."""

    def __init__(self, manager):
        super().__init__(manager)
        self.heading_font = load_font(FONT_SIZE_HEADING)
        self.small_font = load_font(FONT_SIZE_SMALL)
        self.background = load_cover_image("bg_img.png", (SCREEN_WIDTH, SCREEN_HEIGHT))

        self.view = "main"  # "main" = the 3 mode buttons, "pvp" = Single Match / Team Match
        self.main_buttons = [
            BadgeButton("Player vs Computer", self._rect(0), self.on_pvc),
            BadgeButton("Player vs Player", self._rect(1), self.on_pvp_menu),
            BadgeButton("Online (soon)", self._rect(2), self.on_online, enabled=False),
        ]
        self.pvp_buttons = [
            BadgeButton("Single Match", self._rect(0), self.on_single),
            BadgeButton("Team Match (2 vs 2)", self._rect(1), self.on_team),
        ]
        self.back_btn = IconButton(BACK_ICON_FILE, BACK_ICON_POSITION, self.on_back)
        self.music_icon = MusicIcon((20, SCREEN_HEIGHT - 20 - ICON_SIZE), self.on_toggle_music)  # bottom-left corner
        self.help_btn = BadgeButton(
            "How to Play",
            (SCREEN_WIDTH - 24 - 220, SCREEN_HEIGHT - 100, 220, 56),
            self.on_how_to_play,
        )
        self.version_label = outlined_text(self.small_font, f"Version {VERSION}", (255, 255, 255))

    @staticmethod
    def _rect(index: int) -> tuple:
        x = (SCREEN_WIDTH - MODE_BUTTON_WIDTH) // 2
        y = 230 + index * (BUTTON_HEIGHT + BUTTON_GAP)
        return (x, y, MODE_BUTTON_WIDTH, BUTTON_HEIGHT)

    @property
    def buttons(self) -> list:
        return self.main_buttons if self.view == "main" else self.pvp_buttons

    def on_enter(self) -> None:
        self.view = "main"
        music.start()

    # Mode callbacks
    def on_pvc(self) -> None:
        game_setup.begin("pvc")
        self.manager.switch("pen_select")  # Easy / Medium / Hard are picked on the pen screen

    def on_pvp_menu(self) -> None:
        self.view = "pvp"

    def on_single(self) -> None:
        game_setup.begin("pvp")
        self.manager.switch("pen_select")

    def on_team(self) -> None:
        game_setup.begin("team")
        game_setup.set_team_size(2)
        self.manager.switch("pen_select")

    def on_online(self) -> None:
        print("Online selected")  # online play is added in step 5

    def on_how_to_play(self) -> None:
        self.manager.get("how_to_play").return_to = "mode_select"
        self.manager.switch("how_to_play")

    def on_toggle_music(self) -> None:
        settings.set_music_on(not settings.is_music_on())
        music.refresh()

    def on_back(self) -> None:
        if self.view == "pvp":
            self.view = "main"  # back to the 3 mode buttons
        else:
            self.manager.switch("title")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()
            return
        for button in self.buttons:
            button.handle_event(event)
        self.back_btn.handle_event(event)
        self.music_icon.handle_event(event)
        self.help_btn.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        if self.background:
            surface.blit(self.background, (0, 0))
        else:
            surface.fill(BG_COLOR)

        title = "Select Mode" if self.view == "main" else "Player vs Player"
        heading = outlined_text(self.heading_font, title, HEADING_COLOR, outline=3)
        surface.blit(heading, heading.get_rect(center=(SCREEN_WIDTH // 2, 160)))

        for button in self.buttons:
            button.draw(surface)
        self.back_btn.draw(surface)
        self.music_icon.draw(surface)
        self.help_btn.draw(surface)

        surface.blit(
            self.version_label,
            self.version_label.get_rect(bottomright=(SCREEN_WIDTH - 24, SCREEN_HEIGHT - 8)),
        )