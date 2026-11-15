"""The pen select screen: flipping through pens, saving the pick, drawing in every mode."""

import pygame
import pytest

from common.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from common.pen import PEN_ORDER
from game import setup as game_setup
from game.pen_select_screen import PenSelectScreen
from game.screen_manager import ScreenManager


@pytest.fixture
def screen_and_surface():
    pygame.init()
    surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    game_setup.begin("pvp")
    screen = PenSelectScreen(ScreenManager())
    screen.on_enter()
    return screen, surface


def test_arrows_flip_through_pens_and_wrap(screen_and_surface):
    screen, _ = screen_and_surface
    assert screen.selected == PEN_ORDER[0]
    screen.step(1)
    assert screen.selected == PEN_ORDER[1]
    screen.step(-1)
    screen.step(-1)
    assert screen.selected == PEN_ORDER[-1]  # before the first pen comes the last one
    screen.step(1)
    assert screen.selected == PEN_ORDER[0]


def test_keyboard_arrows_flip_pens(screen_and_surface):
    screen, _ = screen_and_surface
    screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    assert screen.selected == PEN_ORDER[1]
    screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
    assert screen.selected == PEN_ORDER[0]


def test_next_saves_the_shown_pen_for_the_current_player(screen_and_surface):
    screen, _ = screen_and_surface
    screen.step(2)
    screen.on_next()
    assert game_setup.setup.pens[0] == PEN_ORDER[2]
    assert game_setup.setup.picking == 1  # now the second player picks


@pytest.mark.parametrize("mode", ["pvc", "pvp", "team"])
def test_every_pen_draws_in_every_mode(screen_and_surface, mode):
    screen, surface = screen_and_surface
    game_setup.begin(mode)
    if mode == "team":
        game_setup.set_team_size(2)
    screen.on_enter()
    for key in PEN_ORDER:
        screen.selected = key
        screen.draw(surface)


def test_every_pen_has_a_picture(screen_and_surface):
    screen, _ = screen_and_surface
    assert set(screen.pen_images) == set(PEN_ORDER)


def test_computer_mode_difficulty_is_chosen_on_this_screen(screen_and_surface):
    screen, surface = screen_and_surface
    game_setup.begin("pvc")
    screen.on_enter()
    assert [key for key, _ in screen.difficulty_buttons] == ["easy", "medium", "hard"]
    screen.set_difficulty("hard")
    assert game_setup.setup.difficulty == "hard"
    screen.draw(surface)


def test_all_pens_have_about_the_same_length_on_screen(screen_and_surface):
    import math

    screen, _ = screen_and_surface
    diagonals = [math.hypot(*image.get_size()) for image in screen.pen_images.values()]
    assert max(diagonals) - min(diagonals) < 4


def test_back_from_computer_mode_goes_to_mode_select():
    pygame.init()
    pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    manager = ScreenManager()
    screen = PenSelectScreen(manager)
    visited = []
    manager.switch = visited.append
    game_setup.begin("pvc")
    screen.on_enter()
    screen.on_back()
    assert visited == ["mode_select"]