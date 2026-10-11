"""Timer-Restzeit für Midea-A1-Entfeuchter."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt as dt_util

from . import DOMAIN, A1Timer


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    if discovery_info is None:
        return
    async_add_entities(TimerRemainingSensor(t) for t in hass.data[DOMAIN])


class TimerRemainingSensor(SensorEntity):
    """Restzeit in Minuten, 0 = kein Timer; Attribut ende = voraussichtliches Ende."""

    _attr_should_poll = False
    _attr_icon = "mdi:timer-sand"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, timer: A1Timer) -> None:
        self._timer = timer
        self._attr_name = f"{timer.name} Timer Restzeit"
        self._attr_unique_id = f"{timer.device_id}_timer_remaining"
        self._end: str | None = None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, self._timer.signal, self._update))

    @callback
    def _update(self) -> None:
        remaining = self._timer.remaining
        if remaining:
            self._end = (dt_util.now() + timedelta(minutes=remaining)).strftime("%H:%M")
        else:
            self._end = None
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self._timer.available and self._timer.remaining is not None

    @property
    def native_value(self) -> int | None:
        return self._timer.remaining

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"ende": self._end}
