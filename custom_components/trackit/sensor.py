"""Async email tracker sensors for Home Assistant."""
from __future__ import annotations

import email
import logging
import re
from dataclasses import dataclass
from datetime import timedelta
from email.header import decode_header
from pathlib import Path
from typing import Any, Dict, List

import aioimaplib
import yaml
from bs4 import BeautifulSoup
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.dt import utcnow

from .const import (
    CONF_FORWARD_DATA,
    CONF_FORWARD_SERVICE,
    CONF_IMAP,
    CONF_PATTERN_FILE,
    CONF_SCAN_INTERVAL,
    DEFAULT_FOLDER,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

# --- Data classes ---------------------------------------------------------

@dataclass
class CarrierPattern:
    name: str
    regex: List[re.Pattern]
    from_filter: List[str]
    html: bool
    url: str | None


# --- Helper functions -----------------------------------------------------

def _decode_header(val: str) -> str:
    out: list[str] = []
    for txt, enc in decode_header(val):
        if isinstance(txt, bytes):
            enc = (enc or "utf-8").lower()
            try:
                out.append(txt.decode(enc))
            except Exception:  # noqa: BLE001
                out.append(txt.decode("utf-8", errors="replace"))
        else:
            out.append(txt)
    return "".join(out)


def _split_body(msg: email.message.Message) -> tuple[str, str]:
    plain, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not plain:
                plain = part.get_payload(decode=True).decode(errors="ignore")
            elif part.get_content_type() == "text/html" and not html:
                html = part.get_payload(decode=True).decode(errors="ignore")
    else:
        payload = msg.get_payload(decode=True).decode(errors="ignore")
        if msg.get_content_type() == "text/plain":
            plain = payload
        else:
            html = payload
    return plain, html


async def fetch_unseen_uids(client: aioimaplib.IMAP4_SSL, last_uid: int) -> List[int]:
    """Return list of unseen UIDs since last_uid."""
    search = ("UID", f"{last_uid + 1}:*") if last_uid else ("ALL",)
    try:
        resp = await client.uid_search(*search)
        return [int(x) for x in resp.lines[0].split()] if resp.lines else []
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("UID search failed: %s", err)
        return []


def filter_by_sender(sender: str, allowed: List[str]) -> bool:
    """Return True if sender matches allowed list."""
    if not allowed:
        return True
    sl = sender.lower()
    return any(a.lower() in sl for a in allowed)


def extract_tracking_numbers(text: str, patterns: List[re.Pattern]) -> List[str]:
    """Extract tracking numbers using patterns."""
    codes: List[str] = []
    for rx in patterns:
        hit = rx.search(text)
        if hit:
            codes.append(hit.group(1).strip())
    return codes


def _load_pattern_file(path: str) -> List[dict[str, Any]]:
    """Helper to load pattern YAML from disk."""
    try:
        return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Pattern file load failed: %s", err)
        return []


async def update_store(store: Store, last_uid: int, numbers: set[str]) -> None:
    """Persist last UID and numbers to Store."""
    try:
        await store.async_save({"last_uid": last_uid, "numbers": list(numbers)})
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Store save failed: %s", err)


async def update_entities(manager: "TrackItManager", new_numbers: Dict[str, List[str]]) -> None:
    """Update sensors with new numbers."""
    for name, codes in new_numbers.items():
        entity = manager.entities.get(name)
        if not entity:
            continue
        for code in codes:
            entity.add_code(code)


# --- Manager --------------------------------------------------------------

class TrackItManager:
    """Central coordinator handling IMAP connection and parsing."""

    def __init__(self, hass: HomeAssistant, cfg: ConfigType) -> None:
        self.hass = hass
        self.cfg = cfg
        self.store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.last_uid: int = 0
        self.seen_numbers: set[str] = set()
        self.patterns: List[CarrierPattern] = []
        self.entities: Dict[str, TrackItSensor] = {}
        self.forward_service: str | None = cfg.get(CONF_FORWARD_SERVICE)
        self.forward_data: Dict[str, Any] = cfg.get(CONF_FORWARD_DATA, {})
        self._unsub = None

    async def async_setup(self) -> None:
        await self._async_load_store()
        await self._async_load_patterns()
        interval = timedelta(seconds=self.cfg.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        self._unsub = async_track_time_interval(self.hass, self.async_scan, interval)

    async def _async_load_patterns(self) -> None:
        path = self.hass.config.path(self.cfg[CONF_PATTERN_FILE])
        data = await self.hass.async_add_executor_job(_load_pattern_file, path)
        for e in data:
            regex = [re.compile(r) for r in (e["regex"] if isinstance(e["regex"], list) else [e["regex"]])]
            frm = e.get("from_filter")
            from_filter = frm if isinstance(frm, list) else [frm] if frm else []
            self.patterns.append(
                CarrierPattern(
                    name=e["name"],
                    regex=regex,
                    from_filter=from_filter,
                    html=bool(e.get("html")),
                    url=e.get("url"),
                )
            )
        _LOGGER.debug("Loaded %d carrier patterns", len(self.patterns))

    async def _async_load_store(self) -> None:
        try:
            data = await self.store.async_load()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Store load failed: %s", err)
            data = None
        if data:
            self.last_uid = data.get("last_uid", 0)
            self.seen_numbers = set(data.get("numbers", []))

    async def async_scan(self, _now=None) -> None:
        imap = self.cfg[CONF_IMAP]
        host = imap[CONF_HOST]
        port = imap[CONF_PORT]
        user = imap[CONF_USERNAME]
        pwd = imap[CONF_PASSWORD]
        folder = imap.get("folder", DEFAULT_FOLDER)

        client = aioimaplib.IMAP4_SSL(host, port)
        try:
            await client.wait_hello_from_server()
            await client.login(user, pwd)
            await client.select(folder)
            uids = await fetch_unseen_uids(client, self.last_uid)
            new_numbers: Dict[str, List[str]] = {}
            for uid in uids:
                try:
                    resp = await client.uid('fetch', str(uid), '(RFC822)')
                    raw = b''.join(resp.lines[1:-1]) if len(resp.lines) > 2 else resp.lines[1]
                    msg = email.message_from_bytes(raw)
                    frm = _decode_header(msg.get('From', ''))
                    subj = _decode_header(msg.get('Subject', ''))
                    plain, html = _split_body(msg)
                    text_plain = f"{subj}\n{plain}"
                    text_html = f"{subj}\n{BeautifulSoup(html, 'html.parser').get_text()}" if html else text_plain
                    for ptn in self.patterns:
                        if not filter_by_sender(frm, ptn.from_filter):
                            continue
                        src = text_html if ptn.html else text_plain
                        codes = extract_tracking_numbers(src, ptn.regex)
                        for code in codes:
                            if code in self.seen_numbers:
                                continue
                            self.seen_numbers.add(code)
                            new_numbers.setdefault(ptn.name, []).append(code)
                            await self._async_forward(code, ptn.name)
                except Exception as err:  # noqa: BLE001
                    _LOGGER.error("Parse failure for UID %s: %s", uid, err)
                self.last_uid = uid
            await client.logout()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("IMAP connection error: %s", err)
            return
        await update_store(self.store, self.last_uid, self.seen_numbers)
        await update_entities(self, new_numbers)

    async def async_unload(self) -> None:
        if self._unsub:
            self._unsub()

    async def _async_forward(self, code: str, courier: str) -> None:
        if not self.forward_service:
            return
        try:
            dom, svc = self.forward_service.split('.')
            data = {
                **self.forward_data,
                "package_tracking_number": code,
                "package_friendly_name": courier,
            }
            await self.hass.services.async_call(dom, svc, data, blocking=False)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Forward service failed: %s", err)


# --- Sensor entities ------------------------------------------------------

class TrackItSensor(RestoreEntity, SensorEntity):
    """Sensor exposing tracking numbers for a single carrier."""

    _attr_should_poll = False

    def __init__(self, manager: TrackItManager, carrier: CarrierPattern) -> None:
        self.manager = manager
        self.carrier = carrier
        self._attr_name = f"TrackIt {carrier.name}"
        self._codes: List[str] = []
        self._attr_native_value = 0
        self._attr_unique_id = f"{DOMAIN}_{carrier.name}"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if state := await self.async_get_last_state():
            self._codes = list(state.attributes.get("tracking_numbers", []))
            self._attr_native_value = len(self._codes)

    def add_code(self, code: str) -> None:
        self._codes.append(code)
        self._attr_native_value = len(self._codes)
        self._attr_extra_state_attributes = {
            "tracking_numbers": list(self._codes),
            "last_update": utcnow().isoformat(),
        }
        self.async_write_ha_state()

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, "email")},
            "name": "TrackIt Mail Tracker",
        }

    async def async_update(self) -> None:  # pragma: no cover - manager handles updates
        """Trigger a manual scan if requested by Home Assistant."""
        await self.manager.async_scan()


# --- Setup ----------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    cfg = entry.data
    manager = TrackItManager(hass, cfg)
    await manager.async_setup()
    entities = []
    for ptn in manager.patterns:
        ent = TrackItSensor(manager, ptn)
        manager.entities[ptn.name] = ent
        entities.append(ent)
    async_add_entities(entities)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager

    async def _async_push(call: ServiceCall) -> None:
        code = call.data.get("code")
        courier = call.data.get("courier", "unknown")
        await manager._async_forward(code, courier)

    if not hass.services.has_service(DOMAIN, "push_tracking"):
        hass.services.async_register(DOMAIN, "push_tracking", _async_push)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    manager: TrackItManager | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if manager:
        await manager.async_unload()
    if DOMAIN in hass.data and not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)
        if hass.services.has_service(DOMAIN, "push_tracking"):
            hass.services.async_remove(DOMAIN, "push_tracking")
    return True


# TODO: Unit tests should cover extract_tracking_numbers and storage update logic.
