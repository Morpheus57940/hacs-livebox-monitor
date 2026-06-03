"""Binary sensors Livebox Monitor."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import LiveboxCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: LiveboxCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities = [
        LiveboxConnectivitySensor(coordinator, entry),
        LiveboxUnknownDeviceAlertSensor(coordinator, entry),
    ]
    async_add_entities(entities)


class LiveboxConnectivitySensor(CoordinatorEntity, BinarySensorEntity):
    _attr_name = "Livebox connectivité"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:router-network"

    def __init__(self, coordinator: LiveboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_connectivity"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Livebox",
            "manufacturer": "Orange",
            "model": "Livebox",
        }

    @property
    def is_on(self) -> bool:
        wan = (self.coordinator.data or {}).get("wan_status", {})
        return wan.get("WanState", "") == "up"


class LiveboxUnknownDeviceAlertSensor(CoordinatorEntity, BinarySensorEntity):
    _attr_name = "Livebox appareil inconnu détecté"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert-network"

    def __init__(self, coordinator: LiveboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_unknown_alert"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Livebox",
            "manufacturer": "Orange",
            "model": "Livebox",
        }

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        return data.get("unknown_count", 0) > 0

    @property
    def extra_state_attributes(self):
        devices = (self.coordinator.data or {}).get("devices", [])
        unknowns = [
            {"mac": d["mac"], "ip": d["ip"], "last_seen": d["last_seen"]}
            for d in devices
            if d.get("unknown") and d.get("active")
        ]
        return {"unknown_devices": unknowns}
