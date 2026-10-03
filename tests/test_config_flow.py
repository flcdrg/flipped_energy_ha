"""Tests for flipped_energy config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_API_TOKEN
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.flipped_energy.api import (
    IntegrationBlueprintApiClientAuthenticationError,
)
from custom_components.flipped_energy.const import (
    CONF_CURRENT_RATE_REFRESH_INTERVAL_MINUTES,
    CONF_ENABLE_INVOICES_PAGE,
    CONF_ENABLE_PLAN_PAGE,
    CONF_ENABLE_USAGE_PAGE,
    CONF_INCLUDE_GST,
    CONF_REFRESH_INTERVAL_MINUTES,
    DOMAIN,
)

pytestmark = pytest.mark.asyncio


async def test_user_flow_success(hass) -> None:
    """Test successful config flow setup."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM

    with patch(
        "custom_components.flipped_energy.api.IntegrationBlueprintApiClient.async_get_data",
        new=AsyncMock(
            return_value={
                "plan_name": "Flipped Saver",
                "account_number": "12345678901234",
                "auth_ok": True,
                "data_fresh": True,
            }
        ),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: "fdk_test"},
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Flipped Energy 12345678901234"
    assert result2["data"] == {CONF_API_TOKEN: "fdk_test"}
    assert result2["result"].unique_id == "12345678901234"


async def test_user_flow_auth_error(hass) -> None:
    """Test config flow shows auth error for invalid credentials."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM

    with patch(
        "custom_components.flipped_energy.api.IntegrationBlueprintApiClient.async_get_data",
        new=AsyncMock(
            side_effect=IntegrationBlueprintApiClientAuthenticationError(
                "Invalid credentials"
            )
        ),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: "fdk_bad"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "auth"}


async def test_options_flow_success(hass, mock_config_entry) -> None:
    """Test options flow can persist refresh and page toggles."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_REFRESH_INTERVAL_MINUTES: 45,
            CONF_CURRENT_RATE_REFRESH_INTERVAL_MINUTES: 10,
            CONF_INCLUDE_GST: True,
            CONF_ENABLE_PLAN_PAGE: True,
            CONF_ENABLE_USAGE_PAGE: True,
            CONF_ENABLE_INVOICES_PAGE: False,
        },
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_REFRESH_INTERVAL_MINUTES] == 45
    assert result2["data"][CONF_CURRENT_RATE_REFRESH_INTERVAL_MINUTES] == 10
    assert result2["data"][CONF_INCLUDE_GST] is True
    assert result2["data"][CONF_ENABLE_INVOICES_PAGE] is False


async def test_options_flow_requires_at_least_one_page(hass, mock_config_entry) -> None:
    """Test options flow validates page selection."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_REFRESH_INTERVAL_MINUTES: 30,
            CONF_CURRENT_RATE_REFRESH_INTERVAL_MINUTES: 10,
            CONF_INCLUDE_GST: False,
            CONF_ENABLE_PLAN_PAGE: False,
            CONF_ENABLE_USAGE_PAGE: False,
            CONF_ENABLE_INVOICES_PAGE: False,
        },
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "select_at_least_one_page"}


async def test_entry_with_username_and_password_asks_for_a_token(hass) -> None:
    """An entry from before the developer API starts a reauth asking for a token."""
    legacy = MockConfigEntry(
        domain=DOMAIN,
        title="user@example.com",
        unique_id="user-example-com",
        data={"username": "user@example.com", "password": "secret"},
    )
    legacy.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(legacy.entry_id)
    await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress()
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]
    assert flows[0]["step_id"] == "reauth_confirm"

    with (
        patch(
            "custom_components.flipped_energy.api.IntegrationBlueprintApiClient.async_get_data",
            new=AsyncMock(return_value={"account_number": "12345678901234"}),
        ),
        patch(
            "custom_components.flipped_energy.async_setup_entry",
            new=AsyncMock(return_value=True),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            flows[0]["flow_id"], {CONF_API_TOKEN: "fdk_new"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert legacy.data == {CONF_API_TOKEN: "fdk_new"}
