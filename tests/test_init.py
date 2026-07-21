"""Tests for flipped_energy integration setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState

from custom_components.flipped_energy.api import IntegrationBlueprintApiClientError

pytestmark = pytest.mark.asyncio


async def test_setup_entry_creates_entities(hass, mock_config_entry) -> None:
    """Test that setting up an entry creates integration entities."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.flipped_energy.api.IntegrationBlueprintApiClient.async_get_data",
        new=AsyncMock(return_value={"title": "foo", "body": "hello world"}),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    sensor_state = hass.states.get("sensor.integration_sensor")
    assert sensor_state is not None
    assert sensor_state.state == "hello world"

    binary_sensor_state = hass.states.get("binary_sensor.flipped_energy_binary_sensor")
    assert binary_sensor_state is not None
    assert binary_sensor_state.state == "on"

    switch_state = hass.states.get("switch.integration_switch")
    assert switch_state is not None
    assert switch_state.state == "on"


async def test_unload_entry(hass, mock_config_entry) -> None:
    """Test unloading a config entry."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.flipped_energy.api.IntegrationBlueprintApiClient.async_get_data",
        new=AsyncMock(return_value={"title": "foo", "body": "hello world"}),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    sensor_state = hass.states.get("sensor.integration_sensor")
    assert sensor_state is None or sensor_state.state == "unavailable"


async def test_setup_entry_not_ready_on_api_error(hass, mock_config_entry) -> None:
    """Test setup retries when coordinator initial refresh fails."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.flipped_energy.api.IntegrationBlueprintApiClient.async_get_data",
        new=AsyncMock(side_effect=IntegrationBlueprintApiClientError("boom")),
    ):
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
    assert hass.states.get("sensor.integration_sensor") is None
