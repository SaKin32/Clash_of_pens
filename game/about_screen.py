"""About Us screen: cinematic rolling credits over a blurred, darkened background."""

from typing import Optional
import pygame

from common.constants import (
    GAME_TITLE,
    VERSION,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BG_COLOR,
    TEXT_COLOR,
    TITLE_COLOR,
    HEADING_COLOR,
    FONT_SIZE_TITLE,
    FONT_SIZE_BUTTON,
    FONT_SIZE_SMALL,
)
from game.assets import load_image, load_cover_image, load_font
from game.icon_button import IconButton
from game.screen_manager import Screen

BACKGROUND_FILE = "bg_img.png"
LOGO_FILE = "Logo.webp"
BACK_ICON_FILE = "back.png"
BACK_ICON_POSITION = (20, 20)  # top-left corner of the window, same as on the Select Mode screen

CREDITS_TIME = 20.0          # seconds for the credits to roll through once, then it starts again
FADE_HEIGHT = 130            # pixels at the top and bottom where the text fades out
BLUR_RADIUS = 8              # blur strength (applied on a half-size copy)
DARKEN_ALPHA = 100           # 0 = no dark layer, 255 = black
LOGO_MAX_SIZE = (620, 240)
MUTED_COLOR = (170, 175, 190)  # student ID text

NAME_COLOR = (255, 255, 255)   # names are pure white
OUTLINE_COLOR = (0, 0, 0)      # thin border around the credit text
OUTLINE_ALPHA = 140            # 0 = no border, 255 = solid black border

# (name, student ID, role). Edit this list to change the credits.
TEAM_MEMBERS = [
    ("Luckman Rafique", "20255103041"),
    ("Md Taimur Rahman", "20255103046"),
    ("Md Showkotul Islam", "20255103058"),
    ("Shimul Islam", "20255103060"),
    ("Md Siam Khan", "20255103069"),
    ("Tanvir Ahmed", "20255103081"),
]
FOOTER_LINES = [
    "Built with Python, pygame-ce, pymunk",
    f"Version {VERSION}",
]


