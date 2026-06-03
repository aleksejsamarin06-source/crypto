import threading
from typing import Callable, List

from src.core.events import event_system


class PanicMode:
    """Emergency response system."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.activated = False
        self.response_handlers: List[Callable[[str], None]] = []
        self.lock = threading.Lock()

    def register_handler(self, handler: Callable[[str], None]):
        self.response_handlers.append(handler)

    def activate(self, method: str = "manual"):
        with self.lock:
            if self.activated:
                return
            self.activated = True

        for handler in list(self.response_handlers):
            try:
                handler(method)
            except Exception as exc:
                print(f"Panic handler failed: {exc}")

        event_system.publish("panic_mode_activated", {"method": method})

    def reset(self):
        with self.lock:
            self.activated = False
