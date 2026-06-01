"""The Tapo IR Hub integration."""
from __future__ import annotations

import json
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api import TapoIrApi, TapoIrAuthError, TapoIrError
from .const import (
    CONF_HOST,
    CONF_NAME_OVERRIDES,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import TapoIrCoordinator

_LOGGER = logging.getLogger(__name__)


def _parse_overrides(raw: str | dict | None) -> dict[str, str]:
    """Accept name overrides as either a dict or a JSON string."""
    if not raw:
        return {}
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    try:
        data = json.loads(raw)
        return {str(k): str(v) for k, v in data.items()}
    except (ValueError, AttributeError):
        _LOGGER.warning("Ignoring malformed name_overrides: %r", raw)
        return {}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tapo IR Hub from a config entry."""
    overrides = _parse_overrides(entry.options.get(CONF_NAME_OVERRIDES))
    api = TapoIrApi(
        host=entry.data[CONF_HOST],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        overrides=overrides,
    )

    try:
        await api.async_connect()
    except TapoIrAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except TapoIrError as err:
        raise ConfigEntryNotReady(str(err)) from err

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = TapoIrCoordinator(hass, entry, api, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator: TapoIrCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.api.async_close()
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change (interval / overrides)."""
    await hass.config_entries.async_reload(entry.entry_id)