def blur_surface(image: pygame.Surface, radius: int) -> pygame.Surface:
    """Return a blurred copy of the image. Works on a half-size copy to stay fast."""
    size = image.get_size()
    small = pygame.transform.smoothscale(image, (size[0] // 2, size[1] // 2))
    if hasattr(pygame.transform, "gaussian_blur"):
        small = pygame.transform.gaussian_blur(small, radius)
    else:
        # Older pygame-ce: shrink a lot and grow back, which also blurs
        tiny = pygame.transform.smoothscale(small, (size[0] // 16, size[1] // 16))
        small = pygame.transform.smoothscale(tiny, small.get_size())
    return pygame.transform.smoothscale(small, size)


def render_outlined(font, text, color, outline=1, bold=False):
    """Text with a thin dark border, so it stays easy to read on any background.

    outline = border thickness in pixels. bold = draw the letters 1 pixel thicker.
    """
    base = font.render(text, True, color)
    extra = 1 if bold else 0
    size = (base.get_width() + 2 * outline + extra, base.get_height() + 2 * outline)
    border = pygame.Surface(size, pygame.SRCALPHA)
    dark = font.render(text, True, OUTLINE_COLOR)
    for dx in range(-outline, outline + 1):
        for dy in range(-outline, outline + 1):
            if dx * dx + dy * dy <= outline * outline + 1:
                for ex in range(extra + 1):
                    border.blit(dark, (outline + dx + ex, outline + dy))
    border.set_alpha(OUTLINE_ALPHA)
    result = pygame.Surface(size, pygame.SRCALPHA)
    result.blit(border, (0, 0))
    for ex in range(extra + 1):
        result.blit(base, (outline + ex, outline))
    return result


class AboutScreen(Screen):
    """Credits roll from the bottom to the top, then start again. ESC or Back leaves."""

    def __init__(self, manager):
        super().__init__(manager)
        self.title_font = load_font(FONT_SIZE_TITLE)
        self.name_font = load_font(FONT_SIZE_BUTTON)
        self.small_font = load_font(FONT_SIZE_SMALL)
        self.back_btn = IconButton(BACK_ICON_FILE, BACK_ICON_POSITION, self.on_back)

        self.background = None   # built the first time the screen opens
        self.credits = self._build_credits()
        self.layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.fade_mask = self._build_fade_mask()
        self.time = 0.0

    # ----- building (done once) -----

    def _load_logo(self):
        """Load the logo scaled to fit LOGO_MAX_SIZE, or None if the file is missing."""
        image = load_image(LOGO_FILE)
        if image is None:
            return None
        w, h = image.get_size()
        scale = min(LOGO_MAX_SIZE[0] / w, LOGO_MAX_SIZE[1] / h)
        size = (max(1, round(w * scale)), max(1, round(h * scale)))
        return pygame.transform.smoothscale(image, size)

    @staticmethod
    def _build_logos_row() -> Optional[pygame.Surface]:
        """Load and scale pythonlogo, pygame-ce, and pymunk side-by-side in a row."""
        names = ["pythonlogo.png", "pygame-ce.png", "pymunk.png"]
        loaded = []
        for name in names:
            img = load_image(name)
            if img:
                loaded.append(img)
        if not loaded:
            return None

        target_h = 80
        scaled = []
        for i, img in enumerate(loaded):
            # pygame-ce (index 1) is square, scale slightly larger for visual balance
            h = target_h + 15 if i == 1 else target_h
            w = max(1, round(img.get_width() * (h / img.get_height())))
            scaled.append(pygame.transform.smoothscale(img, (w, h)))

        gap = 42
        total_w = sum(s.get_width() for s in scaled) + gap * (len(scaled) - 1)
        max_h = max(s.get_height() for s in scaled)

        row = pygame.Surface((total_w, max_h), pygame.SRCALPHA)
        x = 0
        for s in scaled:
            y = (max_h - s.get_height()) // 2
            row.blit(s, (x, y))
            x += s.get_width() + gap
        return row

    def _build_credits(self) -> pygame.Surface:
        """Draw the whole credits text onto one tall surface."""
        logo = self._load_logo()
        blocks = []  # (surface, space_below)
        if logo:
            blocks.append((logo, 90))
        else:
            blocks.append((render_outlined(self.title_font, GAME_TITLE, TITLE_COLOR, outline=3), 90))
        for member in TEAM_MEMBERS:
            name, student_id = member[0], member[1]
            role = member[2] if len(member) > 2 else ""  # the role is optional
            blocks.append((render_outlined(self.name_font, name, NAME_COLOR, outline=1, bold=True), 4))
            if role:
                blocks.append((render_outlined(self.small_font, student_id, MUTED_COLOR), 4))
                blocks.append((render_outlined(self.small_font, role, HEADING_COLOR), 54))
            else:
                blocks.append((render_outlined(self.small_font, student_id, MUTED_COLOR), 54))
        blocks.append((self.small_font.render("", True, TEXT_COLOR), 40))
        for line in FOOTER_LINES:
            blocks.append((render_outlined(self.small_font, line, MUTED_COLOR), 8))
        logos_row = self._build_logos_row()
        if logos_row:
            blocks.append((logos_row, 30))

        height = sum(s.get_height() + gap for s, gap in blocks)
        credits = pygame.Surface((SCREEN_WIDTH, height), pygame.SRCALPHA)
        y = 0
        for surf, gap in blocks:
            credits.blit(surf, surf.get_rect(midtop=(SCREEN_WIDTH // 2, y)))
            y += surf.get_height() + gap
        return credits

    @staticmethod
    def _build_fade_mask() -> pygame.Surface:
        """White in the middle, fading to transparent at the top and bottom edges."""
        mask = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        mask.fill((255, 255, 255, 255))
        for i in range(FADE_HEIGHT):
            alpha = int(255 * i / FADE_HEIGHT)
            color = (255, 255, 255, alpha)
            pygame.draw.line(mask, color, (0, i), (SCREEN_WIDTH, i))
            pygame.draw.line(mask, color, (0, SCREEN_HEIGHT - 1 - i), (SCREEN_WIDTH, SCREEN_HEIGHT - 1 - i))
        return mask

    def _build_background(self):
        """Blurred + darkened background, or None if the image is missing."""
        image = load_cover_image(BACKGROUND_FILE, (SCREEN_WIDTH, SCREEN_HEIGHT))
        if image is None:
            return None
        background = image.copy()
        dark = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, DARKEN_ALPHA))
        background.blit(dark, (0, 0))
        return background

    # ----- screen -----

    def on_enter(self) -> None:
        self.time = 0.0
        if self.background is None:
            self.background = self._build_background()

    def on_back(self) -> None:
        self.manager.switch("title")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()
            return
        self.back_btn.handle_event(event)

    def update(self, dt: float) -> None:
        # The credits start just below the screen and leave just above it, in CREDITS_TIME seconds
        self.time = (self.time + min(dt, 0.1)) % CREDITS_TIME

    def draw(self, surface: pygame.Surface) -> None:
        if self.background:
            surface.blit(self.background, (0, 0))
        else:
            surface.fill(BG_COLOR)

        distance = SCREEN_HEIGHT + self.credits.get_height()
        top = SCREEN_HEIGHT - distance * (self.time / CREDITS_TIME)
        self.layer.fill((0, 0, 0, 0))
        self.layer.blit(self.credits, (0, int(top)))
        self.layer.blit(self.fade_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(self.layer, (0, 0))

        self.back_btn.draw(surface) 