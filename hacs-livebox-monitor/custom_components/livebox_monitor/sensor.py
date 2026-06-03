"""Sensors Livebox Monitor."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN, ICON_DEVICE, ICON_DOWNLOAD, ICON_ROUTER, ICON_UPLOAD, ICON_WIFI
from .coordinator import LiveboxCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: LiveboxCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities = [
        LiveboxOnlineCountSensor(coordinator, entry),
        LiveboxUnknownCountSensor(coordinator, entry),
        LiveboxBlockedCountSensor(coordinator, entry),
        LiveboxWanStatusSensor(coordinator, entry),
        LiveboxUptimeSensor(coordinator, entry),
    ]
    async_add_entities(entities)


class LiveboxBaseSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: LiveboxCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Livebox",
            "manufacturer": "Orange",
            "model": "Livebox",
        }

    @property
    def data(self):
        return self.coordinator.data or {}


class LiveboxOnlineCountSensor(LiveboxBaseSensor):
    _attr_name = "Livebox appareils connectés"
    _attr_icon = ICON_DEVICE
    _attr_native_unit_of_measurement = "appareils"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "online_count")

    @property
    def native_value(self):
        return self.data.get("online_count", 0)

    @property
    def extra_state_attributes(self):
        devices = self.data.get("devices", [])
        return {
            "total": len(devices),
            "unknown": self.data.get("unknown_count", 0),
            "blocked": self.data.get("blocked_count", 0),
        }


class LiveboxUnknownCountSensor(LiveboxBaseSensor):
    _attr_name = "Livebox appareils inconnus"
    _attr_icon = "mdi:help-network"
    _attr_native_unit_of_measurement = "appareils"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "unknown_count")

    @property
    def native_value(self):
        return self.data.get("unknown_count", 0)


class LiveboxBlockedCountSensor(LiveboxBaseSensor):
    _attr_name = "Livebox appareils bloqués"
    _attr_icon = "mdi:block-helper"
    _attr_native_unit_of_measurement = "appareils"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "blocked_count")

    @property
    def native_value(self):
        return self.data.get("blocked_count", 0)


class LiveboxWanStatusSensor(LiveboxBaseSensor):
    _attr_name = "Livebox statut WAN"
    _attr_icon = ICON_ROUTER

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "wan_status")

    @property
    def native_value(self):
        wan = self.data.get("wan_status", {})
        return wan.get("LinkState", "unknown")

    @property
    def extra_state_attributes(self):
        wan = self.data.get("wan_status", {})
        return {
            "wan_state": wan.get("WanState"),
            "link_type": wan.get("LinkType"),
            "ip_address": wan.get("IPAddress"),
            "ipv6_address": wan.get("IPv6Address"),
            "dns_servers": wan.get("DNSServers"),
            "uptime": wan.get("UpTime"),
        }


class LiveboxUptimeSensor(LiveboxBaseSensor):
    _attr_name = "Livebox uptime"
    _attr_icon = ICON_ROUTER
    _attr_native_unit_of_measurement = "s"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "uptime")

    @property
    def native_value(self):
        info = self.data.get("device_info", {})
        return info.get("UpTime", 0)
