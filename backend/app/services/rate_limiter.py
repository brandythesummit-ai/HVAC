"""
Rate limiter for Accela API based on response headers.

Accela communicates rate limits dynamically via headers:
- x-ratelimit-limit: Max calls allowed per hour
- x-ratelimit-remaining: Calls remaining in current window
- x-ratelimit-reset: Unix timestamp when window resets

This class tracks the rate limit state and provides methods to:
1. Check if we should pause before next request
2. Calculate appropriate delay based on remaining quota
3. Handle 429 responses with wait-until-reset logic
"""

import time
import asyncio
import random
import logging
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class AccelaRateLimiter:
    """Tracks and enforces Accela API rate limits based on response headers."""

    def __init__(
        self,
        threshold: float = 0.15,  # Pause when < 15% remaining (85% threshold)
        fallback_delay_pagination: float = 0.5,  # Fallback if no headers
        fallback_delay_enrichment: float = 0.1,
    ):
        """
        Initialize rate limiter.

        Args:
            threshold: Fraction of limit remaining before we pause (0.15 = 15%)
            fallback_delay_pagination: Delay between pagination requests if no headers
            fallback_delay_enrichment: Delay between enrichment requests if no headers
        """
        self.threshold = threshold
        self.fallback_delay_pagination = fallback_delay_pagination
        self.fallback_delay_enrichment = fallback_delay_enrichment

        # Rate limit state (updated from response headers)
        self.limit: Optional[int] = None  # Max calls per hour
        self.remaining: Optional[int] = None  # Calls left in window
        self.reset: Optional[int] = None  # Unix timestamp when window resets
        self.last_updated: Optional[float] = None  # When we last saw headers

        # Stats for monitoring
        self.total_429_count = 0
        self.total_pauses = 0
        self.last_429_time: Optional[float] = None

    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """
        Update rate limit state from response headers.

        Args:
            headers: HTTP response headers dict
        """
        limit_str = headers.get("x-ratelimit-limit")
        remaining_str = headers.get("x-ratelimit-remaining")
        reset_str = headers.get("x-ratelimit-reset")

        if limit_str:
            try:
                self.limit = int(limit_str)
            except (ValueError, TypeError):
                pass

        if remaining_str:
            try:
                self.remaining = int(remaining_str)
            except (ValueError, TypeError):
                pass

        if reset_str:
            try:
                self.reset = int(reset_str)
            except (ValueError, TypeError):
                pass

        if any([limit_str, remaining_str, reset_str]):
            self.last_updated = time.time()
            logger.debug(
                f"[RATE LIMIT] Updated: {self.remaining}/{self.limit} remaining, "
                f"resets at {datetime.utcfromtimestamp(self.reset).isoformat()}Z"
            )

    def should_pause(self) -> bool:
        """
        Check if we should pause before making next request.

        Returns:
            True if we're approaching rate limit and should delay
        """
        if self.limit is None or self.remaining is None:
            # No rate limit info yet, don't pause
            return False

        # Calculate percentage remaining
        pct_remaining = self.remaining / self.limit

        if pct_remaining < self.threshold:
            logger.warning(
                f"[RATE LIMIT] Approaching limit: {self.remaining}/{self.limit} "
                f"({pct_remaining:.1%} remaining) - pausing before next request"
            )
            return True

        return False

    def get_delay_until_safe(self) -> float:
        """
        Calculate how long to wait before next request is safe.

        Returns:
            Seconds to wait (with small jitter added)
        """
        if self.limit is None or self.remaining is None or self.reset is None:
            # No header data, use fallback delay
            return self.fallback_delay_pagination

        now = time.time()
        seconds_until_reset = max(0, self.reset - now)

        if self.remaining == 0:
            # Completely out of quota, wait until reset
            delay = seconds_until_reset + random.uniform(0.1, 0.5)
            logger.warning(
                f"[RATE LIMIT] Quota exhausted, waiting {delay:.1f}s until reset"
            )
            return delay

        # Calculate safe pacing: spread remaining calls over time until reset
        # Reserve some calls for other operations (80% of remaining)
        safe_remaining = int(self.remaining * 0.8)

        if safe_remaining > 0 and seconds_until_reset > 0:
            # Pace calls evenly over remaining time
            delay = seconds_until_reset / safe_remaining
            # Add small jitter to avoid thundering herd
            jitter = random.uniform(0, 0.1 * delay)
            total_delay = delay + jitter

            logger.debug(
                f"[RATE LIMIT] Pacing delay: {total_delay:.2f}s "
                f"({safe_remaining} calls over {seconds_until_reset:.0f}s)"
            )
            return total_delay

        # Default small delay if calculation doesn't work
        return random.uniform(0.1, 0.3)

    async def wait_if_needed(self, request_type: str = "general") -> None:
        """
        Wait if we're approaching rate limit.

        Args:
            request_type: Type of request ("pagination", "enrichment", "general")
        """
        if self.should_pause():
            delay = self.get_delay_until_safe()
            self.total_pauses += 1
            logger.info(
                f"[RATE LIMIT] Pausing {delay:.2f}s before {request_type} request "
                f"(pause #{self.total_pauses})"
            )
            await asyncio.sleep(delay)

    async def handle_429(self, response_headers: Dict[str, str]) -> None:
        """
        Handle 429 Too Many Requests response.

        Args:
            response_headers: Headers from 429 response
        """
        self.total_429_count += 1
        self.last_429_time = time.time()

        # Update state from headers
        self.update_from_headers(response_headers)

        # Check for Retry-After header (takes precedence)
        retry_after_str = response_headers.get("retry-after")
        if retry_after_str:
            try:
                retry_after = float(retry_after_str)
                logger.warning(
                    f"[RATE LIMIT] 429 response with Retry-After: {retry_after}s"
                )
                await asyncio.sleep(retry_after + random.uniform(0.1, 0.5))
                return
            except (ValueError, TypeError):
                pass

        # Fall back to x-ratelimit-reset
        if self.reset:
            now = time.time()
            wait_time = max(0, self.reset - now) + random.uniform(0.5, 2.0)
            logger.warning(
                f"[RATE LIMIT] 429 response, waiting {wait_time:.1f}s until reset "
                f"(429 #{self.total_429_count})"
            )
            await asyncio.sleep(wait_time)
        else:
            # No timing info, use exponential backoff
            backoff = min(2 ** self.total_429_count, 60)  # Max 60s
            jitter = random.uniform(0, 0.5 * backoff)
            total_wait = backoff + jitter
            logger.warning(
                f"[RATE LIMIT] 429 response with no headers, "
                f"exponential backoff: {total_wait:.1f}s"
            )
            await asyncio.sleep(total_wait)

    def get_fallback_delay(self, request_type: str) -> float:
        """
        Get fallback delay when no rate limit headers available.

        Args:
            request_type: "pagination" or "enrichment"

        Returns:
            Delay in seconds
        """
        if request_type == "pagination":
            return self.fallback_delay_pagination
        elif request_type == "enrichment":
            return self.fallback_delay_enrichment
        else:
            return 0.1

    def get_stats(self) -> Dict:
        """Get current rate limiter statistics."""
        return {
            "limit": self.limit,
            "remaining": self.remaining,
            "reset": self.reset,
            "reset_iso": (
                datetime.utcfromtimestamp(self.reset).isoformat() + "Z"
                if self.reset else None
            ),
            "total_429s": self.total_429_count,
            "total_pauses": self.total_pauses,
            "last_429_time": self.last_429_time,
            "last_updated": self.last_updated,
        }
