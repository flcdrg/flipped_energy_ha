"""Tests for flipped_energy API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.flipped_energy.api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientAuthenticationError,
)
from custom_components.flipped_energy.const import (
    SNAPSHOT_ACCOUNT_NUMBER,
    SNAPSHOT_FEEDIN_RATE_BLOCKS,
    SNAPSHOT_FEEDIN_RATE_CENTS,
    SNAPSHOT_IMPORT_RATE_BLOCKS,
    SNAPSHOT_IMPORT_RATE_CENTS,
    SNAPSHOT_METER_NMI,
    SNAPSHOT_SUPPLY_CHARGE_DAILY_CENTS,
    SNAPSHOT_SUPPLY_CHARGE_DAILY_INCL_GST_CENTS,
    SNAPSHOT_USAGE_FEEDIN_YESTERDAY_KWH,
    SNAPSHOT_USAGE_PERIOD_END,
    SNAPSHOT_USAGE_PERIOD_START,
    SNAPSHOT_USAGE_TODAY_KWH,
)

pytestmark = pytest.mark.asyncio


def _response(status: int, payload: object) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.headers = {}
    response.json = AsyncMock(return_value=payload)
    response.raise_for_status = MagicMock()
    return response


async def test_requests_use_developer_api_base_and_bearer_token() -> None:
    """Every call goes to the developer API with the token as a bearer header."""
    session = MagicMock()
    session.request = AsyncMock(return_value=_response(200, {"ok": True}))
    client = IntegrationBlueprintApiClient("fdk_test", session)

    assert await client._fetch_api_json("/api/MyAccount/ProjectAccountData") == {
        "ok": True
    }

    session.request.assert_awaited_once()
    kwargs = session.request.await_args.kwargs
    assert (
        kwargs["url"]
        == "https://mcp-api.flipped.energy/developer/v1/api/MyAccount/ProjectAccountData"
    )
    assert kwargs["headers"] == {"Authorization": "Bearer fdk_test"}


async def test_refused_token_raises_auth_error_instead_of_skipping_paths() -> None:
    """A 401 surfaces as an auth error (reauth), not as missing snapshot fields."""
    session = MagicMock()
    session.request = AsyncMock(return_value=_response(401, {"title": "token revoked"}))
    client = IntegrationBlueprintApiClient("fdk_revoked", session)

    with pytest.raises(IntegrationBlueprintApiClientAuthenticationError):
        await client.async_get_data()


async def test_snapshot_does_not_fetch_reads_or_settlements() -> None:
    """The snapshot skips getreads and getsettlements: no sensor used them."""
    session = MagicMock()
    session.request = AsyncMock(return_value=_response(200, []))
    client = IntegrationBlueprintApiClient("fdk_test", session)

    await client._fetch_api_snapshot_payloads(
        {"plan": True, "usage": True, "invoices": True}
    )

    urls = [call.kwargs["url"] for call in session.request.await_args_list]
    assert urls
    assert all(
        url.startswith("https://mcp-api.flipped.energy/developer/v1/api/")
        for url in urls
    )
    assert not [url for url in urls if "getreads" in url or "getsettlements" in url]


async def test_extract_hourly_usage_metrics_uses_latest_completed_day() -> None:
    """Test hourly usage rows produce the latest historical usage period."""
    client = IntegrationBlueprintApiClient("fdk_test", None)

    snapshot = client._extract_hourly_usage_metrics(
        [
            {
                "time": "2026-07-19T23:00:00",
                "value": 1.0,
                "usageType": "Export",
            },
            {
                "time": "2026-07-20T00:00:00",
                "value": 2.0,
                "usageType": "Export",
            },
            {
                "time": "2026-07-20T01:00:00",
                "value": 3.5,
                "usageType": "Export",
            },
            {
                "time": "2026-07-20T02:00:00",
                "value": 0.5,
                "usageType": "Import",
            },
        ]
    )

    assert snapshot[SNAPSHOT_USAGE_TODAY_KWH] == 5.5
    assert snapshot[SNAPSHOT_USAGE_FEEDIN_YESTERDAY_KWH] == 0.5
    assert snapshot[SNAPSHOT_USAGE_PERIOD_START] == "2026-07-20T00:00:00"
    assert snapshot[SNAPSHOT_USAGE_PERIOD_END] == "2026-07-20"


async def test_extract_usage_totals_uses_all_rows() -> None:
    """Test weekly and monthly usage rows produce period totals."""
    client = IntegrationBlueprintApiClient("fdk_test", None)

    snapshot = client._extract_usage_totals(
        [
            {"time": "2026-07-01T00:00:00", "value": 1.0, "usageType": "Export"},
            {"time": "2026-07-01T01:00:00", "value": 2.5, "usageType": "Export"},
            {"time": "2026-07-01T02:00:00", "value": 0.4, "usageType": "Import"},
        ]
    )

    assert snapshot is not None
    assert snapshot["usage_kwh"] == 3.5
    assert snapshot["feedin_kwh"] == 0.4


async def test_extract_rates_includes_time_of_day_and_supply_charge() -> None:
    """Test rate extraction includes TOD blocks and daily supply charges."""
    client = IntegrationBlueprintApiClient("fdk_test", None)

    snapshot = client._map_snapshot_from_known_api_payloads(
        {
            "/api/MyAccount/ProjectAccountData": {
                "accounts": [
                    {
                        "accountNumber": "ACC-123456",
                        "productName": "Flipped Saver",
                        "product": {
                            "currentPlan": {
                                "billingUnits": [
                                    {
                                        "billingUnitType": "Usage",
                                        "name": "Day",
                                        "chargePerKwh": 0.0993,
                                        "timeOfDayStartMinutes": 540,
                                        "timeOfDayEndMinutes": 1020,
                                    },
                                    {
                                        "billingUnitType": "Usage",
                                        "name": "Evening",
                                        "chargePerKwh": 0.5762,
                                        "timeOfDayStartMinutes": 1020,
                                        "timeOfDayEndMinutes": 1260,
                                    },
                                    {
                                        "billingUnitType": "Usage",
                                        "name": "Night",
                                        "chargePerKwh": 0.3599,
                                        "timeOfDayStartMinutes": 1260,
                                        "timeOfDayEndMinutes": 540,
                                    },
                                    {
                                        "billingUnitType": "FeedInTariff",
                                        "name": "Solar Feed In Tariff",
                                        "chargePerKwh": -0.02,
                                        "timeOfDayStartMinutes": 0,
                                        "timeOfDayEndMinutes": 0,
                                    },
                                    {
                                        "billingUnitType": "SupplyCharge",
                                        "name": "Supply charge (excl GST)",
                                        "period": "Daily",
                                        "periodicCharge": 1.1,
                                    },
                                    {
                                        "billingUnitType": "SupplyCharge",
                                        "name": "Supply charge (incl GST)",
                                        "period": "Daily",
                                        "periodicCharge": 1.21,
                                    },
                                ]
                            }
                        },
                    }
                ]
            },
            "/api/Usage/usage/projectreads/daily": [
                {
                    "time": "2026-07-01T00:00:00",
                    "value": 1.0,
                    "usageType": "Export",
                    "nmi": "NMI-1234567890",
                }
            ],
        }
    )

    assert snapshot[SNAPSHOT_ACCOUNT_NUMBER] == "ACC-123456"
    assert snapshot[SNAPSHOT_METER_NMI] == "NMI-1234567890"
    assert snapshot[SNAPSHOT_IMPORT_RATE_CENTS] == 30.908333
    assert snapshot[SNAPSHOT_FEEDIN_RATE_CENTS] == 2.0
    assert snapshot[SNAPSHOT_SUPPLY_CHARGE_DAILY_CENTS] == 110.0
    assert snapshot[SNAPSHOT_SUPPLY_CHARGE_DAILY_INCL_GST_CENTS] == 121.0

    import_blocks = snapshot[SNAPSHOT_IMPORT_RATE_BLOCKS]
    assert isinstance(import_blocks, list)
    assert len(import_blocks) == 3
    assert import_blocks[0]["name"] == "Day"
    assert import_blocks[0]["start_time"] == "09:00"
    assert import_blocks[0]["end_time"] == "17:00"
    assert import_blocks[0]["rate_cents_kwh"] == 9.93

    feedin_blocks = snapshot[SNAPSHOT_FEEDIN_RATE_BLOCKS]
    assert isinstance(feedin_blocks, list)
    assert len(feedin_blocks) == 1
    assert feedin_blocks[0]["start_time"] == "00:00"
    assert feedin_blocks[0]["end_time"] == "00:00"
    assert feedin_blocks[0]["rate_cents_kwh"] == 2.0
