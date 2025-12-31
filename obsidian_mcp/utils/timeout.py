import signal
import contextlib
from typing import Generator

class TimeoutError(Exception):
    pass

@contextlib.contextmanager
def time_limit(seconds: int) -> Generator[None, None, None]:
    """
    Context manager to enforce a time limit on a block of code using SIGALRM.
    Note: This only works on Unix-based systems (Linux/macOS).
    """
    def signal_handler(signum, frame):
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
