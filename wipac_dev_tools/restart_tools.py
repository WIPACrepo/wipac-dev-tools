"""Function decorators to solve basic problems."""

import asyncio
import functools
import logging
from typing import Optional


def restart_on_failure(
    display_name: str,
    delay_seconds: int,
    logger: Optional[logging.Logger] = None,
    initial_delay: int = 0,
):
    """Decorator to restart an async function on failure after delay.

    Waits hopefully long enough that any transient errors are resolved;
    e.g. a mongo pod failure and restart (otherwise, tries again).
    """

    def decorator(func):

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):

            if logger:
                logger.info(f"Started {display_name}.")

            await asyncio.sleep(initial_delay)

            while True:

                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if logger:
                        logger.exception(e)
                        logger.error(
                            f"above error stopped {display_name}, "
                            f"resuming in {delay_seconds} seconds..."
                        )

                await asyncio.sleep(delay_seconds)
                if logger:
                    logger.info(f"Restarted {display_name}.")

        return wrapper

    return decorator
