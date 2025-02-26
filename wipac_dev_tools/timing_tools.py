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
        """Reset the timer so that the next call to `has_interval_elapsed` will return True.

        This effectively skips the current interval and forces the timer to indicate
        that the interval has elapsed on the next check.
        """
        self._last_time = float("-inf")

    @staticmethod
    def _is_every_n(i: int, log_every_n: int) -> bool:
        if log_every_n < 1:
            return False
        else:
            return i % log_every_n == 0

    async def wait_until_interval(
        self,
        frequency: float = 1.0,
        log_every_n: int = 60,
    ) -> None:
        """Wait asynchronously until the specified interval has elapsed.

        This method checks the elapsed time every `frequency` seconds,
        allowing cooperative multitasking during the wait.
        """
        if self.logger:
            self.logger.debug(
                f"Waiting until {self.seconds}s has elapsed since the last iteration..."
            )
        for i in itertools.count():
            if not self.has_interval_elapsed(do_log=self._is_every_n(i, log_every_n)):
                return
            await asyncio.sleep(frequency)

    def wait_until_interval_sync(
        self,
        frequency: float = 1.0,
        log_every_n: int = 60,
    ) -> None:
        """Wait until the specified interval has elapsed.

        This method checks the elapsed time every `frequency` seconds,
        blocking until the interval has elapsed.
        """
        if self.logger:
            self.logger.debug(
                f"Waiting until {self.seconds}s has elapsed since the last iteration..."
            )
        for i in itertools.count():
            if not self.has_interval_elapsed(do_log=self._is_every_n(i, log_every_n)):
                return
            time.sleep(frequency)

    def has_interval_elapsed(self, do_log: bool = False) -> bool:
        """Check if the specified time interval has elapsed since the last expiration.

        If the interval has elapsed, the internal timer is reset to the current time.
        """
        diff = time.monotonic() - self._last_time
        if diff >= self.seconds:
            self._last_time = time.monotonic()
            if self.logger:
                self.logger.debug(
                    f"At least {self.seconds}s have elapsed (actually {diff}s)."
                )
            return True
        return False
