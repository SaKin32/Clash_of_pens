"""Screen base class and a manager that switches between screens."""

import pygame


class Screen:
    """Base class for every screen (title, mode select, match, ...)."""

    def __init__(self, manager: "ScreenManager"):
        self.manager = manager

    def on_enter(self) -> None:
        """Called each time this screen becomes active."""

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle a single pygame event."""

    def on_quit(self) -> None:
        """Called when the game is closing while this screen is active (save here)."""

    def update(self, dt: float) -> None:
        """Update logic. dt is the frame time in seconds."""

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the screen."""


class ScreenManager:
    """Keeps registered screens and tracks which one is active."""

    def __init__(self):
        self._screens = {}
        self.current = None
        self.running = True

    def register(self, name: str, screen: Screen) -> None:
        self._screens[name] = screen

    def get(self, name: str) -> Screen:
        return self._screens[name]

    def switch(self, name: str) -> None:
        self.current = self._screens[name]
        self.current.on_enter()

    def quit(self) -> None:
        if self.running and self.current is not None:
            self.current.on_quit()
        self.running = False