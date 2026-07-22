"""Tests for flipped_energy integration setup."""

from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState

from custom_components.flipped_energy.api import IntegrationBlueprintApiClientError
from custom_components.flipped_energy.const import (
    CONF_ENABLE_PLAN_PAGE,
    CONF_INCLUDE_GST,
    CONF_REFRESH_INTERVAL_MINUTES,
)

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
                "usage_feedin_yesterday_kwh": 1.2,
                "usage_period_start": "2026-07-20T00:00:00",
                "usage_period_end": "2026-07-20",
                "total_usage_kwh": 321.0,
                "total_feedin_kwh": 41.5,
                "import_rate_cents_kwh": 29.5,
                "feedin_rate_cents_kwh": 8.0,
                "import_rate_blocks": [
                    {
                        "name": "Day",
                        "start_minutes": 540,
                        "end_minutes": 1020,
                        "start_time": "09:00",
                        "end_time": "17:00",
                        "rate_cents_kwh": 9.93,
                    }
                ],
                "feedin_rate_blocks": [
                    {
                        "name": "Solar Feed In Tariff",
                        "start_minutes": 0,
                        "end_minutes": 0,
                        "start_time": "00:00",
                        "end_time": "00:00",
                        "rate_cents_kwh": 2.0,
                    }
                ],
                "supply_charge_daily_cents": 110.0,
                "supply_charge_daily_incl_gst_cents": 121.0,
                "auth_ok": True,
                "data_fresh": True,
                "last_successful_update": "2026-07-21T00:00:00+00:00",
            }
        ),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    sensor_state = hass.states.get("sensor.flipped_energy_usage_yesterday")
    assert sensor_state is not None
    assert sensor_state.state == "8.9"
    assert sensor_state.attributes.get("usage_period_start") == "2026-07-20T00:00:00"
    assert sensor_state.attributes.get("usage_period_end") == "2026-07-20"

    feedin_yesterday_state = hass.states.get("sensor.flipped_energy_feedin_yesterday")
    assert feedin_yesterday_state is not None
    assert feedin_yesterday_state.state == "1.2"

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

    import_rate_state = hass.states.get("sensor.flipped_energy_import_rate")
    assert import_rate_state is not None
    assert import_rate_state.attributes.get("gst_included") is True
    assert len(import_rate_state.attributes.get("import_rate_blocks", [])) == 1

    import_tou_state = hass.states.get("sensor.flipped_energy_import_tou_blocks")
    assert import_tou_state is not None
    assert import_tou_state.state == "1"

    feedin_tou_state = hass.states.get("sensor.flipped_energy_feed_in_tou_blocks")
    assert feedin_tou_state is not None
    assert feedin_tou_state.state == "1"

    import_schedule_state = hass.states.get("sensor.flipped_energy_import_tou_schedule")
    assert import_schedule_state is not None
    assert "09:00-17:00" in import_schedule_state.state

    feedin_schedule_state = hass.states.get(
        "sensor.flipped_energy_feed_in_tou_schedule"
    )
    assert feedin_schedule_state is not None
    assert "00:00-00:00" in feedin_schedule_state.state

    supply_state = hass.states.get("sensor.flipped_energy_supply_charge_daily")
    assert supply_state is not None
    assert supply_state.state == "121.0"
    assert supply_state.attributes.get("gst_included") is True

    supply_incl_state = hass.states.get(
        "sensor.flipped_energy_supply_charge_daily_incl_gst"
    )
    assert supply_incl_state is None


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

    sensor_state = hass.states.get("sensor.flipped_energy_usage_yesterday")
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


