"""
Timeout utilities with cross-platform support.

Uses SIGALRM on Unix and threading on Windows.
"""

import contextlib
import sys
import threading
from typing import Any, Generator


class TimeoutError(Exception):
    """Raised when an operation times out."""

    pass


if sys.platform != "win32":
    import signal

    @contextlib.contextmanager
    def time_limit(seconds: int) -> Generator[None, None, None]:
        """
        Context manager to enforce a time limit on a block of code using SIGALRM.
        Note: This only works on Unix-based systems (Linux/macOS).
        """

        def signal_handler(signum: int, frame: Any) -> None:
            raise TimeoutError(f"Operation timed out after {seconds} seconds")

        # Register the signal function handler
        original_handler = signal.signal(signal.SIGALRM, signal_handler)

        # Set the alarm
        signal.alarm(seconds)

        try:
            yield
        finally:
            # Cancel the alarm
            signal.alarm(0)
            # Restore original handler
            signal.signal(signal.SIGALRM, original_handler)

else:
    # Windows fallback using threading (less reliable for blocking operations)
    @contextlib.contextmanager
    def time_limit(seconds: int) -> Generator[None, None, None]:
        """
        Context manager to enforce a time limit using threading.
        Note: This is a fallback for Windows and may not interrupt blocking I/O.
        """
        timed_out = False

        def timeout_handler() -> None:
            nonlocal timed_out
            timed_out = True

        timer = threading.Timer(seconds, timeout_handler)
        timer.start()

        try:
            yield
            if timed_out:
                raise TimeoutError(f"Operation timed out after {seconds} seconds")
        finally:
            timer.cancel()
