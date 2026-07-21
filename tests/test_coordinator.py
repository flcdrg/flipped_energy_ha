"""Tests for flipped_energy coordinator statistics import."""

from __future__ import annotations

import datetime as dt
from datetime import timedelta
from logging import getLogger
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.flipped_energy.const import (
	SNAPSHOT_USAGE_DAILY_ROWS,
	SNAPSHOT_USAGE_HOURLY_ROWS,
)
from custom_components.flipped_energy.coordinator import BlueprintDataUpdateCoordinator

pytestmark = pytest.mark.asyncio


async def test_async_update_data_imports_usage_statistics(hass, mock_config_entry) -> None:
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
				"usageType": "Import",
			},
			{
				"time": "2026-07-20T01:00:00",
				"value": 1.3,
				"usageType": "Import",
			},
		],
		SNAPSHOT_USAGE_DAILY_ROWS: [
			{
				"time": "2026-07-20T00:00:00",
				"value": 8.0,
				"usageType": "Import",
			}
		],
	}

	mock_config_entry.runtime_data = SimpleNamespace(client=client)
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
	):
		data = await coordinator._async_update_data()

	assert data["usage_today_kwh"] == 8.0
	assert add_stats_mock.call_count == 2


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
				"usageType": "Import",
			},
			{
				"time": "2026-07-20T01:00:00",
				"value": 1.3,
				"usageType": "Import",
			},
		],
	}

	mock_config_entry.runtime_data = SimpleNamespace(client=client)
	coordinator = BlueprintDataUpdateCoordinator(
		hass=hass,
		logger=getLogger(__name__),
		name=mock_config_entry.domain,
		update_interval=timedelta(minutes=30),
		config_entry=mock_config_entry,
	)

	def _last_stat_side_effect(*args, **kwargs):
		statistic_id = args[2]
		return {
			statistic_id: [
				{
					"start": dt.datetime(2026, 7, 20, 0, 0, tzinfo=dt.UTC),
					"state": 1.1,
				}
			]
		}

	with (
		patch(
			"custom_components.flipped_energy.coordinator.get_last_statistics",
			side_effect=_last_stat_side_effect,
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
