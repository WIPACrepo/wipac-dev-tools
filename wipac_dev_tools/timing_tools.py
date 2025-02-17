"""Utilities for timers, interval trackers, etc."""

import asyncio
import logging
import time


class IntervalTimer:
    """A utility class to track time intervals.

    This class allows tracking of elapsed time between actions and provides
    mechanisms to wait until a specified time interval has passed.
    """

    def __init__(self, seconds: float, logger: logging.Logger | str) -> None:
        self.seconds = seconds
        self._last_time = time.monotonic()

        if isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            self.logger = logging.getLogger(logger)

    def fastforward(self):
        """Reset the timer so that the next call to `has_interval_elapsed` will return True.

        This effectively skips the current interval and forces the timer to indicate
        that the interval has elapsed on the next check.
        """
        self._last_time = float("-inf")

    async def wait_until_interval(self, frequency: float = 1.0) -> None:
        """Wait asynchronously until the specified interval has elapsed.

        This method checks the elapsed time every `frequency` seconds,
        allowing cooperative multitasking during the wait.
        """
        self.logger.debug(
            f"Waiting until {self.seconds}s has elapsed since the last iteration..."
        )
        while not self.has_interval_elapsed():
            await asyncio.sleep(frequency)

    def wait_until_interval_sync(self, frequency: float = 1.0) -> None:
        """Wait until the specified interval has elapsed.

        This method checks the elapsed time every `frequency` seconds,
        blocking until the interval has elapsed.
        """
        self.logger.debug(
            f"Waiting until {self.seconds}s has elapsed since the last iteration..."
        )
        while not self.has_interval_elapsed():
            time.sleep(frequency)

    def has_interval_elapsed(self) -> bool:
        """Check if the specified time interval has elapsed since the last expiration.

        If the interval has elapsed, the internal timer is reset to the current time.
        """
        diff = time.monotonic() - self._last_time
        if diff >= self.seconds:
            self._last_time = time.monotonic()
            self.logger.debug(
                f"At least {self.seconds}s have elapsed (actually {diff}s)."
            )
            return True
        return False
