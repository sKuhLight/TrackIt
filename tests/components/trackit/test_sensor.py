import datetime as dt

from custom_components.trackit.const import ATTR_MATCHES
from custom_components.trackit.sensor import TrackItSensor


class DummyCoordinator:
    data = [{"supplier": "DHL", "tracking_id": "123"}]
    last_update = dt.datetime.now()
    last_update_success = True


def test_sensor_state(config_entry):
    coordinator = DummyCoordinator()
    sensor = TrackItSensor(coordinator, config_entry)
    assert sensor.state == 1
    attrs = sensor.extra_state_attributes
    assert attrs[ATTR_MATCHES][0]["tracking_id"] == "123"


def test_sensor_available_during_initial_refresh(config_entry):
    class DummyCoord:
        data = []
        last_update = None
        last_update_success = False

    sensor = TrackItSensor(DummyCoord(), config_entry)
    assert sensor.available


def test_sensor_unavailable_on_failure(config_entry):
    class DummyCoord:
        data = []
        last_update = dt.datetime.now()
        last_update_success = False

    sensor = TrackItSensor(DummyCoord(), config_entry)
    assert not sensor.available
