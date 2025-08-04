"""
Mail‑Tracker Sensor
• Ausführliche DEBUG‑Logs
• Absender‑Filter, max_age_days
• state_mode: "count" | "last_code"
• Thread‑Safety: Keine HA‑Aufrufe mehr im Executor‑Thread
"""

from __future__ import annotations

import email
import logging
import re
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from pathlib import Path
from typing import Any, Dict, List

import voluptuous as vol
import yaml
from bs4 import BeautifulSoup
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STARTED,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.dt import utcnow
from imapclient import IMAPClient

from .const import (
    CONF_FORWARD_DATA,
    CONF_FORWARD_SERVICE,
    CONF_PATTERN_FILE,
    DEFAULT_FOLDER,
    LAST_UID_FILE,
)

_LOGGER = logging.getLogger(__name__)
DEFAULT_SCAN = timedelta(minutes=5)

# Separate Debug‑Datei
_dbg = Path("/config/mail_tracker_debug.log")
if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(_dbg) for h in _LOGGER.handlers):
    fh = logging.FileHandler(_dbg, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _LOGGER.addHandler(fh)

# ───────────────── Plattform‑Schema ─────────────────
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.port,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_NAME,    default="Mail Tracker"): cv.string,
        vol.Optional("folder",     default=DEFAULT_FOLDER): cv.string,
        vol.Required(CONF_PATTERN_FILE): cv.string,
        vol.Optional("scan_interval", default=DEFAULT_SCAN): cv.time_period,
        vol.Optional("max_age_days"): cv.positive_int,
        vol.Optional("state_mode",  default="count"): vol.In(["count", "last_code"]),
        vol.Optional(CONF_FORWARD_SERVICE): cv.string,
        vol.Optional(CONF_FORWARD_DATA, default={}): dict,
    }
)

# ───────── Hilfsfunktionen ─────────
def _decode_header(val: str) -> str:
    out: list[str] = []
    for txt, enc in decode_header(val):
        if isinstance(txt, bytes):
            enc = (enc or "utf-8").lower()
            if enc in ("unknown-8bit", "x-unknown", "ansi_x3.4-1968", "ascii"):
                enc = "utf-8"
            try:
                out.append(txt.decode(enc))
            except Exception:
                out.append(txt.decode("utf-8", errors="replace"))
        else:
            out.append(txt)
    return "".join(out)


def _split_body(msg: email.message.Message) -> tuple[str, str]:
    plain, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if "attachment" in str(part.get("Content-Disposition")):
                continue
            if ctype == "text/plain":
                plain = part.get_payload(decode=True).decode(errors="ignore")
            elif ctype == "text/html":
                html = part.get_payload(decode=True).decode(errors="ignore")
    else:
        payload = msg.get_payload(decode=True).decode(errors="ignore")
        plain = payload if msg.get_content_type() == "text/plain" else ""
        html  = payload if msg.get_content_type() != "text/plain" else ""
    return plain, html


