"""Client API pour la Livebox Orange (TR-069 / API HTTP locale)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

LIVEBOX_PORT = 80
AUTH_URL = "http://{host}:{port}/authenticate"
WS_URL = "http://{host}:{port}/ws"

SYSBUS_HEADERS = {
    "Content-Type": "application/x-sysbus-json",
    "X-Context": "JSON",
}


class LiveboxAuthError(Exception):
    """Erreur d'authentification Livebox."""


class LiveboxConnectionError(Exception):
    """Erreur de connexion Livebox."""


class LiveboxAPI:
    """Client asynchrone pour l'API Livebox."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        port: int = LIVEBOX_PORT,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._session = session
        self._auth_token: str | None = None
        self._session_id: str | None = None

    # ------------------------------------------------------------------
    # Authentification
    # ------------------------------------------------------------------

    async def authenticate(self) -> bool:
        """S'authentifier auprès de la Livebox et récupérer le token."""
        url = AUTH_URL.format(host=self._host, port=self._port)
        payload = {
            "service": "sah.Device.Information",
            "method": "createContext",
            "parameters": {
                "applicationName": "webui",
                "username": self._username,
                "password": self._password,
            },
        }
        try:
            async with self._session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    raise LiveboxAuthError(f"HTTP {resp.status}")
                data = await resp.json(content_type=None)
                status = data.get("status", 0)
                if status != 0:
                    raise LiveboxAuthError(f"Auth failed, status={status}")
                ctx = data.get("data", {})
                self._auth_token = ctx.get("contextID")
                self._session_id = ctx.get("username")
                _LOGGER.debug("Livebox auth OK, contextID=%s", self._auth_token)
                return True
        except aiohttp.ClientError as exc:
            raise LiveboxConnectionError(str(exc)) from exc

    async def _post(self, service: str, method: str, parameters: dict | None = None) -> Any:
        """Effectuer un appel API JSON vers la Livebox."""
        if not self._auth_token:
            await self.authenticate()

        url = WS_URL.format(host=self._host, port=self._port)
        headers = {
            **SYSBUS_HEADERS,
            "X-Context": self._auth_token or "",
            "Cookie": f"context_id={self._auth_token}",
        }
        payload = {
            "service": service,
            "method": method,
            "parameters": parameters or {},
        }
        try:
            async with self._session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    _LOGGER.debug("Token expiré, ré-authentification…")
                    self._auth_token = None
                    await self.authenticate()
                    return await self._post(service, method, parameters)
                if resp.status != 200:
                    _LOGGER.warning("API %s.%s → HTTP %s", service, method, resp.status)
                    return None
                data = await resp.json(content_type=None)
                return data.get("status")
        except aiohttp.ClientError as exc:
            raise LiveboxConnectionError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Appareils connectés
    # ------------------------------------------------------------------

    async def get_devices(self) -> list[dict]:
        """Retourner la liste de tous les appareils connus."""
        result = await self._post(
            "Devices",
            "get",
            {"expression": {"ETHERNET": "not interface and not self", "WIFI": "not interface and not self"}},
        )
        if not result:
            return []
        devices = []
        for expr_result in (result if isinstance(result, list) else [result]):
            if isinstance(expr_result, list):
                devices.extend(expr_result)
            elif isinstance(expr_result, dict):
                devices.append(expr_result)
        return devices

    async def get_active_devices(self) -> list[dict]:
        """Retourner uniquement les appareils actuellement connectés."""
        all_devices = await self.get_devices()
        return [d for d in all_devices if d.get("Active", False)]

    async def get_device_by_mac(self, mac: str) -> dict | None:
        """Obtenir les détails d'un appareil par son adresse MAC."""
        devices = await self.get_devices()
        mac_upper = mac.upper()
        for device in devices:
            if device.get("PhysAddress", "").upper() == mac_upper:
                return device
        return None

    # ------------------------------------------------------------------
    # Statistiques réseau
    # ------------------------------------------------------------------

    async def get_wan_status(self) -> dict:
        """Statut de la connexion WAN (fibre/ADSL)."""
        result = await self._post("NMC", "getWANStatus", {})
        return result or {}

    async def get_lan_ip_stats(self) -> dict:
        """Statistiques IP LAN."""
        result = await self._post(
            "NeMo.Intf.data",
            "getMIBs",
            {"mibs": "eth", "flag": "", "traverse": "all"},
        )
        return result or {}

    async def get_interfaces_stats(self) -> dict:
        """Statistiques de trafic par interface."""
        result = await self._post(
            "NeMo.Intf.lo",
            "getMIBs",
            {"mibs": "base", "flag": "stat", "traverse": "all"},
        )
        return result or {}

    async def get_wifi_stats(self) -> dict:
        """Informations et statistiques Wi-Fi."""
        result = await self._post(
            "NMC.Wifi",
            "get",
            {},
        )
        return result or {}

    async def get_dhcp_leases(self) -> list[dict]:
        """Baux DHCP actifs."""
        result = await self._post(
            "DHCPv4.Server.Pool.default",
            "getStaticLeases",
            {},
        )
        return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # Informations système
    # ------------------------------------------------------------------

    async def get_device_info(self) -> dict:
        """Informations matérielles de la Livebox."""
        result = await self._post(
            "DeviceInfo",
            "get",
            {},
        )
        return result or {}

    async def get_time(self) -> dict:
        """Heure système de la Livebox."""
        result = await self._post("Time", "getTime", {})
        return result or {}

    async def get_uptime(self) -> int:
        """Uptime en secondes."""
        info = await self.get_device_info()
        return info.get("UpTime", 0)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def block_device(self, mac: str) -> bool:
        """Bloquer un appareil par son adresse MAC."""
        result = await self._post(
            "Devices.Device." + mac.upper(),
            "setParameters",
            {"parameters": {"Blocked": True}},
        )
        return result is not None

    async def unblock_device(self, mac: str) -> bool:
        """Débloquer un appareil par son adresse MAC."""
        result = await self._post(
            "Devices.Device." + mac.upper(),
            "setParameters",
            {"parameters": {"Blocked": False}},
        )
        return result is not None

    async def assign_device_name(self, mac: str, name: str) -> bool:
        """Assigner un nom à un appareil."""
        result = await self._post(
            "Devices.Device." + mac.upper(),
            "setName",
            {"source": "webui", "name": name},
        )
        return result is not None

    async def reboot(self) -> bool:
        """Redémarrer la Livebox."""
        result = await self._post("NMC", "reboot", {"reason": "home_assistant"})
        return result is not None

    async def scan_network(self) -> bool:
        """Forcer un scan du réseau."""
        result = await self._post("Devices", "find", {})
        return result is not None

    # ------------------------------------------------------------------
    # Test de connexion
    # ------------------------------------------------------------------

    async def test_connection(self) -> bool:
        """Tester la connexion et l'authentification."""
        try:
            await self.authenticate()
            info = await self.get_device_info()
            return bool(info)
        except (LiveboxAuthError, LiveboxConnectionError):
            return False
