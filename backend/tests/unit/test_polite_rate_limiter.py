"""Unit tests for PoliteRateLimiter."""
import asyncio
import time

import pytest

from app.services.polite_rate_limiter import PoliteRateLimiter


class TestBaseDelay:
    async def test_first_request_no_wait(self):
        rl = PoliteRateLimiter(base_delay_s=0.1, jitter_fraction=0.0)
        t0 = time.monotonic()
        await rl.wait_before_request()
        elapsed = time.monotonic() - t0
        assert elapsed < 0.05, f"First request should not wait, took {elapsed:.3f}s"

    async def test_second_request_waits_base_delay(self):
        rl = PoliteRateLimiter(base_delay_s=0.1, jitter_fraction=0.0, max_per_minute=10000)
        await rl.wait_before_request()
        t0 = time.monotonic()
        await rl.wait_before_request()
        elapsed = time.monotonic() - t0
        assert elapsed >= 0.09, f"Second request should wait ~0.1s, took {elapsed:.3f}s"
        assert elapsed < 0.2, f"Second request took too long: {elapsed:.3f}s"

    async def test_jitter_within_bounds(self):
        rl = PoliteRateLimiter(base_delay_s=0.2, jitter_fraction=0.2, max_per_minute=10000)
        await rl.wait_before_request()
        # Sample a bunch of delays
        delays = []
        for _ in range(5):
            t0 = time.monotonic()
            await rl.wait_before_request()
            delays.append(time.monotonic() - t0)
        # All delays should be within [base*(1-jitter), base*(1+jitter)] = [0.16, 0.24]
        for d in delays:
            assert 0.14 <= d <= 0.28, f"Delay {d:.3f} out of expected range"


class TestWindowCap:
    async def test_respects_per_minute_cap(self):
        # Tight cap so we hit it quickly in tests.
        rl = PoliteRateLimiter(
            base_delay_s=0.0,
            jitter_fraction=0.0,
            max_per_minute=3,
            window_seconds=0.5,  # 500ms window
        )
        # Three requests fast
        await rl.wait_before_request()
        await rl.wait_before_request()
        await rl.wait_before_request()
        # Fourth should pause until the first ages out
        t0 = time.monotonic()
        await rl.wait_before_request()
        elapsed = time.monotonic() - t0
        assert elapsed >= 0.4, f"Fourth request should wait ~500ms, took {elapsed:.3f}s"
        # Stats reflect the window pause
        stats = rl.stats()
        assert stats["total_window_pauses"] >= 1

    async def test_stats_tracked(self):
        rl = PoliteRateLimiter(base_delay_s=0.0, jitter_fraction=0.0)
        for _ in range(3):
            await rl.wait_before_request()
        assert rl.stats()["total_waits"] == 3


class TestBackoff:
    async def test_handle_429_exponential(self, monkeypatch):
        # Deterministic: monkeypatch asyncio.sleep so we assert on the
        # requested delay rather than wall-clock (which is flaky under
        # coverage overhead).
        observed: list[float] = []

        async def fake_sleep(delay):
            observed.append(delay)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        rl = PoliteRateLimiter(base_delay_s=0.01)
        await rl.handle_429_backoff(attempt=1)
        await rl.handle_429_backoff(attempt=3)
        assert len(observed) == 2
        # Attempt 3 delay should be substantially greater than attempt 1
        assert observed[1] > observed[0]
        assert rl.stats()["total_429_backoffs"] == 2

    async def test_backoff_is_capped(self, monkeypatch):
        # Don't actually wait 60s in a unit test. Verify cap math via
        # monkeypatched asyncio.sleep that records the requested delay.
        observed: list[float] = []

        async def fake_sleep(delay):
            observed.append(delay)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        rl = PoliteRateLimiter(base_delay_s=5.0)
        await rl.handle_429_backoff(attempt=10)
        # 2**10 * 5 = 5120, capped at 60 + up to 1s jitter
        assert observed, "asyncio.sleep not called"
        assert observed[-1] <= 61.0, f"Requested delay exceeded cap: {observed[-1]}"