# ───────── Sensor‑Klasse ─────────
class MailTrackerSensor(SensorEntity):
    _attr_icon = "mdi:package-variant-closed"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, cfg: ConfigType) -> None:
        self.hass = hass
        self._name        = cfg[CONF_NAME]
        self._host        = cfg[CONF_HOST]
        self._port        = cfg[CONF_PORT]
        self._user        = cfg[CONF_USERNAME]
        self._pwd         = cfg[CONF_PASSWORD]
        self._folder      = cfg["folder"]
        self._pattern_p   = Path(hass.config.path(cfg[CONF_PATTERN_FILE]))
        self._last_uid_p  = Path(hass.config.path(LAST_UID_FILE))
        self._fwd_svc     = cfg.get(CONF_FORWARD_SERVICE)
        self._fwd_data    = cfg.get(CONF_FORWARD_DATA, {})
        self._max_age     = cfg.get("max_age_days")
        self._state_mode  = cfg.get("state_mode", "count")

        self._compiled: list[dict[str, Any]] = []
        self._last_uid: int | None = None
        self._state: int | str = "" if self._state_mode == "last_code" else 0
        self._attr_extra_state_attributes: Dict[str, Any] = {}

        interval = cfg.get("scan_interval", DEFAULT_SCAN)
        if isinstance(interval, (int, float)):
            interval = timedelta(seconds=int(interval))

        async_track_time_interval(hass, self._async_interval, interval)
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, self._async_startup)

    # ───── Event‑Wrapper ─────
    async def _async_startup(self, _): await self._update()
    async def _async_interval(self, _): await self._update()

    # ───── Main Update ─────
    async def _update(self):
        matches = await self.hass.async_add_executor_job(self._fetch_matches)

        # Fire events & forward service **in Event‑Loop**
        for itm in matches:
            self.hass.bus.async_fire("mail_tracker_found", itm)
            if self._fwd_svc:
                dom, svc = self._fwd_svc.split(".")
                data = {**self._fwd_data,
                        "package_tracking_number": itm["code"],
                        "package_friendly_name":  itm["courier"]}
                _LOGGER.debug("Forward %s → %s", itm["code"], self._fwd_svc)
                try:
                    await self.hass.services.async_call(dom, svc, data, blocking=False)
                except Exception as err:  # noqa: BLE001
                    _LOGGER.error("Forward‑Call %s fehlgeschlagen: %s", self._fwd_svc, err)

        # State setzen
        if self._state_mode == "last_code":
            if matches:
                self._state = matches[-1]["code"]
        else:
            self._state = len(matches)

        self._attr_extra_state_attributes = {
            "last_update": utcnow().isoformat(),
            "matches": matches,
        }
        self.async_write_ha_state()

    # ───── Blocking‑Fetcher ─────
    def _fetch_matches(self) -> list[dict[str, str]]:
        self._load_last_uid()
        self._load_patterns()

        matches: list[dict[str, str]] = []
        try:
            with IMAPClient(self._host, port=self._port, ssl=True) as srv:
                srv.login(self._user, self._pwd)
                _LOGGER.debug("IMAP‑Login OK für %s", self._user)
                srv.select_folder(self._folder, readonly=True)

                criteria: list[str] = []
                if self._max_age:
                    since = (datetime.now(timezone.utc) - timedelta(days=self._max_age)).strftime("%d-%b-%Y")
                    criteria.append(f"SINCE {since}")
                if self._last_uid is not None:
                    criteria.append(f"UID {self._last_uid + 1}:*")
                search = f"({' '.join(criteria)})" if criteria else "ALL"

                uids = srv.search(search)
                _LOGGER.debug("Suche %s → %d Messages", search, len(uids))

                for uid in uids:
                    raw = srv.fetch([uid], ["RFC822"])[uid][b"RFC822"]
                    msg = email.message_from_bytes(raw)
                    subj = _decode_header(msg.get("Subject", ""))
                    frm  = _decode_header(msg.get("From", ""))
                    plain, html = _split_body(msg)
                    preview = (plain or html)[:200].replace("\n", " ")
                    _LOGGER.debug("UID %s | From:%s | Sub:%s | Prev:%s", uid, frm, subj, preview)

                    ptxt = f"{subj}\n{plain}"
                    htxt = f"{subj}\n{BeautifulSoup(html, 'html.parser').get_text()}" if html else ptxt

                    for grp in self._compiled:
                        if grp.get("from_filter") and not any(s.lower() in frm.lower() for s in grp["from_filter"]):
                            continue
                        src = htxt if grp["html"] else ptxt
                        for rx in grp["regex"]:
                            hit = rx.search(src)
                            if hit:
                                code = hit.group(1).strip()
                                _LOGGER.debug("Treffer %s → %s", grp["name"], code)
                                matches.append({
                                    "courier": grp["name"],
                                    "code":    code,
                                    "url":     grp["url"].format(tracking=code) if grp.get("url") else None,
                                })
                                break
                    self._last_uid = uid

                self._save_last_uid()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("IMAP‑Fehler: %s", err, exc_info=True)

        return matches

    # ───── File‑Helper ─────
    def _load_last_uid(self):
        try:    self._last_uid = int(self._last_uid_p.read_text())
        except (FileNotFoundError, ValueError): self._last_uid = None

    def _save_last_uid(self):
        self._last_uid_p.write_text(str(self._last_uid or ""))

    def _load_patterns(self):
        if not self._pattern_p.exists():
            _LOGGER.error("Pattern‑Datei %s fehlt", self._pattern_p)
            self._compiled = []
            return
        data = yaml.safe_load(self._pattern_p.read_text()) or []
        self._compiled = []
        for e in data:
            entry = {
                "name": e["name"],
                "html": bool(e.get("html")),
                "url":  e.get("url"),
                "regex": [re.compile(r) for r in (e["regex"] if isinstance(e["regex"], list) else [e["regex"]])],
            }
            if "from_filter" in e:
                entry["from_filter"] = e["from_filter"] if isinstance(e["from_filter"], list) else [e["from_filter"]]
            self._compiled.append(entry)
        _LOGGER.debug("%d Pattern‑Gruppen geladen", len(self._compiled))

    # ───── Entity‑Props ─────
    @property
    def name(self) -> str:  # type: ignore[override]
        return self._name

    @property
    def native_value(self) -> int | str:  # type: ignore[override]
        return self._state


# ───────────────── Setup ─────────────────
async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities,
    discovery_info=None,
):
    async_add_entities([MailTrackerSensor(hass, config)])
