"""Config & options flow for the Tapo IR Hub integration.

Every form re-renders with the user's most recent input as *suggested values*
(via :meth:`add_suggested_values_to_schema`) so a validation error never wipes
what someone just typed. The integration supports the full set of UI tools:
initial setup, reauthentication, reconfiguration, and an options dialog.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import TapoIrApi, TapoIrAuthError, TapoIrError
from .const import (
    CONF_NAME_OVERRIDES,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def _connection_schema() -> vol.Schema:
    """Host + credentials, with masked password and email-typed username."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST): TextSelector(),
            vol.Required(CONF_USERNAME): TextSelector(
                TextSelectorConfig(type=TextSelectorType.EMAIL)
            ),
            vol.Required(CONF_PASSWORD): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        }
    )


def _credentials_schema() -> vol.Schema:
    """Username + password only (used for reauth)."""
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME): TextSelector(
                TextSelectorConfig(type=TextSelectorType.EMAIL)
            ),
            vol.Required(CONF_PASSWORD): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        }
    )


def _options_schema() -> vol.Schema:
    """Scan interval (number box) + free-text JSON name overrides."""
    return vol.Schema(
        {
            vol.Required(CONF_SCAN_INTERVAL): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    max=3600,
                    step=10,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Optional(CONF_NAME_OVERRIDES): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT, multiline=True)
            ),
        }
    )


async def _validate(data: dict[str, Any]) -> TapoIrApi:
    """Try to connect and enumerate; raises on failure."""
    api = TapoIrApi(
        host=data[CONF_HOST],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
    )
    try:
        await api.async_connect()
        await api.async_enumerate()
    finally:
        await api.async_close()
    return api


def _validate_overrides(raw: str) -> str | None:
    """Return an error key if the overrides string isn't a JSON object."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except ValueError:
        return "invalid_overrides"
    return None if isinstance(parsed, dict) else "invalid_overrides"


class TapoIrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the UI config flow (setup, reauth, reconfigure)."""

    VERSION = 1

    async def _try_connect(
        self, user_input: dict[str, Any]
    ) -> tuple[TapoIrApi | None, dict[str, str]]:
        """Validate credentials, mapping failures to form error keys."""
        errors: dict[str, str] = {}
        api: TapoIrApi | None = None
        try:
            api = await _validate(user_input)
        except TapoIrAuthError:
            errors["base"] = "invalid_auth"
        except TapoIrError:
            errors["base"] = "cannot_connect"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error validating Tapo IR hub")
            errors["base"] = "unknown"
        return api, errors

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            api, errors = await self._try_connect(user_input)
            if api is not None:
                await self.async_set_unique_id(api.hub_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=api.hub_name, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _connection_schema(), user_input or {}
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            merged = {**entry.data, **user_input}
            api, errors = await self._try_connect(merged)
            if api is not None:
                await self.async_set_unique_id(api.hub_id)
                self._abort_if_unique_id_mismatch(reason="wrong_hub")
                return self.async_update_reload_and_abort(entry, data=merged)

        suggested = {CONF_USERNAME: entry.data.get(CONF_USERNAME, "")}
        if user_input:
            suggested.update(user_input)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                _credentials_schema(), suggested
            ),
            errors=errors,
            description_placeholders={CONF_HOST: entry.data.get(CONF_HOST, "")},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user change host/credentials without removing the entry."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            api, errors = await self._try_connect(user_input)
            if api is not None:
                await self.async_set_unique_id(api.hub_id)
                self._abort_if_unique_id_mismatch(reason="wrong_hub")
                return self.async_update_reload_and_abort(entry, data=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _connection_schema(), user_input or dict(entry.data)
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return TapoIrOptionsFlow()


class TapoIrOptionsFlow(OptionsFlow):
    """Scan interval + name overrides (input preserved across errors)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            error = _validate_overrides(user_input.get(CONF_NAME_OVERRIDES, ""))
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                        CONF_NAME_OVERRIDES: (
                            user_input.get(CONF_NAME_OVERRIDES, "") or ""
                        ).strip(),
                    },
                )

        options = self.config_entry.options
        suggested: dict[str, Any] = {
            CONF_SCAN_INTERVAL: options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            CONF_NAME_OVERRIDES: options.get(CONF_NAME_OVERRIDES, ""),
        }
        if user_input is not None:
            suggested.update(user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _options_schema(), suggested
            ),
            errors=errors,
        )
