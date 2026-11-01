# 🔥 Rename "Gas" on the Home Assistant Energy Dashboard

The energy dashboard has a fixed section for gas. If you use it for something else, such as wood and pellets, it still says "Gas" everywhere. Home Assistant has no setting for this and no way to override its translations.

This small frontend module replaces selected texts while the browser loads the language files. The standard energy dashboard stays in place, no custom dashboard is needed. In this example, German "Gas" becomes "Wärme" and "Gasverbrauch" becomes "Wärmeverbrauch".

🇩🇪 [Deutsche Version](/Frontend/energy_dashboard_wording/README.de.md)

---

## What changes

| Where | Before | After |
|---|---|---|
| Dashboard tab | Gas | Wärme |
| Dashboard graph title | Gasverbrauch | Wärmeverbrauch |
| Energy distribution card | Gas | Wärme |
| Sources table, total row | Gas gesamt | Wärme gesamt |
| Settings tab | Gas | Wärme |
| Settings heading and label | Gasverbrauch | Wärmeverbrauch |
| Settings subtitle | Lass Home Assistant deinen Gasverbrauch überwachen. | Lass Home Assistant deinen Wärmeverbrauch überwachen. |

Still unchanged are the buttons and the source dialog in the settings (such as "Gaszähler hinzufügen") and the card editor. They are easy to add to the list if they bother you.

## Installation

1. Copy `energy_dashboard_wording.js` to `/config/www/`.
2. Add it to `configuration.yaml`:

   ```yaml
   frontend:
     extra_module_url:
       - /local/energy_dashboard_wording.js
   ```

3. Restart Home Assistant.
4. **Clear the browser cache.** A normal reload was not enough here. The companion app may also need to be restarted.

## Using your own words

Edit `WORDS` in the script, and set `LANGUAGE` if your interface is not German. The script only changes files of this one language.

To find a key, open the browser developer tools, filter the network tab for `translations` and open the energy page. The frontend loads files such as:

```
/static/translations/energy/de-<hash>.json
/static/translations/lovelace/de-<hash>.json
/static/translations/config/de-<hash>.json
```

Each one is a flat list of `key: text` entries.

Replace specific keys only, not every occurrence of the word. For example, `ui.dialogs.entity_registry.editor.device_classes.binary_sensor.gas` is the device class for real gas detectors.

## Good to know

- **Scope:** It applies to all devices and users whose interface is set to that language.
- **Updates:** The file lives in `/config/www` and survives updates. If a later release renames a key, that text falls back to the original wording. Nothing breaks, you just need to update the key.
- **Timing:** The module loads alongside the frontend. If it ever arrived too late, the original word would show until the next page load. This has not been observed here so far.
- **Single sources:** The names of individual sources in the graph are a separate matter. Home Assistant added [a display name for gas and water sources](https://github.com/home-assistant/frontend/pull/52011) in 2026. This module does not touch them.

## Tested with

Home Assistant 2026.10.4, in the browser including mobile view.

## Removal

Remove the `extra_module_url` entry and the file, restart Home Assistant and clear the browser cache.
