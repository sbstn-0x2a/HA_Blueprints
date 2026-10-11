# 🚿 Fröling Brauchwasser-Steuerung

Ein Home-Assistant-Blueprint für die Brauchwasserbereitung an einem **Fröling-Pelletkessel**. Geladen wird nachts, zur kältesten Stunde der Vorhersage, und nur wenn das Wasser tatsächlich knapp wird — dazu eine zweite Automation, die festhält, ob wirklich geladen wurde.

🇬🇧 [English version](/Automations/froeling_dhw_extra_charge/README.md)

[![Blueprint in Home Assistant importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/sbstn-0x2a/HA_Blueprints/blob/main/Automations/froeling_dhw_extra_charge/froeling_dhw_extra_charge.yaml)

---

## Was macht die Automation?

Statt nachzuheizen, sobald der Speicher unter eine Schwelle fällt, sagt diese Automation vorher, wann das Wasser zu kalt wird — und lädt einmal, zum besten Zeitpunkt der Nacht.

**Komfort-orientierte Nachtladung**
Alle 10 Minuten rechnet das Blueprint die Speichertemperatur mit dem newtonschen Abkühlgesetz voraus: `T(t) = T_Raum + (T0 − T_Raum)·e^(−k·t)`. Fällt die Vorhersage für den nächsten **Morgen** oder den nächsten **Abend** unter die Mindesttemperatur, wird eine Ladung geplant.

**Zeitpunkt nach Wettervorhersage**
Die Ladung wird auf den **kältesten Stundenwert** der Nacht gelegt (geringstes Kondensatrisiko im Schornstein), aber so früh, dass sie `charge_duration_hours` vor der Morgenzeit fertig ist. Die Außentemperatur entscheidet also *wann*, niemals *ob* — sie ist Timing-Optimierer, kein Lade-Gate.

**Ereignisbetrieb bei Kälte**
Unter einer Außentemperatur-Schwelle (`event_mode_threshold`, Standard 15 °C Tagesmittel) bekommt jede Engstelle ihre eigene Ladung. Ein Engpass am Morgen wird weiterhin nachts geladen; ein Engpass nur am Abend wird am Nachmittag geladen (`evening_ready_time − charge_duration_hours`) statt schon in der Nacht davor. Über der Schwelle deckt eine Nachtladung Morgen und Abend ab. Das Tagesmittel stammt aus den nächsten 24 h der Wettervorhersage, mit optionalem Rückfall-Sensor.

**Notfall-Boden**
Unter `min_temperature − 3 °C` wird jederzeit geladen, auch tagsüber. Das ist ein Sicherheitsnetz und sollte selten zünden.

**Harte Sperre über den Anlagenzustand**
Steht die Anlage nicht in einem der erlaubten Zustände, wird überhaupt kein Befehl geschickt — der Notfall-Boden eingeschlossen.

**Quittierte Befehle**
Ein Befehl zählt erst, wenn der Kessel reagiert: Entweder verlässt der Kesselzustand den Ruhezustand, oder die Wassertemperatur steigt über den Wert, der beim Absetzen gemerkt wurde. Bis dahin wird der Befehl bei jedem Lauf innerhalb von `command_retry_window` (Standard 30 min) wiederholt. Bleibt auch der letzte Versuch unquittiert, schreibt das Blueprint einen Logbucheintrag, schickt optional eine Push-Meldung und verkürzt die Sperrzeit auf eine weitere Stunde, damit der nächste reguläre Anlass (z. B. der Notfall-Boden) bald wieder greift.

**Ansteuerung über Cloud oder Modbus**
`control_mode: cloud` löst die Extraladung über eine Entität der Fröling-Cloud-Integration aus. `control_mode: modbus` nutzt stattdessen die Kesselfernsteuerung der [Fröling-S3200-Modbus-Integration](https://github.com/sbstn-0x2a/ha_froeling_modbus): Für die Dauer der Ladung hebt sie den Boiler-Sollwert an und verengt das Nachladefenster, danach stellt sie die ursprünglichen Werte wieder her.

---

## Der Kern: ein Befehl ist keine Ladung

Ein Blueprint kann nur einen Befehl *absetzen*. Ob der Kessel das Wasser tatsächlich erwärmt, ist eine andere Frage — und die beiden fallen häufiger auseinander, als man denkt:

- Der Brenner startet und geht auf **Störung** — der Speicher gewinnt 5 °C statt 25 °C.
- Der Kessel **läuft Stunden später von selbst wieder an**, um eine unvollendete Extraladung zu beenden — ohne jeden Befehl.
- Der Speicher wird als **Nebeneffekt** einer Puffer- oder Heizladung mitgeheizt — ebenfalls ohne Befehl.
- Jemand löst die Extraladung **von Hand** aus, am Kesseldisplay oder in HA.

Frühere Fassungen schrieben „letzte Ladung = jetzt" in dem Moment, in dem der Befehl rausging. Das Dashboard meldete dann Erfolg, während der Speicher bei 46 °C stand, und die 6-Stunden-Sperrzeit lief gegen eine Ladung, die nie stattgefunden hatte.

Deshalb gibt es **zwei getrennte Zeitstempel**:

| Helfer | Wer schreibt | Bedeutung |
|---|---|---|
| `input_datetime.letzter_brauchwasser_befehl` | das Blueprint | wann ein Befehl abgesetzt wurde — steuert nur die Sperrzeit |
| `input_datetime.letzte_brauchwasser_ladung` | die Erfassungs-Automation | wann das Wasser tatsächlich wärmer wurde, egal woher |

Seit v0.11 geht das Blueprint noch einen Schritt weiter und prüft, ob ein Befehl überhaupt *angekommen* ist. In der Praxis kann die Integration einen Befehl ohne jeden Fehler annehmen, und er erreicht den Kessel trotzdem nie. Ohne Quittierung liefe die 6-Stunden-Sperrzeit dann gegen einen verlorenen Befehl — der Notfall-Boden eingeschlossen. Die Sperrzeit beginnt deshalb erst mit der Quittierung (siehe *Quittierte Befehle* oben). Die dafür nötigen Werte stehen in `input_text.brauchwasser_befehl_basis`.

---

## Zwei Bestandteile

| Datei | Zweck |
|---|---|
| `froeling_dhw_extra_charge.yaml` | das Blueprint — entscheidet *ob* und *wann* ein Ladebefehl rausgeht |
| `package_brauchwasser.yaml` | Helfer + die Automation `Brauchwasser – Ladung erfassen`, die echte Ladungen erkennt und ihre Quelle benennt |

**Beides wird gebraucht.** Das Blueprint schreibt in drei Helfer, die im Package definiert sind — allein läuft es nicht.

---

## Voraussetzungen

- **Kessel:** Fröling-Pelletkessel mit einer HA-Integration, die folgendes bereitstellt:
  - einen Temperatursensor für den Speicher oben
  - eine Entität, die die Extraladung auslöst (`button`, `switch`, `water_heater` oder `select`) — für `control_mode: cloud`
  - oder die Fernsteuerungs-Entitäten der [Fröling-S3200-Modbus-Integration](https://github.com/sbstn-0x2a/ha_froeling_modbus) (ab 0.6.0) — für `control_mode: modbus`
  - einen Kesselzustands-Sensor (für die Erkennung von Brennerstarts und die Quittierung von Befehlen)
  - einen Anlagenzustands-Sensor (für die Sperre)
- **Umgebungssensor:** ein Temperaturfühler im Heizungsraum — wird ausschließlich für das Abkühlmodell benutzt
- **Wetter (optional):** eine `weather`-Entität mit stündlicher Vorhersage über `weather.get_forecasts` (z. B. DWD). Leer lassen heißt: Ladung zum spätestmöglichen Zeitpunkt.
- **Außenmittel (optional):** Rückfall für den Ereignisbetrieb, falls die Vorhersage fehlt, z. B. ein Statistik-Helfer (Mittelwert, maximales Alter 24 h) auf dem Außenfühler.
- **Benachrichtigung (optional):** ein `notify`-Dienst für die Meldung „Befehl nicht quittiert“.
- **Packages aktiviert** in der `configuration.yaml`:
  ```yaml
  homeassistant:
    packages: !include_dir_named packages
  ```

---

## Inbetriebnahme

1. **Blueprint importieren** über den Badge oben, oder `froeling_dhw_extra_charge.yaml` nach `config/blueprints/automation/froeling/` kopieren.

2. **`package_brauchwasser.yaml`** nach `config/packages/` kopieren.

3. **Entity-IDs im Package anpassen.** Die Erfassungs-Automation spricht vier Entitäten direkt an — sie sind keine Blueprint-Eingaben:

   | Platzhalter in der Datei | Was dort hingehört | Vorkommen |
   |---|---|---|
   | `sensor.boiler_1_temperatur_oben` | dein Speicherfühler oben | 4 |
   | `select.12345_boiler_01_mode` | deine Extraladen-Entität | 2 |
   | `sensor.12345_kessel_state` | dein Kesselzustands-Sensor | 1 |
   | `sensor.anlagenzustand` | dein Anlagenzustands-Sensor | 1 |

   Prüfe außerdem die beiden Zustandsnamen: `"Vorbereitung"` (der Kesselzustand, der einen Brennerstart markiert) und `"Extraladen"` (die Option der Extraladung). Beide hängen von der Sprache deiner Integration ab.

   Das Blueprint selbst schreibt in `input_datetime.letzter_brauchwasser_befehl`, `input_text.brauchwasser_befehl_basis` und `input_text.brauchwasser_startquelle` — alle drei sind im Package definiert.

4. **Auf Helfer-Kollision achten.** Das Package definiert `input_datetime.letzte_brauchwasser_ladung` und `input_text.grund_brauchwasser_ladung`. Wenn du die beiden schon als UI-Helfer hast, lösche sie dort oder kommentiere die Einträge aus — sonst kollidieren die Entity-IDs. Ein Kommentarblock in der Datei markiert die Stelle.

5. **Home Assistant neu starten.** Ein YAML-Reload genügt nicht, weil das Package neue Helfer-Entitäten anlegt.

6. **Automation aus dem Blueprint anlegen** und die Eingaben ausfüllen (siehe unten). `plant_state_sensor` auf deinen Anlagenzustand setzen — ohne ihn ist die Sperre wirkungslos.

7. **Prüfen.** Nach dem nächsten 10-Minuten-Lauf sollte in `input_text.brauchwasser_warte_grund` ein Klartext stehen, etwa `🌙 Nachtladung geplant 13.09 02:00`. Bleibt das Feld leer, läuft die Automation nicht.

---

## Konfiguration

| Eingabe | Beschreibung | Standard |
|---|---|---|
| `water_temperature_sensor` | Speichertemperatur oben | — |
| `outdoor_temperature_sensor` | Umgebungstemperatur am Speicher — nur Abkühlmodell, nie ein Gate | — |
| `weather_forecast_entity` | Wetter-Entität mit stündlicher Vorhersage; leer = Ladung zum spätestmöglichen Zeitpunkt | *(keine)* |
| `outdoor_mean_sensor` | Rückfall für das Außen-Tagesmittel, falls die Vorhersage fehlt | *(keiner)* |
| `event_mode_threshold` | Unter diesem Tagesmittel bekommt jede Engstelle ihre eigene Ladung (°C) | `15` |
| `control_mode` | `cloud` (Extraladen-Entität) oder `modbus` (Kesselfernsteuerung) | `cloud` |
| `extra_charge_service` | Entität, die die Extraladung auslöst — nur `cloud` | *(keine)* |
| `extra_charge_select_option` | Zu wählende Option, wenn die Entität ein `select` ist | `Extraladen` |
| `modbus_control_select` | Select „Regelung“ der Fernsteuerung — nur `modbus` | *(keiner)* |
| `modbus_control_option` / `modbus_end_option` | Option während / nach der Ladung | `home_assistant` / `kessel` |
| `modbus_setpoint_entity` | Boiler-Solltemperatur der Fernsteuerung (Register 48019) | *(keine)* |
| `modbus_target` | Boiler-Soll für die Ladung; die Anlage stoppt genau hier, max. 65 (°C) | `65` |
| `modbus_desired_entity` / `modbus_reload_entity` | Anlagenwerte „Gewünschte Boilertemperatur“ (41632) und „Nachladen, wenn unter“ (41633) | *(keine)* |
| `modbus_charge_desired` / `modbus_charge_reload` | Werte während der Ladung (°C) | `50` / `45` |
| `modbus_restore_desired` / `modbus_restore_reload` | Werte nach der Ladung (°C) | `65` / `35` |
| `modbus_max_minutes` | Spätestens nach so vielen Minuten geht die Regelung zurück an die Anlage | `180` |
| `min_temperature` | Mindesttemperatur zu den Zielzeiten (°C) | `45` |
| `morning_ready_time` | Wann das Wasser morgens warm sein muss | `05:00` |
| `evening_ready_time` | Wann das Wasser abends warm sein muss | `18:00` |
| `night_charge_earliest` | Frühester Beginn des Nacht-Ladefensters | `22:00` |
| `charge_duration_hours` | Dauer einer vollen Ladung — bestimmt den spätesten Start (h) | `2.5` |
| `min_charge_interval` | Sperrzeit zwischen zwei Befehlen (min) | `360` |
| `prediction_activation_threshold` | Vorhersage wird erst unter dieser Speichertemperatur aktiv (°C) | `52` |
| `heat_loss_coefficient` | Abkühlrate `k` im Newton-Modell (1/h) | `0.011` |
| `boiler_state_sensor` | Kesselzustand für die Quittierung; leer = Quittierung nur über die Wassertemperatur | *(keiner)* |
| `boiler_idle_state` | Kommaliste der Zustände „Kessel tut nichts“ | `Betriebsbereit, Tür offen` |
| `command_retry_window` | So lange wird ein unquittierter Befehl wiederholt (min) | `30` |
| `notify_service` | `notify`-Dienst für die Meldung „nicht quittiert“, z. B. `notify.mobile_app_handy` | *(keiner)* |
| `plant_state_sensor` | Anlagenzustands-Entität; leer schaltet die Sperre ab | *(keine)* |
| `plant_state_allowed` | Kommaliste der Zustände, in denen geladen werden darf | `Brauchwasser` |
| `status_sensor` | `input_text` für den Status-Einzeiler | *(keiner)* |
| `next_charge_sensor` | `input_datetime` für den nächsten Ladezeitpunkt | *(keiner)* |
| `reason_sensor` | `input_text` für den Klartext-Grund | *(keiner)* |

### Den eigenen Wärmeverlust-Koeffizienten bestimmen

`k` beschreibt, wie schnell dein Speicher auskühlt. Zwei Temperaturen im Abstand einiger Stunden ohne Entnahme nehmen, dann

```
k = ln((T0 − T_Raum) / (T1 − T_Raum)) / Stunden
```

`0,011 1/h` entspricht etwa 0,59 °C/h bei 54 K Differenz. Größerer Wert = schlechter isoliert.

---

## Wie eine Ladung erkannt wird

Die Erfassung glaubt keinem Befehl — sie schaut auf die Temperatur.

- **Beginn:** Der Speicher steigt **4 K über den mitgeführten Tiefpunkt**. Der Tiefpunkt folgt der Temperatur beim Abkühlen nach unten und während der Ladung nach oben. Die 4 K sind Absicht: 1–2 K Fühlerrauschen dürfen nicht zählen.
- **Ende:** **30 Minuten ohne Änderung** des Messwerts. Während einer Ladung ändert er sich alle 1–3 Minuten, beim Abkühlen nur alle paar Stunden.
- **Ergebnis:** In `grund_brauchwasser_ladung` steht am Ende z. B. `Automation · 41→66 °C`. Eine fehlgeschlagene Ladung ist an `41→46 °C` sofort erkennbar.

### Woher die Quellenangabe kommt

Die Quelle wird pro **Brennerstart** bestimmt (Kesselzustand → `Vorbereitung`), nicht pro Ladung:

| Bedingung | Quelle |
|---|---|
| Start ≤ 5 min nach einem Befehl | `Automation` |
| später, Auftrag noch offen | `Kessel-Wiederanlauf` |
| Extraladen aktiv, kein Befehl | `Extraladung von Hand` |
| Anlagenzustand = erlaubter Zustand | `Kessel-/Pufferladung` |
| Anlagenzustand = Heizbetrieb | `Heizbetrieb` |
| sonst | `Fremdstart` |

Das 5-Minuten-Fenster ist großzügig: Über 8 Ladungen gemessen lag der Verzug zwischen Befehl und Brennerstart bei 82–127 Sekunden. Ein späterer Start kann ohnehin nicht die Automation gewesen sein — die Sperrzeit verhindert das.

---

## Hinweise

- Läuft alle 10 Minuten, `mode: single`, `max_exceeded: silent`.
- **Winterbetrieb:** Wenn deine Anlage für die kalte Jahreszeit auf einen Heizmodus umgestellt wird, legt `plant_state_allowed: Brauchwasser` die Automation vollständig still. Dann den Heizzustand mit aufnehmen, z. B. `Brauchwasser, Automatik`.
- Der Status-Einzeiler ist durch `input_text` auf 255 Zeichen begrenzt.
- Brennerstarts und ihre Quelle wertet nur die Package-Automation aus. Das Blueprint liest den Kesselzustand ausschließlich, um die eigenen Befehle zu quittieren.
- **Modbus-Betrieb:** Die Kesselfernsteuerung wirkt auf alle Heizkreise zugleich. Im Anlagenzustand `Brauchwasser` ist das neutral; wer zusätzlich `Automatik` freigibt, gibt die Heizkreisregelung für die Dauer der Ladung an Home Assistant ab.
- Nach einer Änderung an der Blueprint-Datei `homeassistant.reload_all` ausführen — ein Reload der Automationen leert den Blueprint-Cache nicht.

---

## Lizenz

MIT-Lizenz — nutzen, anpassen und weitergeben ausdrücklich erwünscht.
