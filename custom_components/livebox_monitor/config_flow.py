"""Config flow pour Livebox Monitor."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LiveboxAPI, LiveboxAuthError, LiveboxConnectionError
from .const import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            int, vol.Range(min=10, max=300)
        ),
        vol.Optional("track_new_devices", default=True): bool,
        vol.Optional("notify_unknown_devices", default=True): bool,
    }
)


class LiveboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Flux de configuration Livebox Monitor."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Étape initiale : saisie des informations de connexion."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = LiveboxAPI(
                host=user_input[CONF_HOST],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                session=session,
                port=user_input.get(CONF_PORT, DEFAULT_PORT),
            )
            try:
                await api.authenticate()
                info = await api.get_device_info()
                serial = info.get("SerialNumber", user_input[CONF_HOST])
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Livebox ({user_input[CONF_HOST]})",
                    data=user_input,
                )
            except LiveboxAuthError:
                errors["base"] = "invalid_auth"
            except LiveboxConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Erreur inattendue lors de la configuration")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"default_host": DEFAULT_HOST},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return LiveboxOptionsFlow(config_entry)


class LiveboxOptionsFlow(config_entries.OptionsFlow):
    """Flux d'options (paramètres modifiables après installation)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(int, vol.Range(min=10, max=300)),
                vol.Optional(
                    "track_new_devices",
                    default=current.get("track_new_devices", True),
                ): bool,
                vol.Optional(
                    "notify_unknown_devices",
                    default=current.get("notify_unknown_devices", True),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
