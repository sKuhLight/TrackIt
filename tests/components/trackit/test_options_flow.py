import pytest

from custom_components.trackit import config_flow
from custom_components.trackit.const import (
    CONF_SCAN_INTERVAL,
    CONF_SENSOR_STATE_MODE,
    CONF_MAX_MATCHES,
    CONF_NAME,
    CONF_VENDORS,
)


@pytest.mark.asyncio
async def test_options_flow_add_dhl(config_entry):
    flow = config_flow.TrackItOptionsFlow(config_entry)
    await flow.async_step_init()
    await flow.async_step_init({"action": "add_dhl"})
    result = await flow.async_step_init({"action": "settings"})
    result = await flow.async_step_settings(
        {
            CONF_SCAN_INTERVAL: 5,
            CONF_SENSOR_STATE_MODE: "count",
            CONF_MAX_MATCHES: 10,
            CONF_NAME: "TrackIT",
        }
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_VENDORS][0]["name"] == "DHL"