async def test_setup_entry_include_gst_option_adjusts_dynamic_values(
    hass, mock_config_entry
) -> None:
    """Test Include GST option toggles dynamic tariff/supply sensor values."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={"include_gst": True},
    )

    with patch(
        "custom_components.flipped_energy.api.IntegrationBlueprintApiClient.async_get_data",
        new=AsyncMock(
            return_value={
                "plan_name": "Flipped Saver",
                "amount_due_aud": 123.45,
                "usage_today_kwh": 8.9,
                "usage_feedin_yesterday_kwh": 1.2,
                "usage_period_start": "2026-07-20T00:00:00",
                "usage_period_end": "2026-07-20",
                "total_usage_kwh": 321.0,
                "total_feedin_kwh": 41.5,
                "import_rate_cents_kwh": 10.0,
                "feedin_rate_cents_kwh": 2.0,
                "import_rate_blocks": [
                    {
                        "name": "Day",
                        "start_minutes": 540,
                        "end_minutes": 1020,
                        "start_time": "09:00",
                        "end_time": "17:00",
                        "rate_cents_kwh": 10.0,
                    }
                ],
                "feedin_rate_blocks": [
                    {
                        "name": "Solar Feed In Tariff",
                        "start_minutes": 0,
                        "end_minutes": 0,
                        "start_time": "00:00",
                        "end_time": "00:00",
                        "rate_cents_kwh": 2.0,
                    }
                ],
                "supply_charge_daily_cents": 110.0,
                "supply_charge_daily_incl_gst_cents": 121.0,
                "auth_ok": True,
                "data_fresh": True,
                "last_successful_update": "2026-07-21T00:00:00+00:00",
            }
        ),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    import_rate = hass.states.get("sensor.flipped_energy_import_rate")
    assert import_rate is not None
    assert import_rate.state == "11.0"
    assert import_rate.attributes.get("gst_included") is True

    supply_state = hass.states.get("sensor.flipped_energy_supply_charge_daily")
    assert supply_state is not None
    assert supply_state.state == "121.0"
    assert supply_state.attributes.get("gst_included") is True


async def test_current_import_tariff_shows_when_refresh_is_current(
    hass, mock_config_entry
) -> None:
    """Test current import tariff sensor exposes value when data is fresh."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={CONF_INCLUDE_GST: False},
    )
    now = dt.datetime(2026, 7, 22, 18, 0, tzinfo=dt.UTC)

    with (
        patch(
            "custom_components.flipped_energy.api.IntegrationBlueprintApiClient.async_get_data",
            new=AsyncMock(
                return_value={
                    "plan_name": "Flipped Saver",
                    "amount_due_aud": 10.0,
                    "usage_today_kwh": 1.0,
                    "usage_feedin_yesterday_kwh": 0.5,
                    "usage_period_end": "2026-07-22",
                    "total_usage_kwh": 2.0,
                    "total_feedin_kwh": 0.5,
                    "import_rate_cents_kwh": 20.0,
                    "feedin_rate_cents_kwh": 2.0,
                    "import_rate_blocks": [
                        {
                            "name": "Day",
                            "start_minutes": 540,
                            "end_minutes": 1020,
                            "start_time": "09:00",
                            "end_time": "17:00",
                            "rate_cents_kwh": 9.93,
                        },
                        {
                            "name": "Evening",
                            "start_minutes": 1020,
                            "end_minutes": 1260,
                            "start_time": "17:00",
                            "end_time": "21:00",
                            "rate_cents_kwh": 57.62,
                        },
                    ],
                    "feedin_rate_blocks": [],
                    "last_successful_update": "2026-07-22T17:10:00+00:00",
                    "auth_ok": True,
                    "data_fresh": True,
                }
            ),
        ),
        patch(
            "custom_components.flipped_energy.sensor.dt_util.now",
            return_value=now,
        ),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.flipped_energy_current_import_tariff")
    assert state is not None
    assert state.state == "57.62"
    assert state.attributes.get("is_stale") is False
    assert state.attributes.get("valid_from") == "2026-07-22T17:00:00+00:00"
    assert state.attributes.get("valid_to") == "2026-07-22T21:00:00+00:00"


async def test_current_import_tariff_hides_when_boundary_is_stale(
    hass, mock_config_entry
) -> None:
    """Test current import tariff goes unknown if not refreshed after changeover."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={CONF_INCLUDE_GST: False},
    )
    now = dt.datetime(2026, 7, 22, 18, 0, tzinfo=dt.UTC)

    with (
        patch(
            "custom_components.flipped_energy.api.IntegrationBlueprintApiClient.async_get_data",
            new=AsyncMock(
                return_value={
                    "plan_name": "Flipped Saver",
                    "amount_due_aud": 10.0,
                    "usage_today_kwh": 1.0,
                    "usage_feedin_yesterday_kwh": 0.5,
                    "usage_period_end": "2026-07-22",
                    "total_usage_kwh": 2.0,
                    "total_feedin_kwh": 0.5,
                    "import_rate_cents_kwh": 20.0,
                    "feedin_rate_cents_kwh": 2.0,
                    "import_rate_blocks": [
                        {
                            "name": "Day",
                            "start_minutes": 540,
                            "end_minutes": 1020,
                            "start_time": "09:00",
                            "end_time": "17:00",
                            "rate_cents_kwh": 9.93,
                        },
                        {
                            "name": "Evening",
                            "start_minutes": 1020,
                            "end_minutes": 1260,
                            "start_time": "17:00",
                            "end_time": "21:00",
                            "rate_cents_kwh": 57.62,
                        },
                    ],
                    "feedin_rate_blocks": [],
                    "last_successful_update": "2026-07-22T16:55:00+00:00",
                    "auth_ok": True,
                    "data_fresh": True,
                }
            ),
        ),
        patch(
            "custom_components.flipped_energy.sensor.dt_util.now",
            return_value=now,
        ),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.flipped_energy_current_import_tariff")
    assert state is not None
    assert state.state == "unknown"
    assert state.attributes.get("is_stale") is True
    assert state.attributes.get("valid_from") == "2026-07-22T17:00:00+00:00"
    assert state.attributes.get("valid_to") == "2026-07-22T21:00:00+00:00"


async def test_gst_toggle_refreshes_sensor_states_immediately(
    hass, mock_config_entry
) -> None:
    """Test GST option toggle immediately updates sensors without reload."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={CONF_INCLUDE_GST: False},
    )

    with (
        patch(
            "custom_components.flipped_energy.api.IntegrationBlueprintApiClient.async_get_data",
            new=AsyncMock(
                return_value={
                    "plan_name": "Flipped Saver",
                    "amount_due_aud": 123.45,
                    "usage_today_kwh": 8.9,
                    "usage_feedin_yesterday_kwh": 1.2,
                    "usage_period_start": "2026-07-20T00:00:00",
                    "usage_period_end": "2026-07-20",
                    "total_usage_kwh": 321.0,
                    "total_feedin_kwh": 41.5,
                    "import_rate_cents_kwh": 10.0,
                    "feedin_rate_cents_kwh": 2.0,
                    "import_rate_blocks": [],
                    "feedin_rate_blocks": [],
                    "supply_charge_daily_cents": 110.0,
                    "supply_charge_daily_incl_gst_cents": 121.0,
                    "auth_ok": True,
                    "data_fresh": True,
                    "last_successful_update": "2026-07-21T00:00:00+00:00",
                }
            ),
        ),
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()) as reload,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        import_rate = hass.states.get("sensor.flipped_energy_import_rate")
        assert import_rate is not None
        assert import_rate.state == "10.0"

        feedin_rate = hass.states.get("sensor.flipped_energy_feed_in_rate")
        assert feedin_rate is not None
        assert feedin_rate.state == "2.0"

        hass.config_entries.async_update_entry(
            mock_config_entry,
            options={CONF_INCLUDE_GST: True},
        )
        await hass.async_block_till_done()

        import_rate = hass.states.get("sensor.flipped_energy_import_rate")
        assert import_rate is not None
        assert import_rate.state == "11.0"

        feedin_rate = hass.states.get("sensor.flipped_energy_feed_in_rate")
        assert feedin_rate is not None
        assert feedin_rate.state == "2.0"
        reload.assert_not_awaited()


