# 💧 Comfee CDDKE-16DEN7 (EU) Luftentfeuchter in Home Assistant

Ein Comfee-Luftentfeuchter **CDDKE-16DEN7 (EU)** (Midea-Gerätetyp `0xA1`), vollständig lokal in Home Assistant eingebunden. Die Grundsteuerung übernimmt die HACS-Integration **Midea AC LAN**. Dazu kommen die richtige Zuordnung von Modi und Lüfterstufen, eine kleine Erweiterung für den **Gerätetimer (1–24 h)**, den Midea AC LAN nicht kennt, und eine Bubble-Card fürs Dashboard.

🇬🇧 [English version](/Integrations/comfee_dehumidifier/README.md)

---

## Bestandteile

| Teil | Datei / Quelle | Wozu |
|---|---|---|
| Integration | HACS **[Midea AC LAN](https://github.com/wuwentao/midea_ac_lan)** (`midea_ac_lan`) | Ein/Aus, Soll-Feuchte, Modus, Ist-Feuchte |
| Optionen | „Customize“ + Switch `Fan Speed` im Config-Entry | richtige Modi und Lüfterstufen |
| Erweiterung | `custom_components/midea_a1_timer/` | Timer lesen und setzen |
| Konfiguration | `package_comfee_entfeuchter.yaml` | lädt die Erweiterung |
| Karte | `dashboard_card.yaml` | Bedienung im Dashboard (Bubble Card) |

Entstehende Entities (`<id>` = Device-ID des Geräts in Midea AC LAN):

| Entity | Herkunft |
|---|---|
| `humidifier.<id>_humidifier` | Midea AC LAN (Ein/Aus, Soll, Modus, Ist-Feuchte als Attribut) |
| `select.<id>_fan_speed` | Midea AC LAN, nach Schritt 3 |
| `select.comfee_luftentfeuchter_timer` | midea_a1_timer (`Aus`, `1 h` … `24 h`) |
| `sensor.comfee_luftentfeuchter_timer_restzeit` | midea_a1_timer (Minuten, Attribut `ende` = HH:MM) |

Getestetes Gerät: Comfee **CDDKE-16DEN7 (EU)**, Typ `0xA1`, Modell `00000Q1A`, Subtype `41377`, Protokoll V3.

---

## 1. Gerät ins WLAN

1. Das Gerät mit der Hersteller-App (MSmartHome) ins WLAN einbinden (nur 2,4 GHz).
2. Am Router eine **feste IP** reservieren.
3. Prüfen, ob das Gerät erreichbar ist: `nc -z -w1 <ip> 6444`.

---

## 2. Midea AC LAN einrichten

1. HACS → **Midea AC LAN** installieren, HA neu starten.
2. *Einstellungen → Geräte & Dienste → Integration hinzufügen → Midea AC LAN*.
3. **Mit gesicherten Werten (bevorzugt):** „Configure manually“ und Device-ID, Typ `161`, IP, Port `6444`, Modell, Subtype, Protokoll `3`, Token und Key eintragen.
4. **Ohne gesicherte Werte:** „Discover automatically“ und die **IP des Geräts** eintragen. „auto“ funktioniert nicht, wenn das Gerät in einem anderen VLAN/Subnetz hängt, weil der Broadcast dort nicht ankommt. Im Login-Schritt „Skip Login (input any user/password)“ wählen, sonst das MSmartHome-Konto.
5. **Token und Key sofort sichern** (außerhalb von Git!). Midea schaltet die Token-Abfrage über die Cloud nach und nach ab. Ohne gesicherte Werte lässt sich das Gerät dann womöglich nicht mehr neu einbinden. Die Werte stehen auch in `/config/.storage/midea_ac_lan/<id>.json`.

---

## 3. Optionen: Modi und Lüfterstufen

Die Standardliste der Integration passt nicht zu diesem Gerät. Ohne Anpassung zeigt HA `mode: null` und bietet Modi an, die das Gerät nicht kennt (`manual`, `continuous`, `shoes_dry`). Die echten Codes wurden per Mitschnitt ermittelt (Modus-Taste am Gerät: auto → silent → dryer):

| Code | Modus | Lüfter |
|---|---|---|
| 11 | auto | wählbar |
| 10 | silent | fest low |
| 4 | dryer | fest high |

Lüfter-Codes: 40 low, 60 medium, 80 high.

*Midea AC LAN → Gerät → Konfigurieren:*

- **Switches:** `Fan Speed` anhaken. Das ergibt `select.<id>_fan_speed`.
- **Customize:**
  ```json
  {"modes":{"11":"auto","10":"silent","4":"dryer"},"speeds":{"40":"low","60":"medium","80":"high"}}
  ```
- Abfrage-Intervall: 30 s (Standard).

**Codes bei einem anderen Gerät ermitteln:** mit `logger.set_level` die Stufe `midealan: debug` setzen, am Gerät alle Modi und Stufen durchschalten (je ca. 40 s stehen lassen, wegen des 30-s-Intervalls) und im Log die Zeilen mit `Received:` auswerten (`'mode': …, 'fan_speed': …`). Danach die Stufe zurück auf `info` setzen.

---

## 4. Timer-Erweiterung `midea_a1_timer`

Midea AC LAN bzw. die Bibliothek `midea-lan` werten die Timer-Bytes der A1-Statusmeldung nicht aus und können keinen Timer setzen. `midea_a1_timer` ist eine kleine Custom-Integration ohne eigenen Eintrag unter „Geräte & Dienste“:

- Sie wird per YAML geladen und hängt sich an das Geräteobjekt von Midea AC LAN (`hass.data["midea_ac_lan"]["devices"]`).
- Sie liest die Timer-Bytes aus jeder Antwort des Geräts mit, also ohne zusätzliche Abfragen.
- Sie setzt den Timer per Rohbefehl (X48-Set).
- Midea AC LAN legt Geräteobjekte bei jedem Reload neu an. Die Erweiterung prüft deshalb alle 30 s und hängt sich bei Bedarf neu an.

Ein HACS-Update von Midea AC LAN lässt die Erweiterung unangetastet. Kaputtgehen kann sie nur, wenn `midea-lan` die Methoden `process_message`, `make_message_set` oder `build_send` umbaut. Dann steht im Log „Timer-Bytes nicht lesbar“, oder die Timer-Entities bleiben `unavailable`.

### Installation

1. Den Ordner `custom_components/midea_a1_timer/` nach `/config/custom_components/midea_a1_timer/` kopieren.
2. `package_comfee_entfeuchter.yaml` nach `/config/packages/` kopieren und `device_id` auf die eigene Device-ID setzen. Packages müssen in `configuration.yaml` aktiviert sein:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
3. Die Konfiguration prüfen und **HA neu starten**. Ein Reload reicht nicht, weil die Integration neu ist.
4. Spätestens 30 s nach dem Start steht im Log:
   `[custom_components.midea_a1_timer] [<id>] an midea_ac_lan-Gerät angehängt`.
   Die Entities sind verfügbar, sobald die erste Statusmeldung des Geräts eingetroffen ist.

Mehrere Geräte lassen sich als weitere Einträge unter `devices:` anlegen.

### Protokoll (Hintergrund)

- **Status** (Body-Typ `C8` für Abfragen, `A0` für Antworten auf Befehle): `body[4]` = Ein-Timer, `body[5]` = Aus-Timer, `body[6]` = Minuten-Nibble (oben Ein, unten Aus). `7f 7f 00` = kein Timer.
- **Restzeit** = h·60 + ((b & 3) + 1)·15 − Nibble, mit h = (b & 0x7C) >> 2 und Bit 7 = Timer aktiv.
  Gemessen: `84 0f` = 60 min, `83 01` = 59 min, `88 0f` = 120 min.
- **Setzen:** X48-Set mit **Bit 7 im Lüfter-Byte** (`body[3] | 0x80`). Ohne das Bit ignoriert das Gerät die Timer-Bytes. Volle Stunden h werden als (h − 1) Stunden + 60 min kodiert: 1 h = `0x83`, 2 h = `0x87`, 24 h = `0xDF`, Nibble 0. Alles `0x00` mit Bit 7 = Timer aus.
- Ist das Gerät an, wird der Aus-Timer gesetzt, sonst der Ein-Timer.
- Normale Befehle von Midea AC LAN (Timer-Bytes `00`, ohne Bit 7) lassen einen laufenden Timer stehen.
- Herkunft der Kodierung: [Chreece/ESPHome-Dehumidifier](https://github.com/Chreece/ESPHome-Dehumidifier) (Protokoll V1), am Comfee CDDKE-16DEN7 (Modell `00000Q1A`) verifiziert.

---

## 5. Dashboard-Karte

Voraussetzung: HACS-Frontend **[Bubble Card](https://github.com/Clooos/Bubble-Card)** (getestet mit 3.4.1). Den Inhalt von `dashboard_card.yaml` als Karte einfügen und `123456789012345` durch die eigene Device-ID ersetzen.

- `step: 5`: Das Gerät nimmt nur 5er-Schritte an und rundet auf den nächsten (73 → 75, 72 → 70, 68 → 70).
- `state_content: current_humidity` zeigt die Ist-Feuchte des Geräts (in 1-%-Schritten).
- Eine Gruppe „Steuerung“ enthält Modus, Lüfter und Timer als Auswahl.
- Die Restzeit erscheint nur, wenn ein Timer läuft (`visibility`).

---

## 6. Prüfliste

1. `humidifier.<id>_humidifier` zeigt bei `available_modes` nur `dryer, silent, auto` und hat einen Modus (nicht `null`).
2. Lüfter in HA umstellen: Das Gerät folgt.
3. Timer in HA auf 1 h stellen: Das Display zeigt 1 h, die Restzeit steht bei ca. 60 min. Danach den Timer am Gerät stellen: HA zeigt ihn nach spätestens 30 s an.
4. Timer auf „Aus“: Die Restzeit geht auf 0, und die Zeile „Rest“ verschwindet aus der Karte.

---

## Hinweise

- **Hysterese:** Das Gerät entscheidet offenbar nicht laufend über Kompressor an/aus. Beobachtet: Bei Ist 55 % und Soll 70 % lief der Kompressor weiter und ging erst 4 s nach einer Änderung am Soll aus. Es wartet also wohl eine Mindestlaufzeit ab oder reagiert erst auf eine Änderung der Einstellung. Eine genaue Messung mit einer eigenen Mess-Steckdose steht noch aus (Kompressor ≈ 150–200 W).
- Die Timer-Entities haben deutsche Namen und Optionen (`Aus`, `Restzeit`, Attribut `ende`). Wer sie umbenennt, muss die Karte anpassen.
- Token und Key gehören **nicht** ins Repository.

---

## Lizenz

MIT License – frei verwendbar, veränderbar und teilbar.
