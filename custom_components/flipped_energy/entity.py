"""BlueprintEntity class."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, SNAPSHOT_ACCOUNT_NUMBER, SNAPSHOT_METER_NMI
from .coordinator import BlueprintDataUpdateCoordinator

DEFAULT_DEVICE_NAME = "Flipped Energy"


class IntegrationBlueprintEntity(CoordinatorEntity[BlueprintDataUpdateCoordinator]):
    """BlueprintEntity class."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: BlueprintDataUpdateCoordinator,
        unique_id_suffix: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{unique_id_suffix}"
        identifiers: set[tuple[str, str]] = {
            (coordinator.config_entry.domain, coordinator.config_entry.entry_id),
        }
        snapshot = coordinator.data if isinstance(coordinator.data, dict) else {}
        account_number = snapshot.get(SNAPSHOT_ACCOUNT_NUMBER)
        if isinstance(account_number, str) and account_number.strip():
            identifiers.add(
                (
                    coordinator.config_entry.domain,
                    f"account_number:{account_number.strip()}",
                )
            )
        meter_nmi = snapshot.get(SNAPSHOT_METER_NMI)
        if isinstance(meter_nmi, str) and meter_nmi.strip():
            identifiers.add(
                (
                    coordinator.config_entry.domain,
                    f"meter_nmi:{meter_nmi.strip()}",
                )
            )
        self._attr_device_info = DeviceInfo(
            identifiers=identifiers,
            name=DEFAULT_DEVICE_NAME,
        )
