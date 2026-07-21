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
        new=AsyncMock(
            return_value={
                "plan_name": "Flipped Saver",
                "amount_due_aud": 123.45,
                "usage_today_kwh": 8.9,
                "usage_period_start": "2026-07-20T00:00:00",
                "usage_period_end": "2026-07-20",
                "total_usage_kwh": 321.0,
                "total_feedin_kwh": 41.5,
                "import_rate_cents_kwh": 29.5,
                "feedin_rate_cents_kwh": 8.0,
                "auth_ok": True,
                "data_fresh": True,
                "last_successful_scrape": "2026-07-21T00:00:00+00:00",
            }
        ),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    sensor_state = hass.states.get("sensor.flipped_energy_usage")
    assert sensor_state is not None
    assert sensor_state.state == "8.9"
    assert sensor_state.attributes.get("usage_period_start") == "2026-07-20T00:00:00"
    assert sensor_state.attributes.get("usage_period_end") == "2026-07-20"

    usage_period_state = hass.states.get("sensor.flipped_energy_usage_period_end")
    assert usage_period_state is not None
    assert usage_period_state.state == "2026-07-20"

    plan_state = hass.states.get("sensor.flipped_energy_plan_name")
    assert plan_state is not None
    assert plan_state.state == "Flipped Saver"

    binary_sensor_state = hass.states.get("binary_sensor.flipped_energy_authenticated")
    assert binary_sensor_state is not None
    assert binary_sensor_state.state == "on"

    amount_due_state = hass.states.get("sensor.flipped_energy_amount_due")
    assert amount_due_state is not None
    assert amount_due_state.state == "123.45"


async def test_unload_entry(hass, mock_config_entry) -> None:
    """Test unloading a config entry."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.flipped_energy.api.IntegrationBlueprintApiClient.async_get_data",
        new=AsyncMock(
            return_value={
                "plan_name": "Flipped Saver",
                "auth_ok": True,
                "data_fresh": True,
            }
        ),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    sensor_state = hass.states.get("sensor.flipped_energy_usage")
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
    assert hass.states.get("sensor.flipped_energy_plan_name") is None
