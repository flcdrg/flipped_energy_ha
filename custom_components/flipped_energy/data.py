"""Custom types for flipped_energy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import IntegrationBlueprintApiClient
    from .coordinator import BlueprintDataUpdateCoordinator


type IntegrationBlueprintConfigEntry = ConfigEntry[IntegrationBlueprintData]


class FlippedEnergySnapshot(TypedDict, total=False):
    """Normalized account data scraped from the portal."""

    plan_name: str
    amount_due_aud: float
    usage_today_kwh: float
    usage_period_start: str
    usage_period_end: str
    total_usage_kwh: float
    total_feedin_kwh: float
    import_rate_cents_kwh: float
    feedin_rate_cents_kwh: float
    billing_period_start: str
    billing_period_end: str
    auth_ok: bool
    data_fresh: bool
    last_successful_scrape: str


@dataclass
class IntegrationBlueprintData:
    """Data for the Blueprint integration."""

    client: IntegrationBlueprintApiClient
    coordinator: BlueprintDataUpdateCoordinator
    integration: Integration
