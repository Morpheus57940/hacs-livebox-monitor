"""Client API pour la Livebox Orange — compatible LB4/5/6/7 (sysbus JSON)."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

# La Livebox 7 répond sur livebox.home/ws ou 192.168.1.1/ws (même port 80)
# L'URL d'auth a changé : /authenticate → /api/v1/login sur certains firmwares LB7
# On tente les deux automatiquement via auto-detect

LIVEBOX_PORT = 80

# Endpoints selon génération
AUTH_ENDPOINTS = [
    "/authenticate",          # LB4 / LB5 / LB6
    "/api/v1/login",          # LB7 firmware récent
    "/sysbus/authenticate",   # variante sysbus
]
WS_ENDPOINTS = [
    "/ws",                    # LB4/5/6 et LB7
    "/sysbus",                # variante
]

SYSBUS_HEADERS = {
    "Content-Type": "application/x-sysbus-json",
    "X-Context": "JSON",
}


class LiveboxAuthError(Exception):
    """Erreur d'authentification Livebox."""


class LiveboxConnectionError(Exception):
    """Erreur de connexion Livebox."""


class LiveboxAPI:
    """Client asynchrone pour l'API Livebox — LB4 à LB7."""

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
        self._auth_url: str | None = None   # détecté automatiquement
        self._ws_url: str | None = None     # détecté automatiquement

    def _base(self) -> str:
        return f"http://{self._host}:{self._port}"

    # ------------------------------------------------------------------
    # Auto-détection de génération (LB4/5/6 vs LB7)
    # ------------------------------------------------------------------

    async def _detect_endpoints(self) -> None:
        """Détecter automatiquement les bons endpoints selon le firmware."""
        base = self._base()

        # Détection endpoint WS
        for ep in WS_ENDPOINTS:
            try:
                async with self._session.get(
                    f"{base}{ep}",
                    timeout=aiohttp.ClientTimeout(total=5),
                    allow_redirects=False,
                ) as r:
                    # 200, 401, 403 = endpoint existe
                    if r.status in (200, 401, 403, 405):
                        self._ws_url = f"{base}{ep}"
                        _LOGGER.debug("WS endpoint détecté : %s", self._ws_url)
                        break
            except Exception:
                continue

        if not self._ws_url:
            self._ws_url = f"{base}/ws"  # fallback

        # Détection endpoint auth
        for ep in AUTH_ENDPOINTS:
            try:
                async with self._session.post(
                    f"{base}{ep}",
                    json={"service": "test", "method": "test", "parameters": {}},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as r:
                    if r.status in (200, 401, 403):
                        self._auth_url = f"{base}{ep}"
                        _LOGGER.debug("Auth endpoint détecté : %s", self._auth_url)
                        break
            except Exception:
                continue

        if not self._auth_url:
            self._auth_url = f"{base}/authenticate"  # fallback LB4-6

    # ------------------------------------------------------------------
    # Authentification
    # ------------------------------------------------------------------

    async def authenticate(self) -> bool:
        """S'authentifier et récupérer le token de contexte."""
        if not self._auth_url:
            await self._detect_endpoints()

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
                self._auth_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 404:
                    # Fallback : essayer l'autre endpoint
                    _LOGGER.warning("Auth 404 sur %s, tentative fallback…", self._auth_url)
                    self._auth_url = None
                    await self._detect_endpoints()
                    return await self.authenticate()
                if resp.status != 200:
                    raise LiveboxAuthError(f"HTTP {resp.status} sur {self._auth_url}")
                data = await resp.json(content_type=None)
                status = data.get("status", 0)
                if status != 0:
                    raise LiveboxAuthError(f"Auth échouée, status={status}")
                ctx = data.get("data", {})
                self._auth_token = ctx.get("contextID")
                _LOGGER.debug("Auth OK — token=%s endpoint=%s", self._auth_token, self._auth_url)
                return True
        except aiohttp.ClientError as exc:
            raise LiveboxConnectionError(str(exc)) from exc

    async def _post(self, service: str, method: str, parameters: dict | None = None) -> Any:
        """Appel API JSON vers la Livebox."""
        if not self._auth_token:
            await self.authenticate()

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
                self._ws_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    _LOGGER.debug("Token expiré, ré-auth…")
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
        """Liste de tous les appareils connus."""
        result = await self._post(
            "Devices",
            "get",
            {"expression": {
                "ETHERNET": "not interface and not self",
                "WIFI": "not interface and not self",
            }},
        )
        if not result:
            return []
        devices = []
        for item in (result if isinstance(result, list) else [result]):
            if isinstance(item, list):
                devices.extend(item)
            elif isinstance(item, dict):
                devices.append(item)
        return devices

    async def get_active_devices(self) -> list[dict]:
        """Appareils actuellement connectés."""
        return [d for d in await self.get_devices() if d.get("Active", False)]

    async def get_device_by_mac(self, mac: str) -> dict | None:
        for d in await self.get_devices():
            if d.get("PhysAddress", "").upper() == mac.upper():
                return d
        return None

    # ------------------------------------------------------------------
    # Statistiques réseau
    # ------------------------------------------------------------------

    async def get_wan_status(self) -> dict:
        return await self._post("NMC", "getWANStatus", {}) or {}

    async def get_interfaces_stats(self) -> dict:
        return await self._post(
            "NeMo.Intf.lo", "getMIBs",
            {"mibs": "base", "flag": "stat", "traverse": "all"},
        ) or {}

    async def get_wifi_stats(self) -> dict:
        return await self._post("NMC.Wifi", "get", {}) or {}

    async def get_dhcp_leases(self) -> list[dict]:
        result = await self._post("DHCPv4.Server.Pool.default", "getStaticLeases", {})
        return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # Informations système
    # ------------------------------------------------------------------

    async def get_device_info(self) -> dict:
        return await self._post("DeviceInfo", "get", {}) or {}

    async def get_uptime(self) -> int:
        return (await self.get_device_info()).get("UpTime", 0)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def block_device(self, mac: str) -> bool:
        result = await self._post(
            f"Devices.Device.{mac.upper()}", "setParameters",
            {"parameters": {"Blocked": True}},
        )
        return result is not None

    async def unblock_device(self, mac: str) -> bool:
        result = await self._post(
            f"Devices.Device.{mac.upper()}", "setParameters",
            {"parameters": {"Blocked": False}},
        )
        return result is not None

    async def assign_device_name(self, mac: str, name: str) -> bool:
        result = await self._post(
            f"Devices.Device.{mac.upper()}", "setName",
            {"source": "webui", "name": name},
        )
        return result is not None

    async def reboot(self) -> bool:
        return await self._post("NMC", "reboot", {"reason": "home_assistant"}) is not None

    async def scan_network(self) -> bool:
        return await self._post("Devices", "find", {}) is not None

    # ------------------------------------------------------------------
    # Test de connexion (utilisé par config_flow)
    # ------------------------------------------------------------------

    async def test_connection(self) -> bool:
        """Tester la connexion — détecte automatiquement le bon endpoint."""
        try:
            await self._detect_endpoints()
            await self.authenticate()
            info = await self.get_device_info()
            lb_model = info.get("ProductClass", "Unknown")
            _LOGGER.info("Livebox détectée : %s (endpoint: %s)", lb_model, self._auth_url)
            return bool(info)
        except (LiveboxAuthError, LiveboxConnectionError) as exc:
            _LOGGER.error("test_connection échoué : %s", exc)
            return False
