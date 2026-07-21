"""Adds config flow for Blueprint."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration
from slugify import slugify

from .api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientAuthenticationError,
    IntegrationBlueprintApiClientCommunicationError,
    IntegrationBlueprintApiClientError,
)
from .const import (
    CONF_ENABLE_INVOICES_PAGE,
    CONF_ENABLE_PLAN_PAGE,
    CONF_ENABLE_USAGE_PAGE,
    CONF_REFRESH_INTERVAL_MINUTES,
    DEFAULT_REFRESH_INTERVAL_MINUTES,
    DOMAIN,
    LOGGER,
    MAX_REFRESH_INTERVAL_MINUTES,
    MIN_REFRESH_INTERVAL_MINUTES,
)


class BlueprintFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                await self._test_credentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except IntegrationBlueprintApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except IntegrationBlueprintApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except IntegrationBlueprintApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    ## Do NOT use this in production code
                    ## The unique_id should never be something that can change
                    ## https://developers.home-assistant.io/docs/config_entries_config_flow_handler#unique-ids
                    unique_id=slugify(user_input[CONF_USERNAME])
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=user_input,
                )

        integration = async_get_loaded_integration(self.hass, DOMAIN)
        assert integration.documentation is not None, (  # noqa: S101
            "Integration documentation URL is not set in manifest.json"
        )

        return self.async_show_form(
            step_id="user",
            description_placeholders={
                "documentation_url": integration.documentation,
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )

    async def _test_credentials(self, username: str, password: str) -> None:
        """Validate credentials."""
        client = IntegrationBlueprintApiClient(
            username=username,
            password=password,
            session=async_get_clientsession(self.hass),
        )
        await client.async_get_data()

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
