"""Global pytest fixtures for flipped_energy tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.flipped_energy.const import DOMAIN

FIXTURES_PATH = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in tests."""
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mocked config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test User",
        unique_id="test-user",
        data={
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "secret",
        },
    )


@pytest.fixture
def load_fixture() -> callable:
    """Return a helper to load fixture file contents as text."""

    def _load(rel_path: str) -> str:
        return (FIXTURES_PATH / rel_path).read_text(encoding="utf-8")

    return _load
