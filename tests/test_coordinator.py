"""Tests for flipped_energy coordinator statistics import."""

from __future__ import annotations

import datetime as dt
from datetime import timedelta
from logging import getLogger
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.recorder.models.statistics import StatisticMeanType

from custom_components.flipped_energy.const import (
    SNAPSHOT_USAGE_DAILY_ROWS,
    SNAPSHOT_USAGE_HOURLY_ROWS,
)
from custom_components.flipped_energy.coordinator import BlueprintDataUpdateCoordinator

pytestmark = pytest.mark.asyncio


async def test_async_update_data_imports_usage_statistics(
    hass, mock_config_entry
) -> None:
    """Test coordinator imports hourly and daily rows as external statistics."""
    client = AsyncMock()
    client.async_get_data.return_value = {
        "usage_today_kwh": 8.0,
        "total_usage_kwh": 100.0,
        "total_feedin_kwh": 10.0,
        SNAPSHOT_USAGE_HOURLY_ROWS: [
            {
                "time": "2026-07-20T00:00:00",
                "value": 1.1,
                "usageType": "Export",
            },
            {
                "time": "2026-07-20T01:00:00",
                "value": 1.3,
                "usageType": "Export",
            },
        ],
        SNAPSHOT_USAGE_DAILY_ROWS: [
            {
                "time": "2026-07-20T00:00:00",
                "value": 8.0,
                "usageType": "Export",
            }
        ],
    }

    mock_config_entry.runtime_data = SimpleNamespace(client=client)
    mock_config_entry.runtime_data.enabled_pages = {
        "plan": True,
        "usage": True,
        "invoices": True,
    }
    mock_config_entry.runtime_data.refresh_interval_minutes = 30
    coordinator = BlueprintDataUpdateCoordinator(
        hass=hass,
        logger=getLogger(__name__),
        name=mock_config_entry.domain,
        update_interval=timedelta(minutes=30),
        config_entry=mock_config_entry,
    )

    with (
        patch(
            "custom_components.flipped_energy.coordinator.get_last_statistics",
            return_value={},
        ),
        patch(
            "custom_components.flipped_energy.coordinator.async_add_external_statistics"
        ) as add_stats_mock,
        patch(
            "custom_components.flipped_energy.coordinator.get_instance"
        ) as get_instance_mock,
    ):
        # Mock the Recorder instance to return results from get_last_statistics
        recorder_mock = AsyncMock()
        recorder_mock.async_add_executor_job.return_value = {}
        get_instance_mock.return_value = recorder_mock

        data = await coordinator._async_update_data()

    assert data["usage_today_kwh"] == 8.0
    assert add_stats_mock.call_count == 2
    first_metadata = add_stats_mock.call_args_list[0].args[1]
    assert first_metadata["mean_type"] is StatisticMeanType.ARITHMETIC
    assert first_metadata["unit_class"] == "energy"


async def test_async_update_data_skips_duplicate_usage_statistics(
    hass,
    mock_config_entry,
) -> None:
    """Test coordinator only imports points newer than existing statistics."""
    client = AsyncMock()
    client.async_get_data.return_value = {
        "usage_today_kwh": 8.0,
        "total_usage_kwh": 100.0,
        "total_feedin_kwh": 10.0,
        SNAPSHOT_USAGE_HOURLY_ROWS: [
            {
                "time": "2026-07-20T00:00:00",
                "value": 1.1,
                "usageType": "Export",
            },
            {
                "time": "2026-07-20T01:00:00",
                "value": 1.3,
                "usageType": "Export",
            },
        ],
    }

    mock_config_entry.runtime_data = SimpleNamespace(client=client)
    mock_config_entry.runtime_data.enabled_pages = {
        "plan": True,
        "usage": True,
        "invoices": True,
    }
    mock_config_entry.runtime_data.refresh_interval_minutes = 30
    coordinator = BlueprintDataUpdateCoordinator(
        hass=hass,
        logger=getLogger(__name__),
        name=mock_config_entry.domain,
        update_interval=timedelta(minutes=30),
        config_entry=mock_config_entry,
    )

    with (
        patch.object(
            coordinator,
            "_async_get_last_stat_start",
            return_value=dt.datetime(2026, 7, 20, 0, 0, tzinfo=dt.UTC),
        ),
        patch(
            "custom_components.flipped_energy.coordinator.async_add_external_statistics"
        ) as add_stats_mock,
    ):
        await coordinator._async_update_data()

    assert add_stats_mock.call_count == 1
    stats_payload = add_stats_mock.call_args.args[2]
    assert len(stats_payload) == 1
    assert stats_payload[0]["state"] == 1.3


