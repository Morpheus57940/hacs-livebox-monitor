"""Intégration Livebox Monitor pour Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .api import LiveboxAPI
from .const import (
    DATA_API,
    DATA_COORDINATOR,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
    SERVICE_ASSIGN_NAME,
    SERVICE_BLOCK_DEVICE,
    SERVICE_REBOOT,
    SERVICE_SCAN,
    SERVICE_UNBLOCK_DEVICE,
)
from .coordinator import LiveboxCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialiser l'intégration depuis une config entry."""
    session = async_get_clientsession(hass)
    api = LiveboxAPI(
        host=entry.data[CONF_HOST],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        session=session,
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
    )

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = LiveboxCoordinator(hass, api, scan_interval=scan_interval)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_API: api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _register_services(hass, api)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharger l'intégration."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recharger si les options changent."""
    await hass.config_entries.async_reload(entry.entry_id)


def _register_services(hass: HomeAssistant, api: LiveboxAPI) -> None:
    """Enregistrer les services HA."""

    async def handle_block(call: ServiceCall) -> None:
        mac = call.data["mac"]
        await api.block_device(mac)
        _LOGGER.info("Appareil %s bloqué", mac)

    async def handle_unblock(call: ServiceCall) -> None:
        mac = call.data["mac"]
        await api.unblock_device(mac)
        _LOGGER.info("Appareil %s débloqué", mac)

    async def handle_assign_name(call: ServiceCall) -> None:
        mac = call.data["mac"]
        name = call.data["name"]
        await api.assign_device_name(mac, name)

    async def handle_reboot(call: ServiceCall) -> None:
        _LOGGER.warning("Redémarrage Livebox demandé depuis HA")
        await api.reboot()

    async def handle_scan(call: ServiceCall) -> None:
        await api.scan_network()

    mac_schema = vol.Schema({vol.Required("mac"): cv.string})
    name_schema = vol.Schema({vol.Required("mac"): cv.string, vol.Required("name"): cv.string})

    hass.services.async_register(DOMAIN, SERVICE_BLOCK_DEVICE, handle_block, schema=mac_schema)
    hass.services.async_register(DOMAIN, SERVICE_UNBLOCK_DEVICE, handle_unblock, schema=mac_schema)
    hass.services.async_register(DOMAIN, SERVICE_ASSIGN_NAME, handle_assign_name, schema=name_schema)
    hass.services.async_register(DOMAIN, SERVICE_REBOOT, handle_reboot, schema=vol.Schema({}))
    hass.services.async_register(DOMAIN, SERVICE_SCAN, handle_scan, schema=vol.Schema({}))
