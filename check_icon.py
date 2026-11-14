"""Diagnostic: why is the music icon not visible? Run from the project folder:  python check_icon.py
Delete this file afterwards."""

import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((1280, 720))

from common.constants import SCREEN_WIDTH, SCREEN_HEIGHT  # noqa: E402
from common.paths import resource_path  # noqa: E402
from game import music_icon  # noqa: E402
from game.assets import load_image  # noqa: E402

print("window:", SCREEN_WIDTH, "x", SCREEN_HEIGHT)

path = resource_path("assets/images/music.png")
print("1) file:", path, "->", "FOUND" if os.path.exists(path) else "NOT FOUND  <-- put music.png in assets\\images")

image = load_image("music.png")
if image is None:
    print("   pygame could not read the picture (wrong name or broken file)")
else:
    w, h = image.get_size()
    alphas = [image.get_at((x, y)).a for x in range(0, w, max(1, w // 64)) for y in range(0, h, max(1, h // 64))]
    solid = sum(a >= music_icon.ALPHA_THRESHOLD for a in alphas) / len(alphas) * 100
    seen = sum(a > 0 for a in alphas) / len(alphas) * 100
    print(f"2) picture size {w}x{h}; visible pixels {seen:.0f}%; solid pixels (alpha>={music_icon.ALPHA_THRESHOLD}) {solid:.0f}%")
    if solid < 0.5:
        print("   <-- the picture is almost fully see-through: lower ALPHA_THRESHOLD in music_icon.py (try 20)")

icon = music_icon.MusicIcon((20, SCREEN_HEIGHT - 20 - music_icon.ICON_SIZE), lambda: None)
print("3) icon rect:", icon.rect, "| picture used:", "YES" if icon.image else "NO (placeholder circle is drawn)")
inside = screen.get_rect().contains(icon.rect)
print("   inside the window:", "yes" if inside else "NO  <-- icon is outside the screen")

screen.fill((30, 60, 110))
icon.draw(screen)
px = [screen.get_at((x, y))[:3] for x in range(icon.rect.left, icon.rect.right, 4) for y in range(icon.rect.top, icon.rect.bottom, 4)]
changed = sum(p != (30, 60, 110) for p in px)
print(f"4) drawn pixels differing from the background: {changed} of {len(px)}", "(OK)" if changed > 20 else " <-- nothing visible gets drawn")

print("5) lines in game/title_screen.py that mention music_icon:")
try:
    for number, line in enumerate(open("game/title_screen.py", encoding="utf-8"), 1):
        if re.search(r"music_icon|MusicIcon|self\.dim|off_amount", line):
            print(f"   {number:>4}: {line.rstrip()}")
except OSError as error:
    print("   could not read:", error)