async def test_non_gst_option_changes_trigger_reload(hass, mock_config_entry) -> None:
    """Test changing structural options still performs a full reload."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.flipped_energy.api.IntegrationBlueprintApiClient.async_get_data",
            new=AsyncMock(
                return_value={
                    "plan_name": "Flipped Saver",
                    "amount_due_aud": 123.45,
                    "usage_today_kwh": 8.9,
                    "usage_feedin_yesterday_kwh": 1.2,
                    "usage_period_start": "2026-07-20T00:00:00",
                    "usage_period_end": "2026-07-20",
                    "total_usage_kwh": 321.0,
                    "total_feedin_kwh": 41.5,
                    "import_rate_cents_kwh": 10.0,
                    "feedin_rate_cents_kwh": 2.0,
                    "import_rate_blocks": [],
                    "feedin_rate_blocks": [],
                    "supply_charge_daily_cents": 110.0,
                    "supply_charge_daily_incl_gst_cents": 121.0,
                    "auth_ok": True,
                    "data_fresh": True,
                    "last_successful_update": "2026-07-21T00:00:00+00:00",
                }
            ),
        ),
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()) as reload,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        hass.config_entries.async_update_entry(
            mock_config_entry,
            options={
                CONF_INCLUDE_GST: False,
                CONF_ENABLE_PLAN_PAGE: False,
                CONF_REFRESH_INTERVAL_MINUTES: 45,
            },
        )
        await hass.async_block_till_done()
        reload.assert_awaited_once()
