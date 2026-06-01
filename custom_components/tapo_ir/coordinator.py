"""Coordinator: the async re-query task for a Tapo IR hub.

The coordinator owns the periodic enumeration of the hub's child IR remotes and
exposes a stable ``data`` mapping (keyed by ``device_id``) that the button and
sensor platforms consume. It also proxies IR fires down to the API layer.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import TapoIrApi, TapoIrAuthError, TapoIrError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TapoIrCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Periodically re-enumerate the hub and cache its child remotes."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: TapoIrApi,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} ({api.host})",
            update_interval=timedelta(seconds=scan_interval),
            always_update=False,
        )
        self.api = api
        self.last_scan: datetime | None = None

    @property
    def hub_id(self) -> str:
        """Stable unique id for the hub device."""
        return self.api.hub_id or self.api.host

    @property
    def hub_name(self) -> str:
        return self.api.hub_name

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Re-query the hub for its current child remotes + keys."""
        try:
            devices = await self.api.async_enumerate()
        except TapoIrAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except TapoIrError as err:
            raise UpdateFailed(str(err)) from err
        self.last_scan = dt_util.utcnow()
        return {device["device_id"]: device for device in devices}

    async def async_fire(self, device_id: str, key_name: str) -> None:
        """Fire a single stored IR key on a child remote."""
        try:
            await self.api.async_fire(device_id, key_name)
        except TapoIrError as err:
            raise UpdateFailed(str(err)) from err
