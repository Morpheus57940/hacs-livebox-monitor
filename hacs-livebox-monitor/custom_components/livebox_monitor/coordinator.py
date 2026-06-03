"""DataUpdateCoordinator pour Livebox Monitor."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LiveboxAPI, LiveboxConnectionError

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)


class LiveboxCoordinator(DataUpdateCoordinator):
    """Coordinateur central qui récupère et distribue les données Livebox."""

    def __init__(self, hass: HomeAssistant, api: LiveboxAPI, scan_interval: int = 30) -> None:
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name="Livebox Monitor",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupérer toutes les données depuis la Livebox."""
        try:
            (
                devices,
                wan_status,
                device_info,
                wifi_stats,
            ) = await self._fetch_all()

            processed_devices = self._process_devices(devices)

            return {
                "devices": processed_devices,
                "wan_status": wan_status,
                "device_info": device_info,
                "wifi_stats": wifi_stats,
                "online_count": sum(1 for d in processed_devices if d.get("active")),
                "unknown_count": sum(1 for d in processed_devices if d.get("unknown")),
                "blocked_count": sum(1 for d in processed_devices if d.get("blocked")),
            }
        except LiveboxConnectionError as exc:
            raise UpdateFailed(f"Erreur de connexion Livebox : {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise UpdateFailed(f"Erreur inattendue : {exc}") from exc

    async def _fetch_all(self) -> tuple:
        """Récupérer toutes les sources de données en parallèle."""
        import asyncio
        results = await asyncio.gather(
            self.api.get_devices(),
            self.api.get_wan_status(),
            self.api.get_device_info(),
            self.api.get_wifi_stats(),
            return_exceptions=True,
        )
        # Remplacer les exceptions par des valeurs par défaut
        devices = results[0] if not isinstance(results[0], Exception) else []
        wan_status = results[1] if not isinstance(results[1], Exception) else {}
        device_info = results[2] if not isinstance(results[2], Exception) else {}
        wifi_stats = results[3] if not isinstance(results[3], Exception) else {}
        return devices, wan_status, device_info, wifi_stats

    @staticmethod
    def _process_devices(raw_devices: list[dict]) -> list[dict]:
        """Normaliser et enrichir les données des appareils."""
        processed = []
        for dev in raw_devices:
            if not isinstance(dev, dict):
                continue

            names = dev.get("Names", [])
            user_name = None
            dhcp_name = None
            for n in names if isinstance(names, list) else []:
                src = n.get("Source", "")
                val = n.get("Name", "")
                if src in ("webui", "user") and val:
                    user_name = val
                elif src == "dhcp" and val:
                    dhcp_name = val

            display_name = user_name or dhcp_name or dev.get("Name", "")
            mac = dev.get("PhysAddress", "")
            is_unknown = not display_name or display_name.lower() in ("", "unknown")

            addresses = dev.get("IPv4Address", [])
            ip = ""
            if isinstance(addresses, list) and addresses:
                ip = addresses[0].get("IPAddress", "") if isinstance(addresses[0], dict) else ""
            elif isinstance(addresses, dict):
                ip = addresses.get("IPAddress", "")

            processed.append({
                "mac": mac,
                "name": display_name or mac,
                "user_name": user_name,
                "dhcp_name": dhcp_name,
                "ip": ip,
                "active": dev.get("Active", False),
                "blocked": dev.get("Blocked", False),
                "unknown": is_unknown,
                "interface": dev.get("InterfaceName", ""),
                "link_type": dev.get("Layer2Interface", ""),
                "first_seen": dev.get("FirstSeen", ""),
                "last_seen": dev.get("LastSeen", ""),
                "device_type": dev.get("DeviceType", ""),
                "vendor": dev.get("Vendor", ""),
                "rssi": dev.get("RSSI"),
                "raw": dev,
            })
        return processed

    def get_device_by_mac(self, mac: str) -> dict | None:
        """Retrouver un appareil dans le cache par son MAC."""
        if not self.data:
            return None
        mac_upper = mac.upper()
        for dev in self.data.get("devices", []):
            if dev.get("mac", "").upper() == mac_upper:
                return dev
        return None
