# this_file: src/vexy_localizzy/sourcefix/progress.py
"""Flushed CLI progress; library calls remain silent."""

import sys
import threading
import time
from contextvars import ContextVar

_current: ContextVar["Progress | None"] = ContextVar("sourcefix_progress", default=None)


class Progress:
    """Report the current stage periodically and track the write boundary."""

    def __init__(self, interval: float = 5.0) -> None:
        self.interval = interval
        self.started = time.monotonic()
        self.stage = "Starting"
        self.state = "staging"
        self.stop = threading.Event()

    def write(self, message: str) -> None:
        print(
            f"[{time.monotonic() - self.started:6.1f}s] {message}",
            file=sys.stderr,
            flush=True,
        )

    def _heartbeat(self) -> None:
        while not self.stop.wait(self.interval):
            self.write(f"{self.stage} — still working")

    def __enter__(self) -> "Progress":
        self.token = _current.set(self)
        self.thread = threading.Thread(target=self._heartbeat, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        self.stop.set()
        self.thread.join()
        _current.reset(self.token)
        if exc_type is KeyboardInterrupt:
            status = {
                "staging": "No source or catalog files were changed.",
                "restored": "Original files were restored.",
                "committed": "Changes were already written. Check the working tree before rerunning.",
            }.get(
                self.state,
                "Check the working tree: writing or restoration was interrupted.",
            )
            self.write(f"Interrupted. {status}")
            raise SystemExit(130) from None
        return False


def report(message: str, *, state: str | None = None) -> None:
    """Publish a stage only while a CLI progress context is active."""
    current = _current.get()
    if current is not None:
        current.stage = message
        if state is not None:
            current.state = state
        current.write(message)
