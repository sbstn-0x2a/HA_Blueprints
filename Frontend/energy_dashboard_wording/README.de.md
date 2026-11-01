# 🔥 „Gas“ im Home-Assistant-Energie-Dashboard umbenennen

Das Energie-Dashboard hat eine feste Rubrik für Gas. Wer sie für etwas anderes nutzt, zum Beispiel für Holz und Pellets, liest trotzdem überall „Gas“. Home Assistant hat dafür keine Einstellung und bietet auch keine Möglichkeit, Übersetzungen zu überschreiben.

Dieses kleine Frontend-Modul ersetzt ausgewählte Texte, während der Browser die Sprachdateien lädt. Das Standard-Energie-Dashboard bleibt erhalten, ein eigenes Dashboard ist nicht nötig. Im Beispiel wird aus „Gas“ „Wärme“ und aus „Gasverbrauch“ „Wärmeverbrauch“.

🇬🇧 [English version](/Frontend/energy_dashboard_wording/README.md)

---

## Was sich ändert

| Ort | Vorher | Nachher |
|---|---|---|
| Dashboard, Tab | Gas | Wärme |
| Dashboard, Diagrammtitel | Gasverbrauch | Wärmeverbrauch |
| Karte Energieverteilung | Gas | Wärme |
| Quellentabelle, Summenzeile | Gas gesamt | Wärme gesamt |
| Einstellungen, Tab | Gas | Wärme |
| Einstellungen, Überschrift und Bezeichnung | Gasverbrauch | Wärmeverbrauch |
| Einstellungen, Untertitel | Lass Home Assistant deinen Gasverbrauch überwachen. | Lass Home Assistant deinen Wärmeverbrauch überwachen. |

Unverändert bleiben die Knöpfe und der Quellen-Dialog in den Einstellungen (etwa „Gaszähler hinzufügen“) sowie der Karteneditor. Wen das stört, ergänzt sie einfach in der Liste.

## Installation

1. `energy_dashboard_wording.js` nach `/config/www/` kopieren.
2. In der `configuration.yaml` eintragen:

   ```yaml
   frontend:
     extra_module_url:
       - /local/energy_dashboard_wording.js
   ```

3. Home Assistant neu starten.
4. **Browser-Cache leeren.** Normales Neuladen hat hier nicht gereicht. Die Companion-App muss eventuell ebenfalls neu gestartet werden.

## Eigene Wörter verwenden

Passe `WORDS` im Skript an, und setze `LANGUAGE`, falls deine Oberfläche nicht auf Deutsch steht. Das Skript ändert nur die Dateien dieser einen Sprache.

Einen Schlüssel findest du über die Entwicklertools des Browsers: Netzwerk-Tab nach `translations` filtern und die Energieseite öffnen. Das Frontend lädt dann Dateien wie diese:

```
/static/translations/energy/de-<hash>.json
/static/translations/lovelace/de-<hash>.json
/static/translations/config/de-<hash>.json
```

Jede davon ist eine flache Liste aus `Schlüssel: Text`.

Ersetze nur gezielte Schlüssel, nicht jedes Vorkommen des Wortes. `ui.dialogs.entity_registry.editor.device_classes.binary_sensor.gas` ist zum Beispiel die Geräteklasse für echte Gasmelder.

## Gut zu wissen

- **Geltung:** Es wirkt auf allen Geräten und für alle Benutzer, deren Oberfläche auf diese Sprache eingestellt ist.
- **Updates:** Die Datei liegt in `/config/www` und übersteht Updates. Benennt ein späteres Release einen Schlüssel um, steht dort wieder der Originaltext. Kaputt geht nichts, nur der Schlüssel muss nachgezogen werden.
- **Timing:** Das Modul lädt parallel zum Frontend. Käme es einmal zu spät, stünde bis zum nächsten Seitenaufruf das ursprüngliche Wort da. Beobachtet wurde das hier bisher nicht.
- **Einzelne Quellen:** Die Namen der einzelnen Quellen im Diagramm sind ein eigenes Thema. Home Assistant hat 2026 [einen Anzeigenamen für Gas- und Wasserquellen](https://github.com/home-assistant/frontend/pull/52011) ergänzt. Dieses Modul ändert daran nichts.

## Getestet mit

Home Assistant 2026.10.4, im Browser einschließlich Mobilansicht.

## Entfernen

Eintrag `extra_module_url` und die Datei entfernen, Home Assistant neu starten und den Browser-Cache leeren.
