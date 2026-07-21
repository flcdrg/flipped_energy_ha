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
from custom_components.flipped_energy.const import DOMAIN

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
        new=AsyncMock(return_value={"title": "foo", "body": "hello world"}),
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
