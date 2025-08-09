"""Config flow for TrackIt."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_IMAP,
    CONF_PATTERN_FILE,
    CONF_SCAN_INTERVAL,
    DEFAULT_FOLDER,
    DEFAULT_PATTERN_FILE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


class TrackItConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TrackIt."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_HOST): cv.string,
                    vol.Required(CONF_PORT, default=993): cv.port,
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                    vol.Optional("folder", default=DEFAULT_FOLDER): cv.string,
                    vol.Optional(CONF_PATTERN_FILE, default=DEFAULT_PATTERN_FILE): cv.string,
                    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
                }
            )
            return self.async_show_form(step_id="user", data_schema=data_schema)

        imap = {
            CONF_HOST: user_input[CONF_HOST],
            CONF_PORT: user_input[CONF_PORT],
            CONF_USERNAME: user_input[CONF_USERNAME],
            CONF_PASSWORD: user_input[CONF_PASSWORD],
            "folder": user_input.get("folder", DEFAULT_FOLDER),
        }
        data = {
            CONF_IMAP: imap,
            CONF_PATTERN_FILE: user_input.get(CONF_PATTERN_FILE, DEFAULT_PATTERN_FILE),
            CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        }
        return self.async_create_entry(title=user_input[CONF_USERNAME], data=data)

