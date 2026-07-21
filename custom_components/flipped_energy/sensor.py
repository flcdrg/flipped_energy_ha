"""Sensor platform for flipped_energy."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)

from .const import (
    SNAPSHOT_AMOUNT_DUE_AUD,
    SNAPSHOT_FEEDIN_RATE_CENTS,
    SNAPSHOT_IMPORT_RATE_CENTS,
    SNAPSHOT_LAST_SUCCESSFUL_UPDATE,
    SNAPSHOT_PLAN_NAME,
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
    def native_value(self) -> str | float | dt.date | dt.datetime | None:
        """Return the native value of the sensor."""
        value = self.coordinator.data.get(self.entity_description.key)
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
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the usage period metadata for the usage sensor."""
        if self.entity_description.key != SNAPSHOT_USAGE_TODAY_KWH:
            return None

        attributes: dict[str, str] = {}
        period_start = self.coordinator.data.get(SNAPSHOT_USAGE_PERIOD_START)
        period_end = self.coordinator.data.get(SNAPSHOT_USAGE_PERIOD_END)
        if period_start is not None:
            attributes[SNAPSHOT_USAGE_PERIOD_START] = str(period_start)
        if period_end is not None:
            attributes[SNAPSHOT_USAGE_PERIOD_END] = str(period_end)
        return attributes or None
