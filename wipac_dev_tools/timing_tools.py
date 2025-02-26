"""Utilities for timers, interval trackers, etc."""

import asyncio
import itertools
import logging
import time
from typing import Union


class IntervalTimer:
    """A utility class to track time intervals.

    This class allows tracking of elapsed time between actions and provides
    mechanisms to wait until a specified time interval has passed.
    """

    def __init__(
        self,
        seconds: float,
        logger: Union[logging.Logger, str, None],
    ) -> None:
        self.seconds = seconds
        self._last_time = time.monotonic()

        if not logger:
            self.logger = None  # no logging
        elif isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            self.logger = logging.getLogger(logger)

    def fastforward(self):
        """Force the interval timer to consider the current interval as already elapsed.

        This resets the internal timer to a state where the next call to `has_interval_elapsed`
        will immediately return `True`, as if the interval has already passed.
        """
        self._last_time = float("-inf")

    @staticmethod
    def _is_nth(i: int, nth: int) -> bool:
        return nth > 0 and i % nth == 0

    async def wait_until_interval(
        self,
        frequency: float = 1.0,
        log_every_nth: int = 60,
    ) -> None:
        """Wait asynchronously until the specified interval has elapsed.

        This method checks the elapsed time every `frequency` seconds,
        allowing cooperative multitasking during the wait.
        """
        if self.logger:
            self.logger.debug(
                f"Waiting for {self.seconds}s interval before proceeding..."
            )

        for i in itertools.count():
            if self.has_interval_elapsed():
                return
            if self.logger and self._is_nth(i, log_every_nth):
                self.logger.debug(f"Still waiting for {self.seconds}s interval...")
            await asyncio.sleep(frequency)

    def wait_until_interval_sync(
        self,
        frequency: float = 1.0,
        log_every_nth: int = 60,
    ) -> None:
        """Wait until the specified interval has elapsed.

        This method checks the elapsed time every `frequency` seconds,
        blocking until the interval has elapsed.
        """
        if self.logger:
            self.logger.debug(
                f"Waiting for {self.seconds}s interval before proceeding..."
            )

        for i in itertools.count():
            if self.has_interval_elapsed():
                return
            if self.logger and self._is_nth(i, log_every_nth):
                self.logger.debug(f"Still waiting for {self.seconds}s interval...")
            time.sleep(frequency)

    def has_interval_elapsed(self) -> bool:
        """Check if the specified time interval has elapsed since the last expiration.

        If the interval has elapsed, the internal timer is reset to the current time.
        """
        diff = time.monotonic() - self._last_time
        if diff >= self.seconds:
            self._last_time = time.monotonic()
            return True
        return False
