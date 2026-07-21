"""DataUpdateCoordinator for flipped_energy."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any

from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    IntegrationBlueprintApiClientAuthenticationError,
    IntegrationBlueprintApiClientError,
    IntegrationBlueprintApiClientRateLimitError,
)
from .const import (
    DOMAIN,
    SNAPSHOT_USAGE_DAILY_ROWS,
    SNAPSHOT_USAGE_HOURLY_ROWS,
)

if TYPE_CHECKING:
    from .data import IntegrationBlueprintConfigEntry


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class BlueprintDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: IntegrationBlueprintConfigEntry

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        try:
            data = await self.config_entry.runtime_data.client.async_get_data()
            await self._async_import_usage_statistics(data)
            return data
        except IntegrationBlueprintApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except IntegrationBlueprintApiClientRateLimitError as exception:
            raise UpdateFailed(
                exception,
                retry_after=exception.retry_after,
            ) from exception
        except IntegrationBlueprintApiClientError as exception:
            raise UpdateFailed(exception) from exception

    async def _async_import_usage_statistics(self, data: Any) -> None:
        """Import fetched usage rows into recorder external statistics."""
        if not isinstance(data, dict):
            return

        await self._async_import_usage_series(
            rows=data.get(SNAPSHOT_USAGE_HOURLY_ROWS),
            statistic_suffix="usage_hourly_import_kwh",
            name="Flipped Energy Hourly Import Usage",
        )
        await self._async_import_usage_series(
            rows=data.get(SNAPSHOT_USAGE_DAILY_ROWS),
            statistic_suffix="usage_daily_import_kwh",
            name="Flipped Energy Daily Import Usage",
        )

    async def _async_import_usage_series(
        self,
        rows: Any,
        statistic_suffix: str,
        name: str,
    ) -> None:
        """Import one usage series while skipping points already in recorder."""
        if not isinstance(rows, list):
            return

        points = self._extract_import_points(rows)
        if not points:
            return

        statistic_id = f"{DOMAIN}:{self.config_entry.entry_id}:{statistic_suffix}"
        last_start = await self._async_get_last_stat_start(statistic_id)
        if last_start is not None:
            points = [point for point in points if point[0] > last_start]
        if not points:
            return

        metadata = {
            "has_mean": False,
            "has_sum": False,
            "name": name,
            "source": DOMAIN,
            "statistic_id": statistic_id,
            "unit_of_measurement": "kWh",
        }
        statistics = [
            {
                "start": start,
                "state": value,
            }
            for start, value in points
        ]
        async_add_external_statistics(self.hass, metadata, statistics)

    async def _async_get_last_stat_start(
        self,
        statistic_id: str,
    ) -> dt.datetime | None:
        """Return the latest imported timestamp for a statistic id."""
        try:
            result = await self.hass.async_add_executor_job(
                get_last_statistics,
                self.hass,
                1,
                statistic_id,
                False,
                {"state"},
            )
        except Exception as exception:  # pylint: disable=broad-except
            self.logger.debug(
                "Unable to read recorder statistics for %s: %s",
                statistic_id,
                exception,
            )
            return None

        rows = result.get(statistic_id, [])
        if not rows:
            return None

        start = rows[0].get("start")
        if not isinstance(start, dt.datetime):
            return None
        if start.tzinfo is None:
            return start.replace(tzinfo=dt.UTC)
        return start.astimezone(dt.UTC)

    def _extract_import_points(
        self,
        rows: list[dict[str, Any]],
    ) -> list[tuple[dt.datetime, float]]:
        """Return sorted UTC timestamp/value points for import rows."""
        points_by_start: dict[dt.datetime, float] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue

            usage_type = row.get("usageType")
            if not isinstance(usage_type, str) or usage_type.lower() != "import":
                continue

            stamp = row.get("time")
            if not isinstance(stamp, str):
                continue

            normalized = stamp.replace("Z", "+00:00")
            try:
                parsed = dt.datetime.fromisoformat(normalized)
            except ValueError:
                continue

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.UTC)
            else:
                parsed = parsed.astimezone(dt.UTC)

            value_raw = row.get("value")
            if isinstance(value_raw, bool) or not isinstance(value_raw, (int, float)):
                continue

            points_by_start[parsed] = float(value_raw)

        return sorted(points_by_start.items(), key=lambda point: point[0])
