"""Timer für Midea-Entfeuchter (Typ 0xA1) aus midea_ac_lan.

midea_ac_lan bzw. midea-lan werten die Timer-Bytes der A1-Statusmeldung nicht aus
und können keinen Timer setzen. Diese Erweiterung hängt sich an das Geräteobjekt
von midea_ac_lan (hass.data["midea_ac_lan"]["devices"]), liest die Timer-Bytes
jeder Antwort mit und setzt den Timer per X48-Set mit Bit 7 im Lüfter-Byte.

Kodierung (am Comfee 0xA1 / 00000Q1A am 11.10.2026 verifiziert, Herkunft:
Chreece/ESPHome-Dehumidifier, Protokoll V1):
  body[4] Ein-Timer, body[5] Aus-Timer, body[6] Minuten-Nibble (oben Ein, unten Aus)
  Bit 7 = Timer aktiv, h = (b & 0x7C) >> 2,
  Restzeit = h * 60 + ((b & 3) + 1) * 15 - Nibble
  Setzen nur mit body[3] | 0x80, sonst ignoriert das Gerät die Timer-Bytes.
  Normale Befehle von midea_ac_lan (Timer-Bytes 00, ohne Bit 7) lassen den Timer stehen.
"""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant.const import CONF_DEVICE_ID, CONF_NAME, EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "midea_a1_timer"
MIDEA_DOMAIN = "midea_ac_lan"
CONF_DEVICES = "devices"
HEADER_LENGTH = 10
STATUS_BODY_TYPES = (0xC8, 0xA0)
MAX_HOURS = 24

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_DEVICES): vol.All(
                    cv.ensure_list,
                    [
                        vol.Schema(
                            {
                                vol.Required(CONF_DEVICE_ID): cv.positive_int,
                                vol.Required(CONF_NAME): cv.string,
                            }
                        )
                    ],
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def _minutes(raw: int, nibble: int) -> int:
    """Restminuten eines Timer-Bytes, 0 wenn nicht aktiv."""
    if not raw & 0x80:
        return 0
    return ((raw & 0x7C) >> 2) * 60 + ((raw & 0x03) + 1) * 15 - nibble


def _encode(hours: int) -> tuple[int, int]:
    """Timer-Byte und Nibble für volle Stunden (V1: h-1 Stunden + 60 Minuten)."""
    if hours <= 0:
        return 0x00, 0x00
    return 0x80 | (((hours - 1) & 0x1F) << 2) | 0x03, 0x00


class A1Timer:
    """Timer-Zustand eines A1-Geräts, gespeist aus den Antworten des Geräts."""

    def __init__(self, hass: HomeAssistant, device_id: int, name: str) -> None:
        self.hass = hass
        self.device_id = device_id
        self.name = name
        self.signal = f"{DOMAIN}_{device_id}"
        self.remaining: int | None = None
        self._device: Any = None
        self._last: tuple | None = None

    @property
    def available(self) -> bool:
        return self._device is not None and bool(getattr(self._device, "available", False))

    @callback
    def async_attach(self, *_: Any) -> None:
        """An das (ggf. nach einem Reload neue) Geräteobjekt von midea_ac_lan hängen."""
        device = self.hass.data.get(MIDEA_DOMAIN, {}).get("devices", {}).get(self.device_id)
        if device is None or device is self._device:
            return
        original = type(device).process_message.__get__(device)

        def process_message(msg: bytes) -> dict[str, Any]:
            status = original(msg)
            try:
                self._parse(msg)
            except Exception:  # Timer darf die Integration nie stören
                _LOGGER.exception("[%s] Timer-Bytes nicht lesbar: %s", self.device_id, msg.hex())
            return status

        device.process_message = process_message
        self._device = device
        _LOGGER.info("[%s] an midea_ac_lan-Gerät angehängt", self.device_id)
        async_dispatcher_send(self.hass, self.signal)

    def _parse(self, msg: bytes) -> None:
        """Läuft im Thread des Geräts."""
        body = msg[HEADER_LENGTH:-1]
        if len(body) < 8 or body[0] not in STATUS_BODY_TYPES:
            return
        power = bool(body[1] & 0x01)
        on_raw, off_raw, ext = body[4], body[5], body[6]
        if power:
            remaining = _minutes(off_raw, ext & 0x0F)
        else:
            remaining = _minutes(on_raw, (ext & 0xF0) >> 4)
        if (power, on_raw, off_raw, ext) == self._last:
            return
        self._last = (power, on_raw, off_raw, ext)
        self.remaining = remaining
        _LOGGER.debug("[%s] Timer %s/%s/%s -> %s min", self.device_id, hex(on_raw), hex(off_raw), hex(ext), remaining)
        self.hass.loop.call_soon_threadsafe(async_dispatcher_send, self.hass, self.signal)

    def set_hours(self, hours: int) -> None:
        """Timer setzen (0 = aus). Läuft im Executor."""
        device = self._device
        if device is None:
            raise RuntimeError("midea_ac_lan-Gerät nicht verfügbar")
        hours = max(0, min(MAX_HOURS, int(hours)))
        raw, nibble = _encode(hours)
        power = bool(device.attributes.get("power"))
        on_raw, off_raw = (0x00, raw) if power else (raw, 0x00)
        ext = nibble if power else nibble << 4
        message = device.make_message_set()
        base = type(message)

        class TimerSet(base):  # type: ignore[misc, valid-type]
            @property
            def _body(self) -> bytearray:
                body = bytearray(base._body.fget(self))
                body[2] |= 0x80
                body[3], body[4], body[5] = on_raw, off_raw, ext
                return body

        message.__class__ = TimerSet
        device.build_send(message)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    timers = [A1Timer(hass, d[CONF_DEVICE_ID], d[CONF_NAME]) for d in config[DOMAIN][CONF_DEVICES]]
    hass.data[DOMAIN] = timers

    @callback
    def attach_all(*_: Any) -> None:
        for timer in timers:
            timer.async_attach()

    # midea_ac_lan legt Geräteobjekte bei jedem Reload neu an, deshalb regelmäßig nachsehen.
    attach_all()
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, attach_all)
    async_track_time_interval(hass, attach_all, timedelta(seconds=30))

    for platform in (Platform.SELECT, Platform.SENSOR):
        hass.async_create_task(async_load_platform(hass, platform, DOMAIN, {}, config))
    return True
