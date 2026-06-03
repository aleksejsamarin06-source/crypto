import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional


class ActivityMonitor:
    """Low-overhead user activity monitor for auto-lock."""

    SENSITIVITY_INTERVALS = {
        "low": 5.0,
        "medium": 2.0,
        "high": 1.0,
    }

    def __init__(self, lock_callback: Callable, config: dict):
        self.lock_callback = lock_callback
        self.config = config
        self.last_activity = datetime.now(timezone.utc)
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

    def start_monitoring(self):
        with self.lock:
            if self.monitoring:
                return
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()

    def stop_monitoring(self):
        with self.lock:
            self.monitoring = False
            thread = self.monitor_thread
        if thread:
            thread.join(timeout=2.0)

    def record_activity(self):
        with self.lock:
            self.last_activity = datetime.now(timezone.utc)

    def update_config(self, config: dict):
        with self.lock:
            self.config.update(config)

    def get_idle_time(self) -> float:
        with self.lock:
            return (datetime.now(timezone.utc) - self.last_activity).total_seconds()

    def _monitor_loop(self):
        while True:
            with self.lock:
                if not self.monitoring:
                    return
                config = dict(self.config)
            timeout = int(config.get("auto_lock_timeout_seconds", 300))
            if config.get("auto_lock_enabled", True) and self.get_idle_time() >= timeout:
                self.lock_callback()
                self.record_activity()
            sensitivity = config.get("activity_sensitivity", "medium")
            time.sleep(self.SENSITIVITY_INTERVALS.get(sensitivity, 2.0))
