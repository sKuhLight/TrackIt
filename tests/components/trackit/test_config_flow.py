import pytest

from custom_components.trackit import config_flow
from custom_components.trackit.const import (
    CONF_IMAP_HOST,
    CONF_IMAP_PORT,
    CONF_SECURITY,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_MAILBOX,
    CONF_SCAN_WINDOW_DAYS,
    CONF_UNSEEN_ONLY,
)


@pytest.mark.asyncio
async def test_config_flow_user(monkeypatch):
    async def _mock_test(hass, data):
        return True

    monkeypatch.setattr(config_flow, "_test_connection", _mock_test)
    flow = config_flow.TrackItConfigFlow()
    flow.hass = None
    user_input = {
        CONF_IMAP_HOST: "imap.example.com",
        CONF_IMAP_PORT: 993,
        CONF_SECURITY: "SSL/TLS",
        CONF_USERNAME: "user",
        CONF_PASSWORD: "pass",
        CONF_MAILBOX: "INBOX",
        CONF_SCAN_WINDOW_DAYS: 14,
        CONF_UNSEEN_ONLY: True,
    }
    result = await flow.async_step_user(user_input)
    assert result["type"] == "create_entry"
    assert result["title"] == "TrackIT"
