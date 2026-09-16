from collections.abc import Iterator


def backoff_delays(
    *,
    attempts: int,
    base_delay: float = 5.0,
    max_delay: float = 60.0,
) -> Iterator[float]:
    """Yield capped exponential-backoff delays between connection attempts.

    `attempts` is the total number of connection attempts, so this yields
    at most `attempts - 1` delays.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    if base_delay <= 0 or max_delay <= 0:
        raise ValueError("delays must be positive")

    delay = min(base_delay, max_delay)
    for _ in range(attempts - 1):
        yield delay
        delay = min(delay * 2, max_delay)
