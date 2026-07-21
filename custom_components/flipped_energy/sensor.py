"""Sensor platform for flipped_energy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)

from .entity import IntegrationBlueprintEntity
from .const import (
    SNAPSHOT_AMOUNT_DUE_AUD,
    SNAPSHOT_FEEDIN_RATE_CENTS,
    SNAPSHOT_IMPORT_RATE_CENTS,
    SNAPSHOT_LAST_SUCCESSFUL_SCRAPE,
    SNAPSHOT_PLAN_NAME,
    SNAPSHOT_TOTAL_FEEDIN_KWH,
    SNAPSHOT_TOTAL_USAGE_KWH,
    SNAPSHOT_USAGE_TODAY_KWH,
)

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
        name="Flipped Energy Usage Today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement="kWh",
        state_class=SensorStateClass.MEASUREMENT,
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
        key=SNAPSHOT_LAST_SUCCESSFUL_SCRAPE,
        name="Flipped Energy Last Successful Scrape",
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
    def native_value(self) -> str | float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)
