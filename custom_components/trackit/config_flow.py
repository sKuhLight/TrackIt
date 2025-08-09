"""Config flow for TrackIT."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .const import (
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
    DEFAULT_IMAP_PORT,
    DEFAULT_MAILBOX,
    DEFAULT_SCAN_WINDOW_DAYS,
    DEFAULT_UNSEEN_ONLY,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DEFAULT_SENSOR_STATE_MODE,
    DEFAULT_MAX_MATCHES,
)
from .imap_client import IMAPClient
from .models import VendorConfig

SECURITY_OPTIONS = ["SSL/TLS", "STARTTLS", "None"]

DHL_TEMPLATE = {
    "name": "DHL",
    "html": True,
    "from_filter": [
        "noreply@dhl.de",
        "@dhl.com",
        "@dhl.de",
        "@gmail.com",
    ],
    "regex": [
        r"\b(\d{20,22})\b",
        r"\b(JJD\w{13,17})\b",
        r"\b([A-Z]{2}\d{9}DE)\b",
    ],
    "css_selectors": ["body", "div, p, span"],
}


async def _test_connection(hass: HomeAssistant, data: dict) -> bool:
    client = IMAPClient(hass, data)
    try:
        await client.async_connect()
        await client.async_logout()
    except Exception:  # pragma: no cover - network errors
        return False
    return True


class TrackItConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TrackIT."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            ok = await _test_connection(self.hass, user_input)
            if ok:
                return self.async_create_entry(
                    title="TrackIT", data=user_input, options=self._default_options()
                )
            errors["base"] = "cannot_connect"
        data_schema = vol.Schema(
            {
                vol.Required(CONF_IMAP_HOST): selector.TextSelector(),
                vol.Required(
                    CONF_IMAP_PORT, default=DEFAULT_IMAP_PORT
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=65535)
                ),
                vol.Required(CONF_SECURITY, default="SSL/TLS"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=SECURITY_OPTIONS)
                ),
                vol.Required(CONF_USERNAME): selector.TextSelector(),
                vol.Required(CONF_PASSWORD): selector.TextSelector(
                    selector.TextSelectorConfig(type="password")
                ),
                vol.Required(
                    CONF_MAILBOX, default=DEFAULT_MAILBOX
                ): selector.TextSelector(),
                vol.Required(
                    CONF_SCAN_WINDOW_DAYS, default=DEFAULT_SCAN_WINDOW_DAYS
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=365)
                ),
                vol.Required(
                    CONF_UNSEEN_ONLY, default=DEFAULT_UNSEEN_ONLY
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    def _default_options(self) -> dict:
        return {
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL_MINUTES,
            CONF_SENSOR_STATE_MODE: DEFAULT_SENSOR_STATE_MODE,
            CONF_MAX_MATCHES: DEFAULT_MAX_MATCHES,
            CONF_VENDORS: [],
            CONF_NAME: "TrackIT",
        }

    async def async_step_import(self, data):  # pragma: no cover - no import
        return await self.async_step_user(data)

    async def async_get_options_flow(self, entry):
        return TrackItOptionsFlow(entry)


def _split_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


class TrackItOptionsFlow(config_entries.OptionsFlow):
    """Handle options for TrackIT."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry
        self.vendors = [VendorConfig(**v) for v in entry.options.get(CONF_VENDORS, [])]
        self.options = dict(entry.options)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            action = user_input["action"]
            if action == "settings":
                return await self.async_step_settings()
            if action == "add_vendor":
                return await self.async_step_vendor()
            if action.startswith("edit_"):
                index = int(action.split("_")[1])
                return await self.async_step_vendor(index=index)
            if action == "add_dhl":
                self.vendors.append(VendorConfig(**DHL_TEMPLATE))
                return await self.async_step_init()
        choices = [
            {"value": "settings", "label": "Settings"},
            {"value": "add_vendor", "label": "Add vendor"},
            {"value": "add_dhl", "label": "Add DHL example"},
        ]
        for idx, vendor in enumerate(self.vendors):
            choices.append({"value": f"edit_{idx}", "label": f"Edit {vendor.name}"})
        schema = vol.Schema(
            {
                vol.Required("action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=choices)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_settings(self, user_input=None):
        if user_input is not None:
            self.options.update(user_input)
            self.options[CONF_VENDORS] = [vars(v) for v in self.vendors]
            return self.async_create_entry(title="", data=self.options)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=1440)
                ),
                vol.Required(
                    CONF_SENSOR_STATE_MODE,
                    default=self.options.get(
                        CONF_SENSOR_STATE_MODE, DEFAULT_SENSOR_STATE_MODE
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=["count", "most_recent"])
                ),
                vol.Required(
                    CONF_MAX_MATCHES,
                    default=self.options.get(CONF_MAX_MATCHES, DEFAULT_MAX_MATCHES),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=1000)
                ),
                vol.Required(
                    CONF_NAME,
                    default=self.options.get(CONF_NAME, "TrackIT"),
                ): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="settings", data_schema=schema)

    async def async_step_vendor(self, user_input=None, index: int | None = None):
        existing = None
        if index is not None:
            existing = self.vendors[index]
        if user_input is not None:
            vendor = VendorConfig(
                name=user_input[CONF_NAME],
                html=user_input.get("html", False),
                from_filter=_split_lines(user_input.get("from_filter", "")),
                regex=_split_lines(user_input.get("regex", "")),
                css_selectors=_split_lines(user_input.get("css_selectors", "")),
            )
            if index is None:
                self.vendors.append(vendor)
            else:
                self.vendors[index] = vendor
            return await self.async_step_init()
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME, default=getattr(existing, "name", "")
                ): selector.TextSelector(),
                vol.Required(
                    "html", default=getattr(existing, "html", False)
                ): selector.BooleanSelector(),
                vol.Optional(
                    "from_filter",
                    default="\n".join(getattr(existing, "from_filter", [])),
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
                vol.Optional(
                    "regex",
                    default="\n".join(getattr(existing, "regex", [])),
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
                vol.Optional(
                    "css_selectors",
                    default="\n".join(getattr(existing, "css_selectors", [])),
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
            }
        )
        return self.async_show_form(step_id="vendor", data_schema=schema)
