import sys
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from custom_components.trackit.const import (  # noqa: E402
    DOMAIN,
    CONF_IMAP_HOST,
    CONF_IMAP_PORT,
    CONF_SECURITY,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_MAILBOX,
    CONF_SCAN_WINDOW_DAYS,
    CONF_UNSEEN_ONLY,
    CONF_SCAN_INTERVAL,
    CONF_SENSOR_STATE_MODE,
    CONF_MAX_MATCHES,
    CONF_VENDORS,
    CONF_NAME,
)


def create_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_IMAP_HOST: "host",
            CONF_IMAP_PORT: 993,
            CONF_SECURITY: "SSL/TLS",
            CONF_USERNAME: "user",
            CONF_PASSWORD: "pass",
            CONF_MAILBOX: "INBOX",
            CONF_SCAN_WINDOW_DAYS: 14,
            CONF_UNSEEN_ONLY: True,
        },
        options={
            CONF_SCAN_INTERVAL: 10,
            CONF_SENSOR_STATE_MODE: "count",
            CONF_MAX_MATCHES: 20,
            CONF_VENDORS: [],
            CONF_NAME: "TrackIT",
        },
        entry_id="test",
        title="TrackIT",
    )


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return create_entry()
