"""Adds config flow for Blueprint."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_TOKEN
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientAuthenticationError,
    IntegrationBlueprintApiClientCommunicationError,
    IntegrationBlueprintApiClientError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

from .const import (
    CONF_CURRENT_RATE_REFRESH_INTERVAL_MINUTES,
    CONF_ENABLE_INVOICES_PAGE,
    CONF_ENABLE_PLAN_PAGE,
    CONF_ENABLE_USAGE_PAGE,
    CONF_INCLUDE_GST,
    CONF_REFRESH_INTERVAL_MINUTES,
    DEFAULT_CURRENT_RATE_REFRESH_INTERVAL_MINUTES,
    DEFAULT_INCLUDE_GST,
    DEFAULT_REFRESH_INTERVAL_MINUTES,
    DOMAIN,
    LOGGER,
    MAX_CURRENT_RATE_REFRESH_INTERVAL_MINUTES,
    MAX_REFRESH_INTERVAL_MINUTES,
    MIN_CURRENT_RATE_REFRESH_INTERVAL_MINUTES,
    MIN_REFRESH_INTERVAL_MINUTES,
    SNAPSHOT_ACCOUNT_NUMBER,
)

DEVELOPER_PORTAL_URL = "https://flipped.energy/accounts/developer"

TOKEN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
        ),
    }
)


class BlueprintFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            snapshot = await self._snapshot_or_error(user_input[CONF_API_TOKEN], errors)
            if snapshot is not None:
                account_number = snapshot[SNAPSHOT_ACCOUNT_NUMBER]
                await self.async_set_unique_id(str(account_number))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Flipped Energy {account_number}",
                    data={CONF_API_TOKEN: user_input[CONF_API_TOKEN]},
                )

        integration = async_get_loaded_integration(self.hass, DOMAIN)
        assert integration.documentation is not None, (  # noqa: S101
            "Integration documentation URL is not set in manifest.json"
        )

        return self.async_show_form(
            step_id="user",
            description_placeholders={
                "documentation_url": integration.documentation,
                "token_url": DEVELOPER_PORTAL_URL,
            },
            data_schema=TOKEN_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, Any],  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Ask for a developer API token when the stored one is refused or missing."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Validate the new token and store it on the existing entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            snapshot = await self._snapshot_or_error(user_input[CONF_API_TOKEN], errors)
            if snapshot is not None:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data={CONF_API_TOKEN: user_input[CONF_API_TOKEN]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={"token_url": DEVELOPER_PORTAL_URL},
            data_schema=TOKEN_SCHEMA,
            errors=errors,
        )

    async def _snapshot_or_error(
        self, api_token: str, errors: dict[str, str]
    ) -> dict[str, Any] | None:
        """Fetch a snapshot with the token; on failure fill errors and return None."""
        client = IntegrationBlueprintApiClient(
            api_token=api_token,
            session=async_get_clientsession(self.hass),
        )
        try:
            snapshot = await client.async_get_data()
        except IntegrationBlueprintApiClientAuthenticationError as exception:
            LOGGER.warning(exception)
            errors["base"] = "auth"
        except IntegrationBlueprintApiClientCommunicationError as exception:
            LOGGER.error(exception)
            errors["base"] = "connection"
        except IntegrationBlueprintApiClientError as exception:
            LOGGER.exception(exception)
            errors["base"] = "unknown"
        else:
            if snapshot.get(SNAPSHOT_ACCOUNT_NUMBER) is None:
                errors["base"] = "no_account"
                return None
            return snapshot
        return None

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return BlueprintOptionsFlow(config_entry)


class BlueprintOptionsFlow(config_entries.OptionsFlow):
    """Handle options for the integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage the integration options."""
        if user_input is not None:
            selected_pages = (
                user_input.get(CONF_ENABLE_PLAN_PAGE, True),
                user_input.get(CONF_ENABLE_USAGE_PAGE, True),
                user_input.get(CONF_ENABLE_INVOICES_PAGE, True),
            )
            if not any(selected_pages):
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._build_schema(user_input),
                    errors={"base": "select_at_least_one_page"},
                )
            return self.async_create_entry(title="", data=user_input)

        defaults = {
            CONF_REFRESH_INTERVAL_MINUTES: self._config_entry.options.get(
                CONF_REFRESH_INTERVAL_MINUTES,
                DEFAULT_REFRESH_INTERVAL_MINUTES,
            ),
            CONF_CURRENT_RATE_REFRESH_INTERVAL_MINUTES: self._config_entry.options.get(
                CONF_CURRENT_RATE_REFRESH_INTERVAL_MINUTES,
                DEFAULT_CURRENT_RATE_REFRESH_INTERVAL_MINUTES,
            ),
            CONF_INCLUDE_GST: self._config_entry.options.get(
                CONF_INCLUDE_GST,
                DEFAULT_INCLUDE_GST,
            ),
            CONF_ENABLE_PLAN_PAGE: self._config_entry.options.get(
                CONF_ENABLE_PLAN_PAGE,
                True,
            ),
            CONF_ENABLE_USAGE_PAGE: self._config_entry.options.get(
                CONF_ENABLE_USAGE_PAGE,
                True,
            ),
            CONF_ENABLE_INVOICES_PAGE: self._config_entry.options.get(
                CONF_ENABLE_INVOICES_PAGE,
                True,
            ),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=self._build_schema(defaults),
            errors={},
        )

    def _build_schema(self, defaults: dict) -> vol.Schema:
        """Build the options form schema."""
        return vol.Schema(
            {
                vol.Required(
                    CONF_REFRESH_INTERVAL_MINUTES,
                    default=defaults.get(
                        CONF_REFRESH_INTERVAL_MINUTES,
                        DEFAULT_REFRESH_INTERVAL_MINUTES,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_REFRESH_INTERVAL_MINUTES,
                        max=MAX_REFRESH_INTERVAL_MINUTES,
                        mode=selector.NumberSelectorMode.BOX,
                        step=1,
                    )
                ),
                vol.Required(
                    CONF_CURRENT_RATE_REFRESH_INTERVAL_MINUTES,
                    default=defaults.get(
                        CONF_CURRENT_RATE_REFRESH_INTERVAL_MINUTES,
                        DEFAULT_CURRENT_RATE_REFRESH_INTERVAL_MINUTES,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_CURRENT_RATE_REFRESH_INTERVAL_MINUTES,
                        max=MAX_CURRENT_RATE_REFRESH_INTERVAL_MINUTES,
                        mode=selector.NumberSelectorMode.BOX,
                        step=1,
                    )
                ),
                vol.Required(
                    CONF_INCLUDE_GST,
                    default=defaults.get(CONF_INCLUDE_GST, DEFAULT_INCLUDE_GST),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_ENABLE_PLAN_PAGE,
                    default=defaults.get(CONF_ENABLE_PLAN_PAGE, True),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_ENABLE_USAGE_PAGE,
                    default=defaults.get(CONF_ENABLE_USAGE_PAGE, True),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_ENABLE_INVOICES_PAGE,
                    default=defaults.get(CONF_ENABLE_INVOICES_PAGE, True),
                ): selector.BooleanSelector(),
            }
        )
