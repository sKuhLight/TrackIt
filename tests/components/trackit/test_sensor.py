import datetime as dt

from custom_components.trackit.const import ATTR_MATCHES
from custom_components.trackit.sensor import TrackItSensor


class DummyCoordinator:
    data = [{"supplier": "DHL", "tracking_id": "123"}]
    last_update_success_time = dt.datetime.now()


def test_sensor_state(config_entry):
    coordinator = DummyCoordinator()
    sensor = TrackItSensor(coordinator, config_entry)
    assert sensor.state == 1
    attrs = sensor.extra_state_attributes
    assert attrs[ATTR_MATCHES][0]["tracking_id"] == "123"
