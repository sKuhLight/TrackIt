"""Constants for the TrackIt integration."""
from __future__ import annotations

DOMAIN = "trackit"

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

CONF_IMAP = "imap"
CONF_CARRIERS = "carriers"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_PATTERN_FILE = "pattern_file"
CONF_FORWARD_SERVICE = "forward_service"  # e.g. "seventeentrack.add_package"
CONF_FORWARD_DATA = "forward_data"  # optional static fields

DEFAULT_FOLDER = "INBOX"
DEFAULT_PATTERN_FILE = "trackit_patterns.yaml"
DEFAULT_SCAN_INTERVAL = 300  # seconds
