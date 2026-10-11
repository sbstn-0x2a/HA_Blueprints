# 💧 Comfee CDDKE-16DEN7 (EU) Dehumidifier in Home Assistant

A Comfee **CDDKE-16DEN7 (EU)** dehumidifier (Midea device type `0xA1`), integrated into Home Assistant fully locally. The HACS integration **Midea AC LAN** provides the basic control. On top of that come the correct mode and fan speed mapping, a small add-on for the **device timer (1–24 h)**, which Midea AC LAN does not support, and a Bubble Card for the dashboard.

🇩🇪 [Deutsche Version](/Integrations/comfee_dehumidifier/README.de.md)

---

## Components

| Part | File / source | Purpose |
|---|---|---|
| Integration | HACS **[Midea AC LAN](https://github.com/wuwentao/midea_ac_lan)** (`midea_ac_lan`) | on/off, target humidity, mode, current humidity |
| Options | "Customize" + `Fan Speed` switch in the config entry | correct modes and fan speeds |
| Add-on | `custom_components/midea_a1_timer/` | read and set the timer |
| Configuration | `package_comfee_entfeuchter.yaml` | loads the add-on |
| Card | `dashboard_card.yaml` | dashboard control (Bubble Card) |

Resulting entities (`<id>` = the device ID in Midea AC LAN):

| Entity | Source |
|---|---|
| `humidifier.<id>_humidifier` | Midea AC LAN (on/off, target, mode, current humidity as attribute) |
| `select.<id>_fan_speed` | Midea AC LAN, after step 3 |
| `select.comfee_luftentfeuchter_timer` | midea_a1_timer (`Aus`, `1 h` … `24 h`) |
| `sensor.comfee_luftentfeuchter_timer_restzeit` | midea_a1_timer (minutes, attribute `ende` = HH:MM) |

Tested device: Comfee **CDDKE-16DEN7 (EU)**, type `0xA1`, model `00000Q1A`, subtype `41377`, protocol V3.

---

## 1. Connect the device to Wi-Fi

1. Add the device to your Wi-Fi with the manufacturer app (MSmartHome). It supports 2.4 GHz only.
2. Reserve a **fixed IP** on your router.
3. Check that the device is reachable: `nc -z -w1 <ip> 6444`.

---

## 2. Set up Midea AC LAN

1. HACS → install **Midea AC LAN**, restart HA.
2. *Settings → Devices & services → Add integration → Midea AC LAN*.
3. **With saved credentials (preferred):** choose "Configure manually" and enter device ID, type `161`, IP, port `6444`, model, subtype, protocol `3`, token and key.
4. **Without saved credentials:** choose "Discover automatically" and enter the **device IP**. "auto" does not work if the device sits in a different VLAN/subnet, because the broadcast does not reach it. In the login step choose "Skip Login (input any user/password)", or use your MSmartHome account.
5. **Back up the token and key right away** (outside of Git!). Midea is gradually shutting down token retrieval via the cloud. Without a backup you may not be able to add the device again later. The values are also stored in `/config/.storage/midea_ac_lan/<id>.json`.

---

## 3. Options: modes and fan speeds

The integration's default list does not match this device. Without customizing, HA shows `mode: null` and offers modes the device does not know (`manual`, `continuous`, `shoes_dry`). The real codes were determined from a capture (mode button on the device: auto → silent → dryer):

| Code | Mode | Fan |
|---|---|---|
| 11 | auto | selectable |
| 10 | silent | fixed low |
| 4 | dryer | fixed high |

Fan codes: 40 low, 60 medium, 80 high.

*Midea AC LAN → device → Configure:*

- **Switches:** tick `Fan Speed`. This creates `select.<id>_fan_speed`.
- **Customize:**
  ```json
  {"modes":{"11":"auto","10":"silent","4":"dryer"},"speeds":{"40":"low","60":"medium","80":"high"}}
  ```
- Polling interval: 30 s (default).

**Finding the codes for a different device:** use `logger.set_level` to set `midealan: debug`, cycle through all modes and speeds on the device (leave each for about 40 s because of the 30 s interval), and read the `Received:` lines in the log (`'mode': …, 'fan_speed': …`). Set the level back to `info` afterwards.

---

## 4. Timer add-on `midea_a1_timer`

Midea AC LAN and its library `midea-lan` neither parse the timer bytes of the A1 status message nor can they set a timer. `midea_a1_timer` is a small custom integration without its own entry under "Devices & services":

- It is loaded via YAML and attaches to the Midea AC LAN device object (`hass.data["midea_ac_lan"]["devices"]`).
- It reads the timer bytes from every device response, so it adds no extra polling.
- It sets the timer with a raw command (X48 set).
- Midea AC LAN recreates its device objects on every reload, so the add-on checks every 30 s and re-attaches when needed.

A HACS update of Midea AC LAN leaves the add-on untouched. It can only break if `midea-lan` changes the methods `process_message`, `make_message_set` or `build_send`. In that case the log shows "Timer-Bytes nicht lesbar", or the timer entities stay `unavailable`.

### Installation

1. Copy the folder `custom_components/midea_a1_timer/` to `/config/custom_components/midea_a1_timer/`.
2. Copy `package_comfee_entfeuchter.yaml` to `/config/packages/` and set `device_id` to your device ID. Packages must be enabled in `configuration.yaml`:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
3. Check the configuration and **restart HA**. A reload is not enough, because the integration is new.
4. Within 30 s after startup the log shows:
   `[custom_components.midea_a1_timer] [<id>] an midea_ac_lan-Gerät angehängt`.
   The entities become available as soon as the first status message from the device arrives.

For several devices, add more entries under `devices:`.

### Protocol (background)

- **Status** (body type `C8` for queries, `A0` for command responses): `body[4]` = on timer, `body[5]` = off timer, `body[6]` = minute nibble (high = on, low = off). `7f 7f 00` = no timer.
- **Remaining time** = h·60 + ((b & 3) + 1)·15 − nibble, with h = (b & 0x7C) >> 2 and bit 7 = timer active.
  Measured: `84 0f` = 60 min, `83 01` = 59 min, `88 0f` = 120 min.
- **Setting:** X48 set with **bit 7 in the fan byte** (`body[3] | 0x80`). Without this bit the device ignores the timer bytes. Full hours h are encoded as (h − 1) hours + 60 min: 1 h = `0x83`, 2 h = `0x87`, 24 h = `0xDF`, nibble 0. All `0x00` with bit 7 = timer off.
- If the device is on, the off timer is set, otherwise the on timer.
- Regular commands from Midea AC LAN (timer bytes `00`, no bit 7) leave a running timer untouched.
- Source of the encoding: [Chreece/ESPHome-Dehumidifier](https://github.com/Chreece/ESPHome-Dehumidifier) (protocol V1), verified on the Comfee CDDKE-16DEN7 (model `00000Q1A`).

---

## 5. Dashboard card

Requires the HACS frontend card **[Bubble Card](https://github.com/Clooos/Bubble-Card)** (tested with 3.4.1). Paste the content of `dashboard_card.yaml` as a card and replace `123456789012345` with your device ID.

- `step: 5`: the device only accepts steps of 5 and rounds to the nearest one (73 → 75, 72 → 70, 68 → 70).
- `state_content: current_humidity` shows the device's current humidity (in 1 % steps).
- A "Steuerung" group holds mode, fan and timer as selects.
- The remaining time only shows while a timer is running (`visibility`).

---

## 6. Checklist

1. `humidifier.<id>_humidifier` lists only `dryer, silent, auto` in `available_modes` and has a mode (not `null`).
2. Change the fan speed in HA: the device follows.
3. Set the timer to 1 h in HA: the display shows 1 h and the remaining time is about 60 min. Then set the timer on the device: HA picks it up within 30 s.
4. Set the timer to "Aus": the remaining time drops to 0 and the "Rest" row disappears from the card.

---

## Notes

- **Hysteresis:** the device apparently does not decide continuously whether the compressor runs. Observed: at 55 % actual and 70 % target, the compressor kept running and only stopped 4 s after the target was changed. So it probably waits for a minimum run time or only reacts to a settings change. A proper measurement with a dedicated metering plug is still open (compressor ≈ 150–200 W).
- The timer entities use German names and options (`Aus`, `Restzeit`, attribute `ende`). If you rename them, adjust the card.
- Token and key do **not** belong in the repository.

---

## License

MIT License — feel free to use, modify, and share.
