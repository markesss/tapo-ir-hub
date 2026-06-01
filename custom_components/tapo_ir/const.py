"""Constants for the Tapo IR Hub integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "tapo_ir"

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]

# Config entry data keys
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Options keys
CONF_SCAN_INTERVAL = "scan_interval"
CONF_NAME_OVERRIDES = "name_overrides"

# Default re-query interval (seconds) for the background async task.
DEFAULT_SCAN_INTERVAL = 300
MIN_SCAN_INTERVAL = 30

# Manufacturer/model strings shown in the device registry.
MANUFACTURER = "TP-Link"
HUB_MODEL = "Tapo IR Hub (H1xx)"
REMOTE_MODEL = "IR Remote profile"
