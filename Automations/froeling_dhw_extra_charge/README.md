# 🚿 Fröling DHW Extra Charge Control

A Home Assistant Blueprint for domestic hot water (DHW) on a **Fröling pellet boiler**. It charges at night, at the coldest forecast hour, and only when the water is actually going to run short — plus a companion automation that records whether a charge *really happened*.

🇩🇪 [Deutsche Version](/Automations/froeling_dhw_extra_charge/README.de.md)

[![Open your Home Assistant instance and import this Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/sbstn-0x2a/HA_Blueprints/blob/main/Automations/froeling_dhw_extra_charge/froeling_dhw_extra_charge.yaml)

---

## What it does

Instead of reheating whenever the tank drops below a threshold, this automation predicts when the water will be too cold and charges once, at the best moment of the night.

**Comfort-first night charging**
Every 10 minutes the blueprint projects the tank temperature forward using Newton's law of cooling, `T(t) = T_room + (T0 − T_room)·e^(−k·t)`. If the forecast for either the next **morning** or the next **evening** target time falls below the minimum temperature, a charge is scheduled.

**Timing by weather forecast**
The charge is placed at the **coldest hourly value** of the night (lowest condensate risk in the chimney), but early enough to finish `charge_duration_hours` before the morning target. The outside temperature decides *when*, never *whether* — it is a timing optimiser, not a gate.

**Emergency floor**
Below `min_temperature − 3 °C` the blueprint charges at any time of day. This is a safety net and should rarely fire.

**Hard plant-state guard**
If the boiler's plant state is not in the allowed list, no command is sent at all — including the emergency floor.

---

## The core idea: a command is not a charge

A blueprint can only *send* a command. Whether the boiler actually heats the water is a different question, and in practice the two come apart more often than you would expect:

- The burner starts and then **faults out** — the tank gains 5 °C instead of 25 °C.
- The boiler **restarts by itself** hours later to finish an unfinished extra charge — no command involved.
- The tank is heated as a **side effect** of a buffer/heating run — again, no command.
- Someone triggers an extra charge **by hand**, at the boiler panel or in HA.

Earlier versions wrote "last charge = now" the moment the command went out. The dashboard then claimed success while the tank sat at 46 °C, and the 6-hour lockout ran against a charge that never happened.

This version therefore keeps **two separate timestamps**:

| Helper | Written by | Meaning |
|---|---|---|
| `input_datetime.letzter_brauchwasser_befehl` | the blueprint | when a command was sent — drives the lockout only |
| `input_datetime.letzte_brauchwasser_ladung` | the detection automation | when the water actually got warmer, whatever the cause |

---

## Two components

| File | Purpose |
|---|---|
| `froeling_dhw_extra_charge.yaml` | the blueprint — decides *if* and *when* to command a charge |
| `package_brauchwasser.yaml` | helpers + the automation `Brauchwasser – Ladung erfassen`, which detects real charges and labels their source |

**Both are required.** The blueprint writes to three helpers defined in the package, so it will not work on its own.

---

## Requirements

- **Boiler:** Fröling pellet boiler with a Home Assistant integration exposing
  - a DHW top temperature sensor
  - an entity that triggers the extra charge (`button`, `switch`, `water_heater` or `select`)
  - a boiler state sensor (for detecting burner starts)
  - a plant state sensor (for the guard)
- **Ambient sensor:** a temperature sensor in the boiler room — used only for the cooling model
- **Weather (optional):** any `weather` entity with hourly forecast via `weather.get_forecasts` (e.g. DWD). Leave empty to charge at the latest possible time instead.
- **Packages enabled** in `configuration.yaml`:
  ```yaml
  homeassistant:
    packages: !include_dir_named packages
  ```

---

## Installation

1. **Import the blueprint** with the badge above, or copy `froeling_dhw_extra_charge.yaml` to `config/blueprints/automation/froeling/`.

2. **Copy `package_brauchwasser.yaml`** to `config/packages/`.

3. **Adjust the entity IDs in the package.** The detection automation references four entities directly — they are not blueprint inputs:

   | Placeholder in the file | What to put there | Occurrences |
   |---|---|---|
   | `sensor.boiler_1_temperatur_oben` | your DHW top temperature sensor | 4 |
   | `select.12345_boiler_01_mode` | your extra-charge entity | 2 |
   | `sensor.12345_kessel_state` | your boiler state sensor | 1 |
   | `sensor.anlagenzustand` | your plant state sensor | 1 |

   Also check the two state strings: `"Vorbereitung"` (the boiler state that marks a burner start) and `"Extraladen"` (the extra-charge option). Both depend on your integration's language.

4. **Check the helper collision.** The package defines `input_datetime.letzte_brauchwasser_ladung` and `input_text.grund_brauchwasser_ladung`. If you already have them as UI helpers, delete those or comment out the entries — otherwise the entity IDs collide. A comment block in the file marks the spot.

5. **Restart Home Assistant.** A YAML reload is not enough, because the package adds new helper entities.

6. **Create the automation** from the blueprint and fill in the inputs (see below). Set `plant_state_sensor` to your plant state entity — without it the guard is inactive.

7. **Verify.** After the next 10-minute cycle, `input_text.brauchwasser_warte_grund` should contain a plain-text reason such as `🌙 Nachtladung geplant 13.09 02:00`. If it stays empty, the automation is not running.

---

## Configuration

| Input | Description | Default |
|---|---|---|
| `water_temperature_sensor` | DHW tank temperature, top sensor | — |
| `outdoor_temperature_sensor` | Ambient temperature at the tank — cooling model only, never a gate | — |
| `weather_forecast_entity` | Weather entity with hourly forecast; empty = charge at the latest possible time | *(none)* |
| `extra_charge_service` | Entity that triggers the extra charge | — |
| `extra_charge_select_option` | Option to select if the entity is a `select` | `Extraladen` |
| `min_temperature` | Minimum DHW temperature at the target times (°C) | `45` |
| `morning_ready_time` | Time the water must be hot in the morning | `05:00` |
| `evening_ready_time` | Time the water must be hot in the evening | `18:00` |
| `night_charge_earliest` | Earliest start of the night charging window | `22:00` |
| `charge_duration_hours` | How long a full charge takes — sets the latest possible start (h) | `2.5` |
| `min_charge_interval` | Lockout between two commands (min) | `360` |
| `prediction_activation_threshold` | Prediction only becomes active below this tank temperature (°C) | `52` |
| `heat_loss_coefficient` | Cooling rate `k` in the Newton model (1/h) | `0.011` |
| `plant_state_sensor` | Plant state entity; empty disables the guard | *(none)* |
| `plant_state_allowed` | Comma list of plant states in which charging is allowed | `Brauchwasser` |
| `status_sensor` | `input_text` for the one-line status | *(none)* |
| `next_charge_sensor` | `input_datetime` for the next charge time | *(none)* |
| `reason_sensor` | `input_text` for the plain-text reason | *(none)* |

### Finding your heat loss coefficient

`k` describes how fast your tank cools. Take two temperatures a few hours apart with no draw-off, then

```
k = ln((T0 − T_room) / (T1 − T_room)) / hours
```

`0.011 1/h` corresponds to roughly 0.59 °C/h at a 54 K difference. Larger value = worse insulation.

---

## How a charge is detected

The detection automation does not trust commands — it watches the temperature.

- **Start:** the tank rises **4 K above the tracked low point**. The low point follows the temperature down while cooling and up during a charge. 4 K is deliberate: a 1–2 K sensor wobble must not count.
- **End:** **30 minutes without any change** in the measured value. During a charge it changes every 1–3 minutes, while cooling only every few hours.
- **Result:** `grund_brauchwasser_ladung` ends up as e.g. `Automation · 41→66 °C`. A failed charge is visible as `41→46 °C`.

### Source labelling

The source is determined per **burner start** (boiler state → `Vorbereitung`), not per charge:

| Condition | Source |
|---|---|
| Start within 5 min of a command | `Automation` |
| later, command still open | `Kessel-Wiederanlauf` (boiler restart) |
| extra-charge entity active, no command | `Extraladung von Hand` (manual) |
| plant state = allowed state | `Kessel-/Pufferladung` (buffer run) |
| plant state = heating mode | `Heizbetrieb` |
| otherwise | `Fremdstart` |

The 5-minute window is generous: measured over 8 charges, the delay between command and burner start was 82–127 seconds. A later start cannot be the automation anyway — the lockout prevents it.

---

## Notes

- Runs every 10 minutes, `mode: single`, `max_exceeded: silent`.
- **Winter operation:** if your plant switches to a heating mode for the cold season, `plant_state_allowed: Brauchwasser` will silence the automation completely. Add the heating state to the list, e.g. `Brauchwasser, Automatik`.
- The blueprint's UI strings and the helper entity IDs are German. Renaming the helpers means editing both files.
- The status line is capped at 255 characters by `input_text`.
- The blueprint never reads the boiler state itself — burner starts are evaluated only in the package automation.

---

## License

MIT License — feel free to use, modify, and share.
