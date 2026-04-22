"""pytest configuration and shared fixtures.

Fixtures specific to a single service (scraper, GHL, DB) live alongside
the tests that use them. This file only holds truly cross-cutting config.
"""
import os

import pytest


def pytest_collection_modifyitems(config, items):
    # Skip @pytest.mark.live unless ENABLE_LIVE_TESTS=1 — live tests make
    # real HTTP calls to HCFL's public portal; opt-in only.
    if os.environ.get("ENABLE_LIVE_TESTS") == "1":
        return
    skip_live = pytest.mark.skip(reason="ENABLE_LIVE_TESTS=1 required")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
