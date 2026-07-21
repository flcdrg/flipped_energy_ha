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
    SNAPSHOT_USAGE_TODAY_KWH,
)

pytestmark = pytest.mark.asyncio


async def test_build_snapshot_extracts_expected_fields(load_fixture) -> None:
    """Test parser extracts normalized values from fixture page content."""
    client = IntegrationBlueprintApiClient("user@example.com", "secret", None)

    plan_html = load_fixture("scrape/plan_page.html")
    usage_html = load_fixture("scrape/usage_page.html")
    invoices_html = load_fixture("scrape/invoices_page.html")

    snapshot = client._build_snapshot(
        {
            "plan": plan_html,
            "usage": usage_html,
            "invoices": invoices_html,
        }
    )

    assert snapshot[SNAPSHOT_PLAN_NAME] == "Flipped Saver"
    assert snapshot[SNAPSHOT_AMOUNT_DUE_AUD] == 123.45
    assert snapshot[SNAPSHOT_USAGE_TODAY_KWH] == 8.9
    assert snapshot[SNAPSHOT_TOTAL_USAGE_KWH] == 321.0
    assert snapshot[SNAPSHOT_TOTAL_FEEDIN_KWH] == 41.5
    assert snapshot[SNAPSHOT_IMPORT_RATE_CENTS] == 29.5
    assert snapshot[SNAPSHOT_FEEDIN_RATE_CENTS] == 8.0
    assert snapshot[SNAPSHOT_BILLING_PERIOD_START] == "2026-07-01"
    assert snapshot[SNAPSHOT_BILLING_PERIOD_END] == "2026-07-31"


async def test_build_snapshot_raises_on_missing_required_fields() -> None:
    """Test parser fails if required usage/billing fields are not found."""
    client = IntegrationBlueprintApiClient("user@example.com", "secret", None)

    with pytest.raises(IntegrationBlueprintApiClientExtractionError):
        client._build_snapshot(
            {
                "plan": "<html><head><title>Plan Details - Flipped Energy</title></head><body>No plan data</body></html>",
                "usage": "<html><body>No numeric usage here</body></html>",
                "invoices": "<html><body>No amount due here</body></html>",
            }
        )


async def test_build_snapshot_raises_when_some_required_fields_are_missing() -> None:
    """Test parser fails when only a subset of required fields can be extracted."""
    client = IntegrationBlueprintApiClient("user@example.com", "secret", None)

    with pytest.raises(IntegrationBlueprintApiClientExtractionError):
        client._build_snapshot(
            {
                "plan": """
                    <html>
                        <head><title>Flipped Saver - Flipped Energy</title></head>
                        <body>Import Rate: 29.5 c/kWh</body>
                    </html>
                """,
                "usage": "<html><body>Usage Today: 8.9 kWh</body></html>",
                "invoices": "<html><body>Amount Due: $123.45</body></html>",
            }
        )


async def test_is_session_valid_releases_response_body() -> None:
    """Test session validation consumes response body to release connection."""
    session = MagicMock()
    client = IntegrationBlueprintApiClient("user@example.com", "secret", session)

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
    """Test async_get_data retries with forced re-auth if a page fetch expires."""
    client = IntegrationBlueprintApiClient("user@example.com", "secret", None)

    with (
        patch.object(client, "_ensure_authenticated", new=AsyncMock()) as auth_mock,
        patch.object(
            client,
            "_fetch_page",
            new=AsyncMock(
                side_effect=[
                    IntegrationBlueprintApiClientAuthenticationError("expired"),
                    "<html><body>Plan Name: Flipped Saver Import Rate: 29.5 c/kWh Feed-in Rate: 8.0 c/kWh</body></html>",
                    "<html><body>Usage Today: 8.9 kWh Total Usage: 321.0 kWh Total Feed-In: 41.5 kWh</body></html>",
                    "<html><body>Amount Due: $123.45</body></html>",
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
