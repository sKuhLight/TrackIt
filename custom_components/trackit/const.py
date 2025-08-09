"""Constants for TrackIT integration."""

from __future__ import annotations

DOMAIN = "trackit"
LOGGER_NAME = "homeassistant.components.trackit"

# Defaults
DEFAULT_IMAP_PORT = 993
DEFAULT_MAILBOX = "INBOX"
DEFAULT_SCAN_WINDOW_DAYS = 14
DEFAULT_UNSEEN_ONLY = True
DEFAULT_SCAN_INTERVAL_MINUTES = 10
DEFAULT_MAX_MATCHES = 20
DEFAULT_SENSOR_STATE_MODE = "count"

# Config keys
CONF_IMAP_HOST = "imap_host"
CONF_IMAP_PORT = "imap_port"
CONF_SECURITY = "security"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_MAILBOX = "mailbox"
CONF_SCAN_WINDOW_DAYS = "scan_window_days"
CONF_UNSEEN_ONLY = "unseen_only"

CONF_SCAN_INTERVAL = "scan_interval_minutes"
CONF_SENSOR_STATE_MODE = "sensor_state_mode"
CONF_MAX_MATCHES = "max_matches"
CONF_VENDORS = "vendors"
CONF_NAME = "name"

SENSOR_STATE_COUNT = "count"
SENSOR_STATE_MOST_RECENT = "most_recent"

STORAGE_VERSION = 1

SERVICE_RESCAN = "rescan"

ATTR_MATCHES = "matches"
ATTR_LAST_SCAN = "last_scan"
