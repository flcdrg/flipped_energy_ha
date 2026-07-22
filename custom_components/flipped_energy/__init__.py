"""
Custom integration to integrate Flipped Energy with Home Assistant.

For more details about this integration, please refer to
https://github.com/flcdrg/flipped_energy_ha
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import IntegrationBlueprintApiClient
from .const import (
    CONF_ENABLE_INVOICES_PAGE,
    CONF_ENABLE_PLAN_PAGE,
    CONF_ENABLE_USAGE_PAGE,
    CONF_INCLUDE_GST,
    CONF_REFRESH_INTERVAL_MINUTES,
    DEFAULT_INCLUDE_GST,
    DEFAULT_REFRESH_INTERVAL_MINUTES,
    DOMAIN,
    LOGGER,
)
from .coordinator import BlueprintDataUpdateCoordinator
from .data import IntegrationBlueprintData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import IntegrationBlueprintConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    refresh_interval_minutes = _refresh_interval_from_options(entry)
    enabled_pages = _enabled_pages_from_options(entry)
    include_gst = bool(entry.options.get(CONF_INCLUDE_GST, DEFAULT_INCLUDE_GST))

    coordinator = BlueprintDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(minutes=refresh_interval_minutes),
        config_entry=entry,
    )
    entry.runtime_data = IntegrationBlueprintData(
        client=IntegrationBlueprintApiClient(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            session=async_get_clientsession(hass),
            enabled_pages=enabled_pages,
        ),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
        include_gst=include_gst,
        refresh_interval_minutes=refresh_interval_minutes,
        enabled_pages=enabled_pages,
    )

    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _refresh_interval_from_options(entry: IntegrationBlueprintConfigEntry) -> int:
    """Return effective refresh interval from entry options."""
    return int(
        entry.options.get(
            CONF_REFRESH_INTERVAL_MINUTES,
            DEFAULT_REFRESH_INTERVAL_MINUTES,
        )
    )


def _enabled_pages_from_options(
    entry: IntegrationBlueprintConfigEntry,
) -> dict[str, bool]:
    """Return effective enabled page flags from entry options."""
    enabled_pages = {
        "plan": bool(entry.options.get(CONF_ENABLE_PLAN_PAGE, True)),
        "usage": bool(entry.options.get(CONF_ENABLE_USAGE_PAGE, True)),
        "invoices": bool(entry.options.get(CONF_ENABLE_INVOICES_PAGE, True)),
    }
    if not any(enabled_pages.values()):
        enabled_pages["usage"] = True
    return enabled_pages


async def async_options_updated(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> None:
    """React to options updates with immediate GST refresh or full reload."""
    new_refresh = _refresh_interval_from_options(entry)
    new_pages = _enabled_pages_from_options(entry)
    new_include_gst = bool(entry.options.get(CONF_INCLUDE_GST, DEFAULT_INCLUDE_GST))

    runtime_data = entry.runtime_data
    needs_reload = (
        runtime_data.refresh_interval_minutes != new_refresh
        or runtime_data.enabled_pages != new_pages
    )
    if needs_reload:
        await hass.config_entries.async_reload(entry.entry_id)
        return

    if runtime_data.include_gst != new_include_gst:
        runtime_data.include_gst = new_include_gst
        if runtime_data.coordinator.data is not None:
            runtime_data.coordinator.async_set_updated_data(
                runtime_data.coordinator.data
            )
