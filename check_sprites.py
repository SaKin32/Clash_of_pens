"""Quick check: shows how every pen picture is drawn, and saves sprites_check.png.

Run it from the project folder:   python check_sprites.py
It changes nothing in the game.
"""

import os
import sys

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((900, 640))

from common.pen import PENS, PEN_ORDER
from game.assets import load_image
from game.match_art import _level, _trim, pen_sprite
from game.pen_select_screen import PEN_IMAGES

print("pygame", pygame.version.ver, "| python", sys.version.split()[0])
print()
print(f"{'pen':14s}{'file':>12s}{'leveled':>12s}{'ratio':>8s}{'hitbox':>10s}{'drawn':>10s}")

sheet = pygame.Surface((900, 640))
sheet.fill((120, 80, 40))
font = pygame.font.Font(None, 22)
y = 12
for key in PEN_ORDER:
    stats = PENS[key]
    image = load_image(PEN_IMAGES[key])
    leveled = _level(_trim(image))
    sprite = pen_sprite(key, stats.length, stats.width)
    lw, lh = leveled.get_size()
    print(
        f"{key:14s}{str(image.get_size()):>12s}{str((lw, lh)):>12s}{lw / lh:>8.1f}"
        f"{str((stats.length, stats.width)):>10s}{str(sprite.get_size()):>10s}"
    )
    sheet.blit(sprite, (20, y))
    small = pygame.transform.smoothscale(leveled, (300, max(1, round(300 * lh / lw))))
    sheet.blit(small, (500, y))
    sheet.blit(font.render(key, True, (255, 255, 255)), (300, y))
    y += 100

pygame.image.save(sheet, "sprites_check.png")
print()
print("Saved sprites_check.png (left: pens as the game draws them, right: the leveled picture)")