"""Timer-Auswahl (Aus, 1–24 h) für Midea-A1-Entfeuchter."""

from __future__ import annotations

import math

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN, MAX_HOURS, A1Timer

OFF = "Aus"
OPTIONS = [OFF] + [f"{h} h" for h in range(1, MAX_HOURS + 1)]


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    if discovery_info is None:
        return
    async_add_entities(TimerSelect(t) for t in hass.data[DOMAIN])


class TimerSelect(SelectEntity):
    """Zeigt den Timer wie das Display (angefangene Stunden) und setzt ihn."""

    _attr_should_poll = False
    _attr_icon = "mdi:timer-outline"
    _attr_options = OPTIONS

    def __init__(self, timer: A1Timer) -> None:
        self._timer = timer
        self._attr_name = f"{timer.name} Timer"
        self._attr_unique_id = f"{timer.device_id}_timer"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._timer.signal, self.async_write_ha_state)
        )

    @property
    def available(self) -> bool:
        return self._timer.available and self._timer.remaining is not None

    @property
    def current_option(self) -> str | None:
        remaining = self._timer.remaining
        if remaining is None:
            return None
        if remaining <= 0:
            return OFF
        return f"{min(MAX_HOURS, math.ceil(remaining / 60))} h"

    async def async_select_option(self, option: str) -> None:
        hours = 0 if option == OFF else int(option.split()[0])
        await self.hass.async_add_executor_job(self._timer.set_hours, hours)
