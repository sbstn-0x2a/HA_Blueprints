# 🔋 Solar Battery SOC Target Control

Ein Home Assistant Blueprint zur dynamischen Solarakku-Ladesteuerung — optimiert für Anlagen mit **Fronius-Wechselrichter**, **BYD Battery Box** und **Open-Meteo Solar Forecast**.

🇬🇧 [English version](/Automations/fronius_soc_target/README.md)

[![Blueprint in Home Assistant importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/Toxo666/HA_Blueprints/blob/main/Automations/fronius_soc_target/bms_fronius_soc_target.yaml)

---

## Was macht die Automation?

Statt den Akku einfach so schnell wie möglich zu laden, verteilt diese Automation die Ladung intelligent über drei Phasen relativ zum täglichen Leistungspeak:

**Phase 1 — Vor dem Peak (SOC unter Zielwert)**
Der Akku wird mit berechneter Leistung geladen, um den konfigurierten *Ziel-SOC* (z.B. 55%) genau zum Zeitpunkt des Peaks zu erreichen. So bleibt ausreichend Kapazität frei, um die mittägliche Solarspitze zu absorbieren.

**Phase 2 — Vor dem Peak (SOC bereits am oder über Zielwert)**
Der verbleibende Laderaum bis zum konfigurierten Maximum (z.B. 97%) wird gleichmäßig über das gesamte aktive Zeitfenster (bis Peak + Nachlaufzeit) verteilt.

**Phase 3 — Nach dem Peak**
Der Akku wird kontrolliert auf das Maximum geladen, verteilt auf die verbleibende Nachlaufzeit. Hat der SOC das Maximum erreicht, übernimmt der Fronius im Auto-Modus.

In allen Phasen wird die Ladeleistung durch die berechnete Bedarfsrate gedeckelt, um Überschießen zu vermeiden. Netzbezug wird stets verhindert. Ist ein E-Auto angesteckt, ist die Automation inaktiv.

---

## Adaptiver Ziel-SOC

Wenn der Post-Peak-Solarertrag nicht ausreicht, um den Akku von `target_soc` auf `soc_max` zu laden, wird der effektive Ziel-SOC vor dem Peak automatisch angehoben, um das erwartete Defizit auszugleichen.

**Beispiel:** Ziel = 55%, Maximum = 97%, Akku = 20.38 kWh → benötigt 8.56 kWh nach Peak. Prognose nur 5 kWh → Defizit 3.56 kWh → ~17.5% extra → effektiver Ziel-SOC wird auf 72.5% angehoben.

---

## Voraussetzungen

- **Wechselrichter:** Fronius (mit BMS-Steuerung via Modbus, Integration [`fronius_modbus`](https://github.com/callifo/fronius_modbus) via HACS — empfohlen wird der Fork von [@callifo](https://github.com/callifo), der aktiv gepflegt wird)
- **Akku:** BYD Battery Box Premium HV (oder kompatibles BMS mit `select`-Modusentität und `number`-Ladeleistungsentität)
- **Solarprognose:** [Open-Meteo Solar Forecast](https://github.com/flowolf/ha-open-meteo-solar-forecast) via HACS, mit `wh_period`-Attribut und einem *Remaining*-Sensor
- **Stromzähler:** Beliebiger Energiezähler mit vorzeichenbehafteter Netzleistung (negativ = Einspeisung), z.B. Shelly Pro 3EM
- **E-Auto-Laden (optional):** [evcc](https://evcc.io/) mit binären `connected`-Sensoren je Ladepunkt

---

## Konfiguration

| Parameter | Beschreibung | Standard |
|-----------|--------------|---------|
| Peakzeit-Sensor (`peak_time_sensor`) | Open-Meteo Sensor mit dem Zeitpunkt der höchsten Leistung heute | sensor.power_highest_peak_time_today |
| Solar Forecast Sensor (`solar_forecast_sensor`) | Open-Meteo Tagesprognose-Sensor (kWh, benötigt `wh_period`-Attribut) | sensor.energy_production_today |
| Verbleibender Tagesertrag (`remaining_sensor`) | Open-Meteo Noch erwarteter Solarertrag heute (kWh) | sensor.energy_production_today_remaining |
| Akku SOC Sensor (`soc_sensor`) | Aktueller Ladestand des Akkus (%) | — |
| PV-Leistung (`pv_power_sensor`) | Gesamte aktuelle Ausgangsleistung der Solaranlage (W) | — |
| Netzsensor (`grid_power_sensor`) | Netzleistung in W — negativ = Einspeisung, positiv = Bezug | — |
| BMS Steuerungsmodus (`control_mode_select`) | Select-Entität für die Betriebsmodi des BMS | — |
| Ladeleistungs-Entität (`charge_limit_number`) | Number-Entität für die Ladeleistungsvorgabe ans BMS (W) | — |
| E-Auto angesteckt (`ev_connected_sensor_1/2`) | Optional: EVCC Binary Sensor je Ladepunkt — Automation ist inaktiv solange ein Auto angesteckt ist | *(keiner)* |
| Modus bei aktivem Laden (`option_on_load`) | BMS-Betriebsmodus solange die Automation aktiv lädt | `PV Charge Limit` |
| Modus bei inaktivem Laden (`option_off_load`) | BMS-Betriebsmodus wenn die Automation nicht eingreift | `Auto` |
| Akku-Kapazität (`battery_capacity_kwh`) | Nutzbare Kapazität des Akkus — Grundlage für die Leistungsberechnung (kWh) | `10.0` |
| Ziel-SOC bei Peak (`target_soc_at_peak`) | Gewünschter Ladestand zum Zeitpunkt des Leistungspeaks — der verbleibende Puffer absorbiert die solare Mittagsspitze (%) | `55` |
| SOC-Maximum (`soc_max`) | Ab diesem Ladestand schaltet die Automation auf Auto — der Fronius übernimmt dann das Einspeisemanagement (%) | `97` |
| Maximale Ladeleistung (`max_charge_power`) | Hardware-Obergrenze der Ladeleistung (W) | `6000` |
| Minimale Ladeleistung (`min_charge_power`) | Untergrenze bei sehr kleinem berechnetem Bedarf, z.B. bei langem Vorlauf (W) | `500` |
| Vorlaufzeit vor Peak (`pre_peak_hours`) | Stunden vor dem Peak, ab denen die Ladesteuerung aktiv wird | `7` |
| Nachlaufzeit nach Peak (`post_peak_hours`) | Stunden nach dem Peak, in denen die Steuerung noch weiterläuft — danach Auto-Modus | `2` |
| Netz-Einspeiselimit (`grid_feed_limit`) | Einspeiseleistungsgrenze gem. §14a EnWG oder Netzbetreibervorgabe (W) | `7200` |
| Toleranz (`tolerance`) | Abstand unter dem Einspeiselimit, ab dem die Ladeleistung erhöht wird — sollte der Schrittweite entsprechen (W) | `350` |
| Regelschrittweite (`step_w`) | Leistungsänderung je Regelzyklus beim Hoch- oder Runterregeln (W) | `500` |
| Mindest-Tagesertrag (`forecast_limit`) | Prognostizierter Tagesertrag muss diesen Wert überschreiten — sonst bleibt die Automation inaktiv (schlechtes Wetter) (kWh) | `40` |
| Mindest-Peak-Leistung (`peak_power_limit`) | Prognostizierte Peak-Stundenenergie muss diesen Wert überschreiten — sonst bleibt die Automation inaktiv (kWh) | `7.5` |
| Skalierungsfaktor (`read_scale_factor`) | Korrekturfaktor für die Rücklesung der aktuellen Ladeleistung vom BMS — normalerweise 1 | `1` |

---

## Regellogik

Alle 5 Minuten (oder bei Änderung des Peak-Sensors) wertet die Automation die aktuelle Netzleistung aus:

- **Netzbezug (> +100 W):** Ladeleistung um einen Schritt reduzieren → kein Laden aus dem Netz
- **Einspeisung unter Limit:** Ladeleistung um einen Schritt erhöhen, gedeckelt durch `required_w`
- **Einspeisung am oder über Limit:** Ladeleistung um einen Schritt erhöhen, gedeckelt durch `required_w`

Die Automation schaltet in den Ruhemodus wenn:
- Außerhalb des aktiven Zeitfensters (definiert durch Vorlaufzeit vor Peak und Nachlaufzeit nach Peak: `pre_peak_hours`, `post_peak_hours`)
- Ladestand hat das konfigurierte Maximum erreicht (`soc_max`)
- E-Auto ist angesteckt (`ev_connected_sensor_1/2`)
- Prognostizierter Tagesertrag liegt unter dem Mindest-Schwellwert für Aktivierung (`forecast_limit`)
- Prognostizierte Peak-Stundenenergie liegt unter dem Mindest-Schwellwert für Aktivierung (`peak_power_limit`)

---

## Mein Setup

Getestet mit:
- Fronius Symo Gen24 Plus 12.0 SC mit BYD Battery Box Premium HVS 20.38 kWh
- [`fronius_modbus`](https://github.com/callifo/fronius_modbus) von [@callifo](https://github.com/callifo) (HACS) — der aktiv gepflegte Fork, den ich empfehle
- Open-Meteo Solar Forecast (HACS)
- Shelly Pro 3EM als Stromzähler
- evcc mit Wattpilot und NRGKick
<img width="780" height="1959" alt="Screenshot 2026-04-12 at 20-39-18 Automationen – Home Assistant" src="https://github.com/user-attachments/assets/e80d2e24-d311-4001-b75e-190dda559285" />

---

## Hinweise

- Die Automation läuft im `single`-Modus — überlappende Ausführungen werden verworfen, nicht in die Warteschlange gestellt.
- evcc setzt das Ladelimit beim Anstecken eines E-Autos bei mir automatisch auf 80% des Autoakkus zurück — eine separate Reset-Automation ist nicht nötig.
- Das `wh_period`-Attribut des Open-Meteo Forecast Sensors wird für die Post-Peak-Ertragskalkulation genutzt. Ist es nicht verfügbar, dient der `remaining`-Sensor als Fallback.

---

## Danksagung

Herzlichen Dank an [@callifo](https://github.com/callifo) für die Pflege von [`fronius_modbus`](https://github.com/callifo/fronius_modbus) — der aktiv gewarteten Home Assistant Integration für Fronius-Wechselrichter mit Modbus BMS-Steuerung. Ohne diese Integration wäre dieser Blueprint nicht möglich.

---

## Lizenz

MIT License — frei verwendbar, anpassbar und weitergabe erlaubt.
