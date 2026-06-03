"""Constantes pour Livebox Monitor."""

DOMAIN = "livebox_monitor"

DEFAULT_HOST = "192.168.1.1"
DEFAULT_PORT = 80
DEFAULT_USERNAME = "admin"
DEFAULT_SCAN_INTERVAL = 30  # secondes

PLATFORMS = ["sensor", "binary_sensor", "device_tracker", "switch"]

# Clés de données coordinator
DATA_COORDINATOR = "coordinator"
DATA_API = "api"

# Attributs appareils
ATTR_MAC = "mac"
ATTR_IP = "ip"
ATTR_VENDOR = "vendor"
ATTR_LINK_TYPE = "link_type"
ATTR_FIRST_SEEN = "first_seen"
ATTR_LAST_SEEN = "last_seen"
ATTR_RSSI = "rssi"
ATTR_BLOCKED = "blocked"
ATTR_UNKNOWN = "unknown"

# Services
SERVICE_BLOCK_DEVICE = "block_device"
SERVICE_UNBLOCK_DEVICE = "unblock_device"
SERVICE_ASSIGN_NAME = "assign_name"
SERVICE_REBOOT = "reboot"
SERVICE_SCAN = "scan_network"

# Icônes
ICON_ROUTER = "mdi:router-network"
ICON_DEVICE = "mdi:devices"
ICON_WIFI = "mdi:wifi"
ICON_ETHERNET = "mdi:ethernet"
ICON_BLOCKED = "mdi:block-helper"
ICON_UNKNOWN = "mdi:help-network"
ICON_DOWNLOAD = "mdi:download-network"
ICON_UPLOAD = "mdi:upload-network"
