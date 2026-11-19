"""Small music icon button: click to turn the music On/Off.

Off  = the icon fades to a dim grey look.   On = it fades back to full colour.
Every click plays a short "press and bounce" animation.
"""

import math

import pygame

from game import settings
from game.assets import load_image

ICON_FILE = "music.png"
ICON_SIZE = 64
ALPHA_THRESHOLD = 128  # pixels fainter than this are treated as empty when trimming
OFF_LEVEL = 0.4  # how bright the icon stays when music is Off (0 = invisible, 1 = unchanged)
OFF_BRIGHTNESS = 0.7  # colour of the Off icon (grey) is this bright
OFF_OPACITY = 0.9  # how solid the Off icon is (1 = fully solid)
FADE_SPEED = 4.0  # colour fade speed (1 / seconds)
CLICK_TIME = 0.5  # seconds the press-and-bounce animation lasts
CLICK_DEPTH = 0.22  # how much the icon shrinks when pressed


def _fit(name: str, size: int):
    """Load an icon, trim empty transparent borders and fit it into size x size WITHOUT stretching."""
    image = load_image(name)
    if image is None:
        return None
    mask = pygame.mask.from_surface(image, ALPHA_THRESHOLD)
    rects = mask.get_bounding_rects()
    if rects:  # remove faint/see-through halos completely, keep only the solid part of the icon
        solid = pygame.Surface(image.get_size(), pygame.SRCALPHA)
        mask.to_surface(solid, setsurface=image, unsetcolor=(0, 0, 0, 0))
        image = solid.subsurface(rects[0].unionall(rects[1:])).copy()
    scale = size / max(image.get_width(), image.get_height())
    new_size = (max(1, round(image.get_width() * scale)), max(1, round(image.get_height() * scale)))
    return pygame.transform.smoothscale(image, new_size)


class MusicIcon:
    """Icon button that draws assets/images/music.png (dim grey while music is Off)."""

    def __init__(self, position: tuple, on_toggle, size: int = ICON_SIZE):
        self.rect = pygame.Rect(position[0], position[1], size, size)
        self.on_toggle = on_toggle
        self.image = _fit(ICON_FILE, size)
        self.dim_image = None
        if self.image:
            self.dim_image = self._make_grey(self.image)
        self.level = 1.0 if settings.is_music_on() else OFF_LEVEL  # current brightness
        self.click_time = CLICK_TIME  # CLICK_TIME means "no animation running"
        self._last_tick = pygame.time.get_ticks()

    @staticmethod
    def _make_grey(image: pygame.Surface) -> pygame.Surface:
        """Grey copy of the icon that keeps the original see-through (alpha) areas."""
        grey = pygame.transform.grayscale(image).convert_alpha()
        shape = image.copy()
        shape.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_ADD)  # colours -> white, alpha kept
        grey.blit(shape, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)  # grey colours, original alpha
        return grey


    @property
    def off_amount(self) -> float:
        """0.0 while music is On, 1.0 while it is Off (moves smoothly in between)."""
        return max(0.0, min(1.0, (1.0 - self.level) / (1.0 - OFF_LEVEL)))


    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.click_time = 0.0
                self.on_toggle()

    def _update(self) -> None:
        now = pygame.time.get_ticks()
        dt = min(0.1, (now - self._last_tick) / 1000)
        self._last_tick = now
        target = 1.0 if settings.is_music_on() else OFF_LEVEL
        step = FADE_SPEED * dt
        self.level += max(-step, min(step, target - self.level))
        self.click_time = min(CLICK_TIME, self.click_time + dt)

    def _scale(self) -> float:
        """Press-and-bounce: shrinks at once, springs back a little too big, then settles at 1."""
        p = self.click_time / CLICK_TIME
        return 1.0 - CLICK_DEPTH * math.exp(-5 * p) * math.cos(2.5 * math.pi * p) if p < 1 else 1.0

    def draw(self, surface: pygame.Surface) -> None:
        self._update()
        scale = self._scale()
        if self.image:
            mix = (self.level - OFF_LEVEL) / (1.0 - OFF_LEVEL)  # 0 = fully Off look, 1 = fully On look
            frame = self.dim_image.copy()
            frame.fill((int(255 * OFF_BRIGHTNESS),) * 3 + (int(255 * OFF_OPACITY),), special_flags=pygame.BLEND_RGBA_MULT)
            colour = self.image.copy()
            colour.fill((255, 255, 255, int(255 * max(0.0, min(1.0, mix)))), special_flags=pygame.BLEND_RGBA_MULT)
            frame.blit(colour, (0, 0))
        else:  # icon file missing: draw a simple round placeholder so the button still works
            frame = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.circle(frame, (40, 40, 40), frame.get_rect().center, self.rect.width // 2)
            pygame.draw.circle(frame, (255, 255, 255), frame.get_rect().center, self.rect.width // 2, 3)
            if not settings.is_music_on():
                frame.set_alpha(int(255 * OFF_LEVEL))
        if abs(scale - 1.0) > 0.002:
            size = (max(1, round(frame.get_width() * scale)), max(1, round(frame.get_height() * scale)))
            frame = pygame.transform.smoothscale(frame, size)
        surface.blit(frame, frame.get_rect(center=self.rect.center))