"""Tests for flipped_energy config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType

from custom_components.flipped_energy.api import (
    IntegrationBlueprintApiClientAuthenticationError,
)
from custom_components.flipped_energy.const import (
    CONF_ENABLE_INVOICES_PAGE,
    CONF_ENABLE_PLAN_PAGE,
    CONF_ENABLE_USAGE_PAGE,
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
                "auth_ok": True,
                "data_fresh": True,
            }
        ),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "secret",
            },
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "user@example.com"
    assert result2["data"][CONF_USERNAME] == "user@example.com"


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
            {
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "bad-secret",
            },
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
            CONF_ENABLE_PLAN_PAGE: True,
            CONF_ENABLE_USAGE_PAGE: True,
            CONF_ENABLE_INVOICES_PAGE: False,
        },
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_REFRESH_INTERVAL_MINUTES] == 45
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
            CONF_ENABLE_PLAN_PAGE: False,
            CONF_ENABLE_USAGE_PAGE: False,
            CONF_ENABLE_INVOICES_PAGE: False,
        },
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "select_at_least_one_page"}
