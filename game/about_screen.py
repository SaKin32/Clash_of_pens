"""About Us screen: team members, roles and photos."""

import pygame

from common.constants import (
    SCREEN_WIDTH,
    BG_COLOR,
    TEXT_COLOR,
    HEADING_COLOR,
    FONT_SIZE_HEADING,
    FONT_SIZE_BUTTON,
    FONT_SIZE_SMALL,
    BACK_BUTTON_RECT,
)
from game.button import Button
from game.screen_manager import Screen

# Fill in real names and roles later. Photos can be added to each entry.
TEAM_MEMBERS = [
    ("Member 1", "Role"),
    ("Member 2", "Role"),
    ("Member 3", "Role"),
    ("Member 4", "Role"),
    ("Member 5", "Role"),
    ("Member 6", "Role"),
]


class AboutScreen(Screen):
    """Shows the team credits."""

    def __init__(self, manager):
        super().__init__(manager)
        self.heading_font = pygame.font.Font(None, FONT_SIZE_HEADING)
        self.name_font = pygame.font.Font(None, FONT_SIZE_BUTTON)
        self.role_font = pygame.font.Font(None, FONT_SIZE_SMALL)
        self.back_btn = Button("Back", BACK_BUTTON_RECT, self.on_back)

    def on_back(self) -> None:
        self.manager.switch("title")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()
            return
        self.back_btn.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)

        heading = self.heading_font.render("About Us", True, HEADING_COLOR)
        surface.blit(heading, heading.get_rect(center=(SCREEN_WIDTH // 2, 120)))

        # Two columns, three rows
        for i, (name, role) in enumerate(TEAM_MEMBERS):
            col, row = i % 2, i // 2
            x = SCREEN_WIDTH // 2 + (col - 0.5) * 460
            y = 240 + row * 110
            name_surf = self.name_font.render(name, True, TEXT_COLOR)
            role_surf = self.role_font.render(role, True, TEXT_COLOR)
            surface.blit(name_surf, name_surf.get_rect(center=(x, y)))
            surface.blit(role_surf, role_surf.get_rect(center=(x, y + 34)))

        self.back_btn.draw(surface)