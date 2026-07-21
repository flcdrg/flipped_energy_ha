"""Tests for flipped_energy API scraping client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from custom_components.flipped_energy.api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientAuthenticationError,
    IntegrationBlueprintApiClientExtractionError,
)
from custom_components.flipped_energy.const import (
    SNAPSHOT_AMOUNT_DUE_AUD,
    SNAPSHOT_BILLING_PERIOD_END,
    SNAPSHOT_BILLING_PERIOD_START,
    SNAPSHOT_FEEDIN_RATE_CENTS,
    SNAPSHOT_IMPORT_RATE_CENTS,
    SNAPSHOT_PLAN_NAME,
    SNAPSHOT_TOTAL_FEEDIN_KWH,
    SNAPSHOT_TOTAL_USAGE_KWH,
    SNAPSHOT_USAGE_PERIOD_END,
    SNAPSHOT_USAGE_PERIOD_START,
    SNAPSHOT_USAGE_TODAY_KWH,
)

pytestmark = pytest.mark.asyncio


async def test_is_session_valid_releases_response_body() -> None:
    """Test session validation consumes response body to release connection."""
    session = MagicMock()
    client = IntegrationBlueprintApiClient("user@example.com", "secret", session)
    client._auth_token = "token-value"

    response = AsyncMock()
    response.url = "https://flipped.energy/accounts/"
    response.status = 200

    context_manager = AsyncMock()
    context_manager.__aenter__.return_value = response
    context_manager.__aexit__.return_value = None
    session.get.return_value = context_manager

    assert await client._is_session_valid() is True
    response.read.assert_awaited_once()


async def test_async_get_data_reauths_after_session_expiry() -> None:
    """Test async_get_data retries with forced re-auth if API calls expire."""
    client = IntegrationBlueprintApiClient("user@example.com", "secret", None)

    with (
        patch.object(client, "_ensure_authenticated", new=AsyncMock()) as auth_mock,
        patch.object(
            client,
            "_augment_snapshot_from_api",
            new=AsyncMock(
                side_effect=[
                    IntegrationBlueprintApiClientAuthenticationError("expired"),
                    {
                        SNAPSHOT_PLAN_NAME: "Flipped Saver",
                        SNAPSHOT_AMOUNT_DUE_AUD: 123.45,
                        SNAPSHOT_USAGE_TODAY_KWH: 8.9,
                        SNAPSHOT_USAGE_PERIOD_START: "2026-07-20T00:00:00",
                        SNAPSHOT_USAGE_PERIOD_END: "2026-07-20",
                        SNAPSHOT_TOTAL_USAGE_KWH: 321.0,
                        SNAPSHOT_TOTAL_FEEDIN_KWH: 41.5,
                        SNAPSHOT_IMPORT_RATE_CENTS: 29.5,
                        SNAPSHOT_FEEDIN_RATE_CENTS: 8.0,
                    },
                ]
            ),
        ),
    ):
        data = await client.async_get_data()

    auth_mock.assert_has_awaits([call(), call(force=True)])
    assert data[SNAPSHOT_PLAN_NAME] == "Flipped Saver"
    assert data["auth_ok"] is True
    assert data["data_fresh"] is True
    assert data["last_successful_scrape"]


async def test_extract_hourly_usage_metrics_uses_latest_completed_day() -> None:
    """Test hourly usage rows produce the latest historical usage period."""
    client = IntegrationBlueprintApiClient("user@example.com", "secret", None)

    snapshot = client._extract_hourly_usage_metrics(
        [
            {
                "time": "2026-07-19T23:00:00",
                "value": 1.0,
                "usageType": "Import",
            },
            {
                "time": "2026-07-20T00:00:00",
                "value": 2.0,
                "usageType": "Import",
            },
            {
                "time": "2026-07-20T01:00:00",
                "value": 3.5,
                "usageType": "Import",
            },
            {
                "time": "2026-07-20T02:00:00",
                "value": 0.5,
                "usageType": "Export",
            },
        ]
    )

    assert snapshot[SNAPSHOT_USAGE_TODAY_KWH] == 5.5
    assert snapshot[SNAPSHOT_USAGE_PERIOD_START] == "2026-07-20T00:00:00"
    assert snapshot[SNAPSHOT_USAGE_PERIOD_END] == "2026-07-20"
