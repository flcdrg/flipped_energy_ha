"""Sensor platform for flipped_energy."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.util import dt as dt_util

from .const import (
    SNAPSHOT_AMOUNT_DUE_AUD,
    SNAPSHOT_CURRENT_FEEDIN_TARIFF_CENTS,
    SNAPSHOT_CURRENT_IMPORT_TARIFF_CENTS,
    SNAPSHOT_FEEDIN_RATE_BLOCKS,
    SNAPSHOT_FEEDIN_RATE_CENTS,
    SNAPSHOT_FEEDIN_TOU_SCHEDULE,
    SNAPSHOT_IMPORT_RATE_BLOCKS,
    SNAPSHOT_IMPORT_RATE_CENTS,
    SNAPSHOT_IMPORT_TOU_SCHEDULE,
    SNAPSHOT_LAST_SUCCESSFUL_UPDATE,
    SNAPSHOT_PLAN_NAME,
    SNAPSHOT_SUPPLY_CHARGE_DAILY_CENTS,
    SNAPSHOT_SUPPLY_CHARGE_DAILY_INCL_GST_CENTS,
    SNAPSHOT_TOTAL_FEEDIN_KWH,
    SNAPSHOT_TOTAL_USAGE_KWH,
    SNAPSHOT_USAGE_PERIOD_END,
    SNAPSHOT_USAGE_PERIOD_START,
    SNAPSHOT_USAGE_TODAY_KWH,
)
from .entity import IntegrationBlueprintEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import BlueprintDataUpdateCoordinator
    from .data import IntegrationBlueprintConfigEntry

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key=SNAPSHOT_PLAN_NAME,
        name="Flipped Energy Plan Name",
        icon="mdi:lightning-bolt-circle",
    ),
    SensorEntityDescription(
        key=SNAPSHOT_AMOUNT_DUE_AUD,
        name="Flipped Energy Amount Due",
        icon="mdi:cash",
        native_unit_of_measurement="AUD",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SNAPSHOT_USAGE_TODAY_KWH,
        name="Flipped Energy Usage",
        native_unit_of_measurement="kWh",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SNAPSHOT_USAGE_PERIOD_END,
        name="Flipped Energy Usage Period End",
        device_class=SensorDeviceClass.DATE,
    ),
    SensorEntityDescription(
        key=SNAPSHOT_TOTAL_USAGE_KWH,
        name="Flipped Energy Total Usage",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement="kWh",
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key=SNAPSHOT_TOTAL_FEEDIN_KWH,
        name="Flipped Energy Total Feed-In",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement="kWh",
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key=SNAPSHOT_IMPORT_RATE_CENTS,
        name="Flipped Energy Import Rate",
        icon="mdi:currency-usd",
        native_unit_of_measurement="c/kWh",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SNAPSHOT_FEEDIN_RATE_CENTS,
        name="Flipped Energy Feed-In Rate",
        icon="mdi:solar-power-variant",
        native_unit_of_measurement="c/kWh",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SNAPSHOT_CURRENT_IMPORT_TARIFF_CENTS,
        name="Flipped Energy Current Import Tariff",
        icon="mdi:flash",
        native_unit_of_measurement="c/kWh",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SNAPSHOT_CURRENT_FEEDIN_TARIFF_CENTS,
        name="Flipped Energy Current Feed-In Tariff",
        icon="mdi:solar-power",
        native_unit_of_measurement="c/kWh",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SNAPSHOT_IMPORT_RATE_BLOCKS,
        name="Flipped Energy Import TOU Blocks",
        icon="mdi:clock-time-eight-outline",
    ),
    SensorEntityDescription(
        key=SNAPSHOT_FEEDIN_RATE_BLOCKS,
        name="Flipped Energy Feed-In TOU Blocks",
        icon="mdi:clock-time-eight-outline",
    ),
    SensorEntityDescription(
        key=SNAPSHOT_IMPORT_TOU_SCHEDULE,
        name="Flipped Energy Import TOU Schedule",
        icon="mdi:table-clock",
    ),
    SensorEntityDescription(
        key=SNAPSHOT_FEEDIN_TOU_SCHEDULE,
        name="Flipped Energy Feed-In TOU Schedule",
        icon="mdi:table-clock",
    ),
    SensorEntityDescription(
        key=SNAPSHOT_SUPPLY_CHARGE_DAILY_CENTS,
        name="Flipped Energy Supply Charge Daily",
        icon="mdi:transmission-tower",
        native_unit_of_measurement="c/day",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SNAPSHOT_SUPPLY_CHARGE_DAILY_INCL_GST_CENTS,
        name="Flipped Energy Supply Charge Daily (Incl GST)",
        icon="mdi:transmission-tower",
        native_unit_of_measurement="c/day",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SNAPSHOT_LAST_SUCCESSFUL_UPDATE,
        name="Flipped Energy Last Successful Update",
        icon="mdi:clock-check",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: IntegrationBlueprintConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        IntegrationBlueprintSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class IntegrationBlueprintSensor(IntegrationBlueprintEntity, SensorEntity):
    """flipped_energy Sensor class."""

    def __init__(
        self,
        coordinator: BlueprintDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, unique_id_suffix=entity_description.key)
        self.entity_description = entity_description

    @property
    def native_value(self) -> str | int | float | dt.date | dt.datetime | None:
        """Return the native value of the sensor."""
        key = self.entity_description.key
        value = self.coordinator.data.get(key)
        result: str | int | float | dt.date | dt.datetime | None = value

        if key == SNAPSHOT_CURRENT_IMPORT_TARIFF_CENTS:
            active = self._active_tariff_context(SNAPSHOT_IMPORT_RATE_BLOCKS)
            if active and not active["is_stale"]:
                return active["rate_cents_kwh"]
            return None

        if key == SNAPSHOT_CURRENT_FEEDIN_TARIFF_CENTS:
            active = self._active_tariff_context(SNAPSHOT_FEEDIN_RATE_BLOCKS)
            if active and not active["is_stale"]:
                return active["rate_cents_kwh"]
            return None

        if value is None:
            # Schedule sensors are derived from TOU block attributes.
            if key == SNAPSHOT_IMPORT_TOU_SCHEDULE:
                result = self._format_tou_schedule(
                    self.coordinator.data.get(SNAPSHOT_IMPORT_RATE_BLOCKS)
                )
            elif key == SNAPSHOT_FEEDIN_TOU_SCHEDULE:
                result = self._format_tou_schedule(
                    self.coordinator.data.get(SNAPSHOT_FEEDIN_RATE_BLOCKS)
                )
            else:
                result = None
        elif key in (
            SNAPSHOT_IMPORT_RATE_BLOCKS,
            SNAPSHOT_FEEDIN_RATE_BLOCKS,
        ) and isinstance(value, list):
            result = len(value)
        else:
            device_class = self.entity_description.device_class
            if device_class == SensorDeviceClass.TIMESTAMP and isinstance(value, str):
                normalized = value.replace("Z", "+00:00")
                result = dt.datetime.fromisoformat(normalized)
            elif device_class == SensorDeviceClass.DATE and isinstance(value, str):
                result = dt.date.fromisoformat(value[:10])

        return result

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional metadata for usage, rates, and supply charges."""
        key = self.entity_description.key
        attributes: dict[str, Any] = {}

        if key == SNAPSHOT_USAGE_TODAY_KWH:
            period_start = self.coordinator.data.get(SNAPSHOT_USAGE_PERIOD_START)
            period_end = self.coordinator.data.get(SNAPSHOT_USAGE_PERIOD_END)
            if period_start is not None:
                attributes[SNAPSHOT_USAGE_PERIOD_START] = str(period_start)
            if period_end is not None:
                attributes[SNAPSHOT_USAGE_PERIOD_END] = str(period_end)

        block_attribute_map: dict[str, tuple[str, bool]] = {
            SNAPSHOT_IMPORT_RATE_CENTS: (SNAPSHOT_IMPORT_RATE_BLOCKS, True),
            SNAPSHOT_FEEDIN_RATE_CENTS: (SNAPSHOT_FEEDIN_RATE_BLOCKS, True),
            SNAPSHOT_IMPORT_RATE_BLOCKS: (SNAPSHOT_IMPORT_RATE_BLOCKS, False),
            SNAPSHOT_FEEDIN_RATE_BLOCKS: (SNAPSHOT_FEEDIN_RATE_BLOCKS, False),
            SNAPSHOT_IMPORT_TOU_SCHEDULE: (SNAPSHOT_IMPORT_RATE_BLOCKS, False),
            SNAPSHOT_FEEDIN_TOU_SCHEDULE: (SNAPSHOT_FEEDIN_RATE_BLOCKS, False),
        }
        block_config = block_attribute_map.get(key)
        if block_config:
            block_key, require_non_empty = block_config
            rate_blocks = self.coordinator.data.get(block_key)
            if isinstance(rate_blocks, list) and (rate_blocks or not require_non_empty):
                attributes[block_key] = rate_blocks

        if key == SNAPSHOT_SUPPLY_CHARGE_DAILY_CENTS:
            incl_gst = self.coordinator.data.get(
                SNAPSHOT_SUPPLY_CHARGE_DAILY_INCL_GST_CENTS
            )
            if incl_gst is not None:
                attributes[SNAPSHOT_SUPPLY_CHARGE_DAILY_INCL_GST_CENTS] = incl_gst

        current_tariff_map: dict[str, str] = {
            SNAPSHOT_CURRENT_IMPORT_TARIFF_CENTS: SNAPSHOT_IMPORT_RATE_BLOCKS,
            SNAPSHOT_CURRENT_FEEDIN_TARIFF_CENTS: SNAPSHOT_FEEDIN_RATE_BLOCKS,
        }
        current_block_key = current_tariff_map.get(key)
        if current_block_key:
            active = self._active_tariff_context(current_block_key)
            if active:
                attributes.update(active)

        return attributes or None

    def _active_tariff_context(self, block_key: str) -> dict[str, Any] | None:
        """Return active tariff block context including validity and staleness."""
        blocks = self.coordinator.data.get(block_key)
        if not isinstance(blocks, list) or not blocks:
            return None

        now = dt_util.now()
        minute_now = (now.hour * 60) + now.minute
        active_block = self._find_active_block(blocks, minute_now)
        if active_block is None:
            return None

        valid_from, valid_to = self._resolve_block_validity_window(now, active_block)
        last_update = self._parse_last_successful_update()
        is_stale = (
            last_update is None
            or last_update < valid_from
            or (now >= valid_to and last_update < valid_to)
        )

        context: dict[str, Any] = {
            "valid_from": valid_from.isoformat(),
            "valid_to": valid_to.isoformat(),
            "is_stale": is_stale,
            "last_successful_update": (
                last_update.isoformat() if last_update is not None else None
            ),
            "rate_cents_kwh": active_block.get("rate_cents_kwh"),
            "start_time": active_block.get("start_time"),
            "end_time": active_block.get("end_time"),
        }
        if "name" in active_block:
            context["name"] = active_block.get("name")
        return context

    def _find_active_block(
        self,
        blocks: list[Any],
        minute_now: int,
    ) -> dict[str, Any] | None:
        """Return the first TOU block active at the provided minute-of-day."""
        for block in blocks:
            if not isinstance(block, dict):
                continue
            start = block.get("start_minutes")
            end = block.get("end_minutes")
            if not isinstance(start, int) or not isinstance(end, int):
                continue
            if self._is_minute_in_block(minute_now, start, end):
                return block
        return None

    def _is_minute_in_block(self, minute_now: int, start: int, end: int) -> bool:
        """Return True when the current minute is inside the TOU block window."""
        if start == end:
            return True
        if start < end:
            return start <= minute_now < end
        return minute_now >= start or minute_now < end

    def _resolve_block_validity_window(
        self,
        now: dt.datetime,
        block: dict[str, Any],
    ) -> tuple[dt.datetime, dt.datetime]:
        """Resolve active block validity window as tz-aware datetimes."""
        start = int(block["start_minutes"])
        end = int(block["end_minutes"])
        day = now.date()

        if start == end:
            start_day = day
            end_day = day + dt.timedelta(days=1)
        elif start < end:
            start_day = day
            end_day = day
        elif (now.hour * 60 + now.minute) >= start:
            start_day = day
            end_day = day + dt.timedelta(days=1)
        else:
            start_day = day - dt.timedelta(days=1)
            end_day = day

        valid_from = dt.datetime.combine(
            start_day,
            dt.time(hour=start // 60, minute=start % 60),
            tzinfo=now.tzinfo,
        )
        valid_to = dt.datetime.combine(
            end_day,
            dt.time(hour=end // 60, minute=end % 60),
            tzinfo=now.tzinfo,
        )
        if valid_to <= valid_from:
            valid_to = valid_to + dt.timedelta(days=1)

        return valid_from, valid_to

    def _parse_last_successful_update(self) -> dt.datetime | None:
        """Parse last successful snapshot update timestamp as local tz-aware dt."""
        raw = self.coordinator.data.get(SNAPSHOT_LAST_SUCCESSFUL_UPDATE)
        if not isinstance(raw, str):
            return None
        normalized = raw.replace("Z", "+00:00")
        try:
            parsed = dt.datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.UTC)
        return parsed.astimezone(dt_util.now().tzinfo)

    def _format_tou_schedule(self, value: Any) -> str | None:
        """Return a compact human-readable TOU schedule from rate blocks."""
        if not isinstance(value, list) or not value:
            return None

        segments: list[str] = []
        for block in value:
            if not isinstance(block, dict):
                continue
            name = block.get("name")
            start_time = block.get("start_time")
            end_time = block.get("end_time")
            rate = block.get("rate_cents_kwh")

            if not isinstance(start_time, str) or not isinstance(end_time, str):
                continue

            prefix = f"{name} " if isinstance(name, str) and name.strip() else ""
            if isinstance(rate, (int, float)):
                segments.append(
                    f"{prefix}{start_time}-{end_time} @ {float(rate):.4f} c/kWh"
                )
            else:
                segments.append(f"{prefix}{start_time}-{end_time}")

        if not segments:
            return None
        return "; ".join(segments)
