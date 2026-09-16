import pytest

from unified.reliability import backoff_delays


def test_exponential_backoff_is_capped():
    assert list(
        backoff_delays(attempts=6, base_delay=5, max_delay=20)
    ) == [5, 10, 20, 20, 20]


def test_single_attempt_has_no_wait():
    assert list(backoff_delays(attempts=1)) == []


def test_invalid_attempt_count_is_rejected():
    with pytest.raises(ValueError):
        list(backoff_delays(attempts=0))