async def test_build_statistic_id_is_recorder_valid(hass, mock_config_entry) -> None:
    """Test generated statistic IDs follow recorder validation constraints."""
    client = AsyncMock()
    mock_config_entry.runtime_data = SimpleNamespace(client=client)
    mock_config_entry.runtime_data.enabled_pages = {
        "plan": True,
        "usage": True,
        "invoices": True,
    }
    mock_config_entry.runtime_data.refresh_interval_minutes = 30
    coordinator = BlueprintDataUpdateCoordinator(
        hass=hass,
        logger=getLogger(__name__),
        name=mock_config_entry.domain,
        update_interval=timedelta(minutes=30),
        config_entry=mock_config_entry,
    )

    statistic_id = coordinator._build_statistic_id("usage_hourly_import_kwh")
    assert statistic_id.startswith("flipped_energy:")
    assert statistic_id.count(":") == 1
    assert "-" not in statistic_id


async def test_async_update_data_tolerates_statistics_import_failure(
    hass,
    mock_config_entry,
) -> None:
    """Test coordinator still returns data when stats import fails."""
    client = AsyncMock()
    client.async_get_data.return_value = {
        "usage_today_kwh": 8.0,
        "total_usage_kwh": 100.0,
        "total_feedin_kwh": 10.0,
    }

    mock_config_entry.runtime_data = SimpleNamespace(client=client)
    mock_config_entry.runtime_data.enabled_pages = {
        "plan": True,
        "usage": True,
        "invoices": True,
    }
    mock_config_entry.runtime_data.refresh_interval_minutes = 30
    coordinator = BlueprintDataUpdateCoordinator(
        hass=hass,
        logger=getLogger(__name__),
        name=mock_config_entry.domain,
        update_interval=timedelta(minutes=30),
        config_entry=mock_config_entry,
    )

    with patch.object(
        coordinator,
        "_async_import_usage_statistics",
        side_effect=RuntimeError("boom"),
    ):
        data = await coordinator._async_update_data()

    assert data["usage_today_kwh"] == 8.0


async def test_async_update_data_uses_plan_only_between_full_refreshes(
    hass,
    mock_config_entry,
) -> None:
    """Test fast polls only request plan data and keep previous static fields."""
    client = AsyncMock()
    client.async_get_data.return_value = {
        "plan_name": "Flipped Saver",
        "import_rate_cents_kwh": 30.0,
        "feedin_rate_cents_kwh": 2.0,
    }

    mock_config_entry.runtime_data = SimpleNamespace(
        client=client,
        enabled_pages={"plan": True, "usage": True, "invoices": True},
        refresh_interval_minutes=30,
    )
    coordinator = BlueprintDataUpdateCoordinator(
        hass=hass,
        logger=getLogger(__name__),
        name=mock_config_entry.domain,
        update_interval=timedelta(minutes=5),
        config_entry=mock_config_entry,
    )
    coordinator.data = {
        "usage_today_kwh": 7.5,
        "total_usage_kwh": 200.0,
        "amount_due_aud": 50.0,
    }
    coordinator._last_full_refresh_at = dt.datetime.now(dt.UTC)

    data = await coordinator._async_update_data()

    client.async_get_data.assert_awaited_once_with(
        enabled_pages={"plan": True, "usage": False, "invoices": False}
    )
    assert data["usage_today_kwh"] == 7.5
    assert data["amount_due_aud"] == 50.0
    assert data["import_rate_cents_kwh"] == 30.0
