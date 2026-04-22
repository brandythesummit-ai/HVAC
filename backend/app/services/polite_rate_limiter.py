"""Polite rate limiter for the HCFL legacy scraper.

Unlike the Accela rate limiter (`rate_limiter.py`), HCFL's legacy
PermitReports tool doesn't publish rate-limit headers. We self-pace
with a fixed jittered delay and a sliding per-minute window cap.

The goal is not to hit a stated limit but to not be rude to a
government website that has no incentive to serve us. 400-600ms
between calls at ~60 req/min sits well below anything that would
raise flags, and still yields a manageable wall-clock time
(~2 hours for a full 14K-street backfill).
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import deque
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class PoliteRateLimiter:
    # Base delay between requests in seconds (before jitter).
    base_delay_s: float = 0.5
    # Fraction of base_delay to randomize by, ±. 0.2 = ±20% = 400-600ms.
    jitter_fraction: float = 0.2
    # Max requests per rolling 60-second window.
    max_per_minute: int = 60
    # Time window to enforce the max_per_minute limit over, in seconds.
    window_seconds: float = 60.0

    _last_request_at: float = 0.0
    _recent_request_times: deque[float] = field(default_factory=deque)
    _total_waits: int = 0
    _total_window_pauses: int = 0
    _total_429_backoffs: int = 0

    async def wait_before_request(self) -> None:
        # Enforce base jittered delay + sliding-window cap.
        now = time.monotonic()

        # Step 1: trim old window entries
        while self._recent_request_times and self._recent_request_times[0] < now - self.window_seconds:
            self._recent_request_times.popleft()

        # Step 2: if we're at the window cap, pause until the oldest expires.
        if len(self._recent_request_times) >= self.max_per_minute:
            oldest = self._recent_request_times[0]
            wait_until = oldest + self.window_seconds
            remaining = wait_until - now
            if remaining > 0:
                log.warning(
                    "[POLITE] Hit per-minute cap (%d/%d), pausing %.2fs",
                    len(self._recent_request_times),
                    self.max_per_minute,
                    remaining,
                )
                self._total_window_pauses += 1
                await asyncio.sleep(remaining)
                now = time.monotonic()

        # Step 3: ensure minimum delay since last request.
        if self._last_request_at:
            jitter = random.uniform(-self.jitter_fraction, self.jitter_fraction)
            target_delay = self.base_delay_s * (1 + jitter)
            since_last = now - self._last_request_at
            remaining = target_delay - since_last
            if remaining > 0:
                await asyncio.sleep(remaining)
                now = time.monotonic()

        self._last_request_at = now
        self._recent_request_times.append(now)
        self._total_waits += 1

    async def handle_429_backoff(self, attempt: int = 1) -> None:
        # Exponential backoff on rate-limit / server-error responses.
        delay = min(60.0, (2 ** attempt) * self.base_delay_s + random.uniform(0, 1))
        log.warning("[POLITE] Backoff attempt %d, sleeping %.2fs", attempt, delay)
        self._total_429_backoffs += 1
        await asyncio.sleep(delay)

    def stats(self) -> dict:
        return {
            "total_waits": self._total_waits,
            "total_window_pauses": self._total_window_pauses,
            "total_429_backoffs": self._total_429_backoffs,
            "current_window_count": len(self._recent_request_times),
        }
