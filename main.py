"""Entry point for Clash of Pens."""

import sys

import pygame
import pymunk

from common.constants import (
    GAME_TITLE, VERSION, SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR, TEXT_COLOR
)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(f"{GAME_TITLE} v{VERSION}")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 48)

    # Smoke test: confirm pymunk is installed and working
    space = pymunk.Space()
    space.gravity = (0, 0)
    physics_ok = space.gravity == (0, 0)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        screen.fill(BG_COLOR)
        text = f"{GAME_TITLE} - setup OK | pymunk: {'OK' if physics_ok else 'FAIL'}"
        surf = font.render(text, True, TEXT_COLOR)
        screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()