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
    CONF_INCLUDE_GST,
    DEFAULT_INCLUDE_GST,
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
    SNAPSHOT_USAGE_FEEDIN_YESTERDAY_KWH,
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
        name="Flipped Energy Usage Yesterday",
        native_unit_of_measurement="kWh",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SNAPSHOT_USAGE_FEEDIN_YESTERDAY_KWH,
        name="Flipped Energy Feedin Yesterday",
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

    _DEFAULT_GST_MULTIPLIER = 1.1

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
        current_tariff_map: dict[str, str] = {
            SNAPSHOT_CURRENT_IMPORT_TARIFF_CENTS: SNAPSHOT_IMPORT_RATE_BLOCKS,
            SNAPSHOT_CURRENT_FEEDIN_TARIFF_CENTS: SNAPSHOT_FEEDIN_RATE_BLOCKS,
        }
        block_key = current_tariff_map.get(key)
        if block_key is not None:
            return self._current_tariff_native_value(key, block_key)

        if key == SNAPSHOT_SUPPLY_CHARGE_DAILY_CENTS:
            return self._resolve_supply_charge_value_cents()

        schedule_block_map: dict[str, str] = {
            SNAPSHOT_IMPORT_TOU_SCHEDULE: SNAPSHOT_IMPORT_RATE_BLOCKS,
            SNAPSHOT_FEEDIN_TOU_SCHEDULE: SNAPSHOT_FEEDIN_RATE_BLOCKS,
        }
        schedule_key = schedule_block_map.get(key)
        if schedule_key is not None and value is None:
            return self._format_tou_schedule(
                self._adjusted_rate_blocks(key, schedule_key)
            )

        if key in (
            SNAPSHOT_IMPORT_RATE_BLOCKS,
            SNAPSHOT_FEEDIN_RATE_BLOCKS,
        ) and isinstance(value, list):
            return len(value)

        if key in (SNAPSHOT_IMPORT_RATE_CENTS, SNAPSHOT_FEEDIN_RATE_CENTS):
            adjusted = self._adjust_rate_value(key, value)
            if adjusted is not None:
                return adjusted

        return self._coerce_native_value_by_device_class(value)

    def _current_tariff_native_value(self, key: str, block_key: str) -> float | None:
        """Return current tariff rate for the active non-stale block."""
        active = self._active_tariff_context(key, block_key)
        if active and not active["is_stale"]:
            rate = active.get("rate_cents_kwh")
            if isinstance(rate, (int, float)):
                return float(rate)
        return None

    def _coerce_native_value_by_device_class(
        self,
        value: Any,
    ) -> str | int | float | dt.date | dt.datetime | None:
        """Convert native values for DATE/TIMESTAMP sensors when needed."""
        if value is None:
            return None

        device_class = self.entity_description.device_class
        if device_class == SensorDeviceClass.TIMESTAMP and isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            return dt.datetime.fromisoformat(normalized)
        if device_class == SensorDeviceClass.DATE and isinstance(value, str):
            return dt.date.fromisoformat(value[:10])
        return value

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
            rate_blocks = self._adjusted_rate_blocks(key, block_key)
            if isinstance(rate_blocks, list) and (rate_blocks or not require_non_empty):
                attributes[block_key] = rate_blocks

        if key == SNAPSHOT_SUPPLY_CHARGE_DAILY_CENTS:
            incl_gst = self.coordinator.data.get(
                SNAPSHOT_SUPPLY_CHARGE_DAILY_INCL_GST_CENTS
            )
            if incl_gst is not None:
                attributes[SNAPSHOT_SUPPLY_CHARGE_DAILY_INCL_GST_CENTS] = incl_gst

        if key in self._dynamic_gst_sensor_keys():
            attributes["gst_included"] = self._include_gst_enabled()

        current_tariff_map: dict[str, str] = {
            SNAPSHOT_CURRENT_IMPORT_TARIFF_CENTS: SNAPSHOT_IMPORT_RATE_BLOCKS,
            SNAPSHOT_CURRENT_FEEDIN_TARIFF_CENTS: SNAPSHOT_FEEDIN_RATE_BLOCKS,
        }
        current_block_key = current_tariff_map.get(key)
        if current_block_key:
            active = self._active_tariff_context(key, current_block_key)
            if active:
                attributes.update(active)

        return attributes or None

    def _active_tariff_context(self, key: str, block_key: str) -> dict[str, Any] | None:
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

        rate = context.get("rate_cents_kwh")
        if isinstance(rate, (int, float)) and self._key_uses_dynamic_gst(key):
            context["rate_cents_kwh"] = self._apply_gst_if_enabled(float(rate))
        return context

    def _include_gst_enabled(self) -> bool:
        """Return True when GST should be included in dynamic tariff values."""
        return bool(
            self.coordinator.config_entry.options.get(
                CONF_INCLUDE_GST,
                DEFAULT_INCLUDE_GST,
            )
        )

    def _dynamic_gst_sensor_keys(self) -> set[str]:
        """Return sensor keys with values affected by Include GST option."""
        return {
            SNAPSHOT_IMPORT_RATE_CENTS,
            SNAPSHOT_CURRENT_IMPORT_TARIFF_CENTS,
            SNAPSHOT_IMPORT_RATE_BLOCKS,
            SNAPSHOT_IMPORT_TOU_SCHEDULE,
            SNAPSHOT_SUPPLY_CHARGE_DAILY_CENTS,
        }

    def _key_uses_dynamic_gst(self, key: str) -> bool:
        """Return True when Include GST should transform this sensor key."""
        return key in self._dynamic_gst_sensor_keys()

    def _adjust_rate_value(self, key: str, value: Any) -> float | None:
        """Return rate value adjusted for Include GST option."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if not self._key_uses_dynamic_gst(key):
            return float(value)
        return self._apply_gst_if_enabled(float(value))

    def _apply_gst_if_enabled(self, value: float) -> float:
        """Apply GST multiplier when Include GST option is enabled."""
        if not self._include_gst_enabled():
            return value
        return round(value * self._gst_multiplier(), 6)

    def _gst_multiplier(self) -> float:
        """Derive GST multiplier from supply charge snapshots, fallback to default."""
        excl_raw = self.coordinator.data.get(SNAPSHOT_SUPPLY_CHARGE_DAILY_CENTS)
        incl_raw = self.coordinator.data.get(
            SNAPSHOT_SUPPLY_CHARGE_DAILY_INCL_GST_CENTS
        )
        if isinstance(excl_raw, (int, float)) and isinstance(incl_raw, (int, float)):
            excl = float(excl_raw)
            incl = float(incl_raw)
            if excl > 0 and incl > 0:
                return incl / excl
        return self._DEFAULT_GST_MULTIPLIER

    def _resolve_supply_charge_value_cents(self) -> float | None:
        """Return supply charge value based on Include GST option."""
        excl_raw = self.coordinator.data.get(SNAPSHOT_SUPPLY_CHARGE_DAILY_CENTS)
        incl_raw = self.coordinator.data.get(
            SNAPSHOT_SUPPLY_CHARGE_DAILY_INCL_GST_CENTS
        )

        excl = float(excl_raw) if isinstance(excl_raw, (int, float)) else None
        incl = float(incl_raw) if isinstance(incl_raw, (int, float)) else None

        if self._include_gst_enabled():
            if incl is not None:
                return round(incl, 6)
            if excl is not None:
                return round(excl * self._gst_multiplier(), 6)
            return None

        if excl is not None:
            return round(excl, 6)
        return round(incl, 6) if incl is not None else None

    def _adjusted_rate_blocks(
        self,
        key: str,
        block_key: str,
    ) -> list[dict[str, Any]] | None:
        """Return rate blocks with rate values adjusted for Include GST option."""
        raw_blocks = self.coordinator.data.get(block_key)
        if not isinstance(raw_blocks, list):
            return None

        adjusted: list[dict[str, Any]] = []
        for block in raw_blocks:
            if not isinstance(block, dict):
                continue
            block_copy = dict(block)
            rate = block_copy.get("rate_cents_kwh")
            if isinstance(rate, (int, float)) and self._key_uses_dynamic_gst(key):
                block_copy["rate_cents_kwh"] = self._apply_gst_if_enabled(float(rate))
            adjusted.append(block_copy)
        return adjusted

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
