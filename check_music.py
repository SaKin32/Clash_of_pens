"""Finds out why the music is silent. Run from the project folder: python check_music.py"""

import os
import time

import pygame

from game import settings
from game.music import MUSIC_BASE, MUSIC_EXTENSIONS

pygame.init()
settings.load()

print("1) Music setting is On:", settings.is_music_on(), "  <- must be True (title screen button: Music: On)")
print("2) Sound system started:", bool(pygame.mixer.get_init()), "  <- must be True")

folder = os.path.dirname(MUSIC_BASE)
print("3) Files inside", folder + ":", os.listdir(folder) if os.path.isdir(folder) else "FOLDER NOT FOUND")

found = None
for extension in MUSIC_EXTENSIONS:
    path = MUSIC_BASE + extension
    exists = os.path.exists(path)
    print("   ", path, "->", "FOUND" if exists else "missing")
    if exists and not found:
        found = path

if found and pygame.mixer.get_init():
    try:
        pygame.mixer.music.load(found)
        pygame.mixer.music.play()
        time.sleep(1.5)
        print("4) Playing", found, "-> busy:", pygame.mixer.music.get_busy(), " (you should hear it now)")
    except pygame.error as error:
        print("4) Could not play", found, "->", error)
else:
    print("4) Nothing to play (fix the lines above first)")