"""Sensor platform for TrackIT."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_STATE_MOST_RECENT,
    CONF_SENSOR_STATE_MODE,
    DEFAULT_SENSOR_STATE_MODE,
    ATTR_MATCHES,
    ATTR_LAST_SCAN,
)
from .coordinator import TrackItCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: TrackItCoordinator = data["coordinator"]
    async_add_entities([TrackItSensor(coordinator, entry)])


class TrackItSensor(CoordinatorEntity[TrackItCoordinator], SensorEntity):
    """Representation of the TrackIT sensor."""

    _attr_icon = "mdi:package-variant-closed"

    def __init__(self, coordinator: TrackItCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = entry.options.get("name", "TrackIT")
        self._attr_unique_id = entry.entry_id

    @property
    def available(self) -> bool:
        if self.coordinator.last_update is None:
            return True
        return self.coordinator.last_update_success

    @property
    def state(self) -> str | int | None:
        mode = self._entry.options.get(
            CONF_SENSOR_STATE_MODE, DEFAULT_SENSOR_STATE_MODE
        )
        data = self.coordinator.data or []
        if mode == SENSOR_STATE_MOST_RECENT:
            if data:
                return data[0]["tracking_id"]
            return None
        return len(data)

    @property
    def extra_state_attributes(self):
        return {
            ATTR_MATCHES: self.coordinator.data,
            ATTR_LAST_SCAN: self.coordinator.last_update.isoformat()
            if self.coordinator.last_update and self.coordinator.last_update_success
            else None,
            "mailbox": self._entry.data.get("mailbox"),
            "scan_window_days": self._entry.data.get("scan_window_days"),
            "unseen_only": self._entry.data.get("unseen_only"),
        }
