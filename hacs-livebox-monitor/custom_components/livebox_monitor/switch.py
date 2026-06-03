"""Switch Livebox Monitor — blocage d'appareils."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_API, DATA_COORDINATOR, DOMAIN
from .api import LiveboxAPI
from .coordinator import LiveboxCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: LiveboxCoordinator = data[DATA_COORDINATOR]
    api: LiveboxAPI = data[DATA_API]
    tracked: set[str] = set()

    @callback
    def _add_new() -> None:
        new_entities = []
        for dev in (coordinator.data or {}).get("devices", []):
            mac = dev.get("mac", "")
            if mac and mac not in tracked:
                tracked.add(mac)
                new_entities.append(LiveboxBlockSwitch(coordinator, api, entry, mac))
        if new_entities:
            async_add_entities(new_entities)

    coordinator.async_add_listener(_add_new)
    _add_new()


class LiveboxBlockSwitch(CoordinatorEntity, SwitchEntity):
    """Switch ON = accès autorisé, OFF = bloqué."""

    def __init__(self, coordinator: LiveboxCoordinator, api: LiveboxAPI, entry: ConfigEntry, mac: str) -> None:
        super().__init__(coordinator)
        self._api = api
        self._mac = mac
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_block_{mac.replace(':', '_')}"

    @property
    def _device(self) -> dict:
        return self.coordinator.get_device_by_mac(self._mac) or {}

    @property
    def name(self) -> str:
        dev = self._device
        name = dev.get("name") or self._mac
        return f"{name} — accès réseau"

    @property
    def is_on(self) -> bool:
        return not self._device.get("blocked", False)

    @property
    def icon(self) -> str:
        return "mdi:lan-connect" if self.is_on else "mdi:lan-disconnect"

    async def async_turn_on(self, **kwargs) -> None:
        await self._api.unblock_device(self._mac)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self._api.block_device(self._mac)
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict:
        dev = self._device
        return {
            "mac": self._mac,
            "ip": dev.get("ip"),
            "vendor": dev.get("vendor"),
        }
