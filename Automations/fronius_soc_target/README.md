# 🔋 Solar Battery SOC Target Control

A Home Assistant Blueprint for dynamic solar battery charge management — optimized for systems with a **Fronius inverter**, **BYD Battery Box**, and **Open-Meteo solar forecast**.

**Current version: v2** — two field-measured defects of v1 are fixed, see [What v2 changes](#what-v2-changes). It needs one additional helper.

🇩🇪 [Deutsche Version](/Automations/fronius_soc_target/README.de.md)

[![Open your Home Assistant instance and import this Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/Toxo666/HA_Blueprints/blob/main/Automations/fronius_soc_target/bms_fronius_soc_target.yaml)

---

## What it does

Instead of simply charging the battery as fast as possible, this automation distributes charging intelligently across three phases relative to the daily solar peak:

**Phase 1 — Before Peak (SOC below target)**
The battery is charged at a calculated rate to reach the configured *target SOC* (e.g. 55%) exactly at peak time. This keeps capacity free to absorb midday solar surplus.

**Phase 2 — Before Peak (SOC at or above target)**
The remaining headroom to the configured maximum SOC (e.g. 97%) is spread evenly over the full active window (time to peak + post-peak hours).

**Phase 3 — After Peak**
The battery is charged to the configured maximum, distributed across the remaining post-peak window. Fronius takes over in Auto mode once maximum SOC is reached.

In all phases, charging power is capped by the calculated demand rate to prevent overshooting. Grid draw is always prevented. If an EV is connected, the automation is inactive.

---

## Adaptive target SOC

If post-peak solar yield is not sufficient to charge the battery from `target_soc` to `soc_max`, the effective target SOC is automatically raised before the peak to compensate for the expected deficit.

**Example:** target = 55%, max = 97%, battery = 20.38 kWh → needs 8.56 kWh post-peak. If only 5 kWh is forecast → deficit 3.56 kWh → ~17.5% extra → effective target raised to 72.5%.

---

## What v2 changes

v1 had two defects that only showed up in operation:

**1. The ramp collapsed to zero.** The last commanded charge power was read back from the BMS charge limit `number`. That entity only exists in `PV Charge Limit` mode — in `Auto` it is `unavailable`, and `float(0)` turned it into a hard 0 W. The ramp restarted from scratch (observed three times within 40 minutes on 2026-07-18). v2 keeps its own memory in an `input_number` and writes the setpoint there **before** touching the number.

**2. Random branch selection.** The grid power was read as an instantaneous value from a meter that swings by kilowatts from second to second, so the up/down decision was close to a coin flip. The fix is not in the blueprint: feed it a **smoothed** grid sensor (a 5-minute mean via the Statistics integration) instead of the raw one.

A third fix guards against the peak time sensor being `unknown` while the solar forecast reloads — `as_datetime(None)` raised an `AttributeError` and discarded the whole control cycle (10 times on 2026-08-30). Such a cycle is now skipped silently; the next tick takes over.

---

## Requirements

- **Inverter:** Fronius (with BMS control via Modbus via [`fronius_modbus`](https://github.com/callifo/fronius_modbus) HACS integration — use the [@callifo](https://github.com/callifo) fork, it is actively maintained)
- **Battery:** BYD Battery Box Premium HV (or compatible BMS with `select` mode control and `number` charge limit entity)
- **Solar Forecast:** [Open-Meteo Solar Forecast](https://github.com/flowolf/ha-open-meteo-solar-forecast) HACS integration with `wh_period` attribute and a *remaining* sensor
- **Grid Meter:** Any energy meter with signed grid power (negative = feed-in), e.g. Shelly Pro 3EM
- **Helper (required):** one `input_number` as the memory for the last commanded charge power — see `package_bms_soc_target.yaml`
- **Smoothed grid sensor (strongly recommended):** a 5-minute mean of the grid power, created via **Settings → Devices & Services → Helpers → Statistics**. Pass that sensor as `grid_power_sensor` instead of the raw meter.
- **EV Charging (optional):** [evcc](https://evcc.io/) with [ha-evcc](https://github.com/marq24/ha-evcc) HACS integration with binary `connected` sensors per charger

---

## Configuration

| Parameter | Description | Default for ex. 10kwp |
|-----------|-------------|---------|
| Peak time sensor (`peak_time_sensor`) | Open-Meteo sensor with today's time of highest solar output | — |
| Solar forecast sensor (`solar_forecast_sensor`) | Daily forecast sensor (kWh, requires `wh_period` attribute) | — |
| Remaining yield today (`remaining_sensor`) | Expected remaining solar yield for today (kWh) | — |
| Battery SOC sensor (`soc_sensor`) | Current battery state of charge (%) | — |
| PV power sensor (`pv_power_sensor`) | Total current output of the solar system (W) | — |
| Grid power sensor (`grid_power_sensor`) | Grid power in W — negative = feed-in, positive = draw | — |
| BMS control mode (`control_mode_select`) | Select entity for BMS operating modes | — |
| Charge limit entity (`charge_limit_number`) | Number entity for BMS charge power setpoint (W) | — |
| Last command memory (`last_cmd_helper`) | `input_number` storing the last commanded charge power — v2, prevents the ramp from resetting | — |
| EV connected sensor (`ev_connected_sensor_1/2`) | Optional: EVCC binary sensor per charger — automation is inactive while an EV is connected | *(none)* |
| Mode when charging (`option_on_load`) | BMS mode while the automation is actively controlling charge | `PV Charge Limit` |
| Mode when inactive (`option_off_load`) | BMS mode when the automation is not intervening | `Auto` |
| Battery capacity (`battery_capacity_kwh`) | Usable battery capacity — basis for power calculations (kWh) | `10.0` |
| Target SOC at peak (`target_soc_at_peak`) | Desired SOC at the time of peak solar output — remaining headroom absorbs the midday surplus (%) | `55` |
| SOC maximum (`soc_max`) | Above this SOC the automation switches to Auto — Fronius takes over feed-in management (%) | `97` |
| Maximum charge power (`max_charge_power`) | Hardware upper limit for charge power (W) | `6000` |
| Minimum charge power (`min_charge_power`) | Lower floor when calculated demand is very small, e.g. with a long lead time (W) | `500` |
| Pre-peak hours (`pre_peak_hours`) | Hours before peak at which the automation becomes active | `7` |
| Post-peak hours (`post_peak_hours`) | Hours after peak during which the automation continues — then switches to Auto mode | `2` |
| Grid feed-in limit (`grid_feed_limit`) | Feed-in power limit per §14a EnWG or grid operator requirement (W) | `7200` |
| Tolerance (`tolerance`) | Margin below the feed-in limit at which charge power starts ramping up — should match the step size (W) | `350` |
| Step size (`step_w`) | Power adjustment per regulation cycle when ramping up or down (W) | `500` |
| Minimum daily forecast (`forecast_limit`) | Forecasted daily yield must exceed this value — otherwise automation stays inactive (bad weather) (kWh) | `40` |
| Minimum peak energy (`peak_power_limit`) | Forecasted peak-hour energy must exceed this value — otherwise automation stays inactive (kWh) | `7.5` |
| Read scale factor (`read_scale_factor`) | Correction divisor for reading back the current charge limit from the BMS — normally 1 | `1` |

---

## How the charge power is regulated

Every 5 minutes (or on peak sensor change), the automation evaluates the current grid power. Feed it the **smoothed** sensor — with raw instantaneous values the branch below is chosen more or less at random:

- **Grid draw (> +100 W):** Reduce charge power by one step → protect against grid draw
- **Feed-in below limit:** Ramp up by one step, capped at `required_w`
- **At or above feed-in limit:** Ramp up by one step, capped at `required_w`

The automation is deactivated (switches to `off_mode`) when:
- Outside the active time window (defined by hours before and after peak: `pre_peak_hours`, `post_peak_hours`)
- SOC has reached the configured maximum (`soc_max`)
- EV is connected (`ev_connected_sensor_1/2`)
- Daily forecast is below the minimum threshold for activation (`forecast_limit`)
- Peak-hour energy is below the minimum threshold for activation (`peak_power_limit`)

---

## My setup

Tested with:
- Fronius Symo Gen24 Plus 10.0 with BYD Battery Box Premium HV 20.38 kWh
- [`fronius_modbus`](https://github.com/callifo/fronius_modbus) by [@callifo](https://github.com/callifo) (HACS) — the actively maintained fork I recommend
- Open-Meteo Solar Forecast (HACS)
- Shelly Pro 3EM as grid meter
- evcc with Wattpilot and NRGKick
<img width="780" height="1959" alt="Screenshot 2026-04-12 at 20-39-18 Automationen – Home Assistant" src="https://github.com/user-attachments/assets/e80d2e24-d311-4001-b75e-190dda559285" />


---

## Notes

- The automation runs in `single` mode — overlapping executions are dropped, not queued.
- evcc resets EV charge limits to 80% on connect, so no special handling is needed there.
- The `wh_period` attribute from the Open-Meteo forecast sensor is used for post-peak yield calculation. If unavailable, the `remaining` sensor is used as fallback.

---

## Acknowledgements

Big thanks to [@callifo](https://github.com/callifo) for maintaining [`fronius_modbus`](https://github.com/callifo/fronius_modbus) — the actively maintained Home Assistant integration for Fronius inverters with Modbus BMS control. This blueprint would not be possible without it.

---

## License

MIT License — feel free to use, modify, and share.
