import pytest

from tactical_game.ui import projection


@pytest.fixture(autouse=True)
def diamond_camera_between_tests():
    """Every test starts (and leaves the shared camera) in the diamond view."""
    projection.set_blend(0.0)
    yield
    projection.set_blend(0.0)
