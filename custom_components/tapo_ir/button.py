"""Button platform: one button per IR key, plus a hub Rescan button."""
from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, HUB_MODEL, MANUFACTURER, REMOTE_MODEL
from .coordinator import TapoIrCoordinator


def _hub_device_info(coordinator: TapoIrCoordinator) -> DeviceInfo:
    """Identity for the hub itself (the system-wide controller device)."""
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.hub_id)},
        name=coordinator.hub_name,
        manufacturer=MANUFACTURER,
        model=coordinator.api.hub_model or HUB_MODEL,
        sw_version=coordinator.api.hub_fw,
    )


def _child_device_info(
    coordinator: TapoIrCoordinator, device: dict[str, Any]
) -> DeviceInfo:
    """Identity for a child IR remote, linked to the hub via via_device."""
    return DeviceInfo(
        identifiers={(DOMAIN, device["device_id"])},
        name=device["name"],
        manufacturer=MANUFACTURER,
        model=device.get("model") or REMOTE_MODEL,
        via_device=(DOMAIN, coordinator.hub_id),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the hub Rescan button and dynamically-discovered IR key buttons."""
    coordinator: TapoIrCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([TapoIrRescanButton(coordinator)])

    known: set[str] = set()

    @callback
    def _add_new_keys() -> None:
        new_entities: list[TapoIrKeyButton] = []
        for device in (coordinator.data or {}).values():
            for key in device["keys"]:
                unique_id = f"{device['device_id']}_{key['slug']}"
                if unique_id in known:
                    continue
                known.add(unique_id)
                new_entities.append(
                    TapoIrKeyButton(coordinator, device, key, unique_id)
                )
        if new_entities:
            async_add_entities(new_entities)

    _add_new_keys()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_keys))


class TapoIrKeyButton(CoordinatorEntity[TapoIrCoordinator], ButtonEntity):
    """A single stored IR key, fired via sendIrCmdById."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TapoIrCoordinator,
        device: dict[str, Any],
        key: dict[str, Any],
        unique_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device["device_id"]
        self._key_name = key["name"]
        self._attr_unique_id = unique_id
        self._attr_name = key["label"]
        self._attr_icon = key["icon"]
        self._attr_device_info = _child_device_info(coordinator, device)

    @property
    def available(self) -> bool:
        """Available while its parent device is still present in the scan."""
        return (
            super().available
            and self._device_id in (self.coordinator.data or {})
        )

    async def async_press(self) -> None:
        await self.coordinator.async_fire(self._device_id, self._key_name)


class TapoIrRescanButton(CoordinatorEntity[TapoIrCoordinator], ButtonEntity):
    """Hub-level button that forces an immediate re-query of the hub."""

    _attr_has_entity_name = True
    _attr_name = "Rescan devices"
    _attr_icon = "mdi:magnify-scan"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: TapoIrCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.hub_id}_rescan"
        self._attr_device_info = _hub_device_info(coordinator)

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
