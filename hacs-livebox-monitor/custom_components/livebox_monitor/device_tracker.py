"""Device Tracker Livebox Monitor — suivi de présence Wi-Fi."""
from __future__ import annotations

import logging

from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import LiveboxCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: LiveboxCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    tracked: set[str] = set()

    @callback
    def _add_new_devices() -> None:
        new_entities = []
        for dev in (coordinator.data or {}).get("devices", []):
            mac = dev.get("mac", "")
            if mac and mac not in tracked:
                tracked.add(mac)
                new_entities.append(LiveboxDeviceTracker(coordinator, entry, mac))
        if new_entities:
            async_add_entities(new_entities)

    coordinator.async_add_listener(_add_new_devices)
    _add_new_devices()


class LiveboxDeviceTracker(CoordinatorEntity, ScannerEntity):
    """Tracker pour un appareil du réseau Livebox."""

    def __init__(self, coordinator: LiveboxCoordinator, entry: ConfigEntry, mac: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_tracker_{mac.replace(':', '_')}"

    @property
    def _device(self) -> dict:
        return self.coordinator.get_device_by_mac(self._mac) or {}

    @property
    def name(self) -> str:
        dev = self._device
        return dev.get("name") or self._mac

    @property
    def is_connected(self) -> bool:
        return self._device.get("active", False)

    @property
    def source_type(self) -> SourceType:
        link = self._device.get("link_type", "")
        if "wifi" in link.lower() or "wlan" in link.lower():
            return SourceType.ROUTER
        return SourceType.ROUTER

    @property
    def ip_address(self) -> str | None:
        return self._device.get("ip") or None

    @property
    def mac_address(self) -> str:
        return self._mac

    @property
    def hostname(self) -> str | None:
        return self._device.get("dhcp_name") or None

    @property
    def icon(self) -> str:
        dev = self._device
        link = dev.get("link_type", "").lower()
        if "wifi" in link or "wlan" in link:
            return "mdi:wifi" if dev.get("active") else "mdi:wifi-off"
        return "mdi:ethernet" if dev.get("active") else "mdi:ethernet-off"

    @property
    def extra_state_attributes(self) -> dict:
        dev = self._device
        return {
            "mac": self._mac,
            "ip": dev.get("ip"),
            "link_type": dev.get("link_type"),
            "vendor": dev.get("vendor"),
            "first_seen": dev.get("first_seen"),
            "last_seen": dev.get("last_seen"),
            "blocked": dev.get("blocked"),
            "rssi": dev.get("rssi"),
        }
