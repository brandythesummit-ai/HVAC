"""Minimal smoke test proving the pytest harness is wired correctly.

Replaced as real tests are added in subsequent milestones (M5, M7, M12, etc.).
"""


def test_pytest_can_run():
    assert 1 + 1 == 2


async def test_pytest_asyncio_auto_mode_runs_async_tests():
    # No @pytest.mark.asyncio — pytest.ini sets asyncio_mode = auto,
    # so bare async def tests must execute. If pytest-asyncio is
    # broken or uninstalled, pytest will collect this and fail.
    assert 1 + 1 == 2
