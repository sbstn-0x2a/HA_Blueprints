// Replaces selected texts of the Home Assistant frontend while its language files load.
// Used here to show "Wärme" instead of "Gas" on the energy dashboard, because wood and
// pellets are tracked as gas sources.
//
// Load it through frontend: extra_module_url in configuration.yaml.
// If a key no longer exists or anything fails, the original text stays in place.

const LANGUAGE = "de";

const WORDS = {
  // Energy dashboard
  "ui.panel.energy.title.gas": "Wärme",
  "ui.panel.energy.cards.energy_gas_graph_title": "Wärmeverbrauch",
  "ui.panel.lovelace.cards.energy.energy_distribution.gas": "Wärme",
  "ui.panel.lovelace.cards.energy.energy_sources_table.gas_total": "Wärme gesamt",

  // Settings > Dashboards > Energy
  "ui.panel.config.energy.tabs.gas": "Wärme",
  "ui.panel.config.energy.gas.title": "Wärmeverbrauch",
  "ui.panel.config.energy.gas.sub": "Lass Home Assistant deinen Wärmeverbrauch überwachen.",
  "ui.panel.config.energy.gas.gas_consumption": "Wärmeverbrauch",
};

const LANGUAGE_FILE = new RegExp(
  `/static/translations/(?:[^/]+/)?${LANGUAGE}-[0-9a-f]+\\.json`
);
const originalFetch = window.fetch;

window.fetch = async function (...args) {
  const response = await originalFetch.apply(this, args);
  try {
    const url = typeof args[0] === "string" ? args[0] : args[0]?.url ?? String(args[0]);
    if (!response.ok || !LANGUAGE_FILE.test(url)) return response;

    const texts = await response.clone().json();
    let changed = false;
    for (const [key, word] of Object.entries(WORDS)) {
      if (key in texts) {
        texts[key] = word;
        changed = true;
      }
    }
    if (!changed) return response;

    return new Response(JSON.stringify(texts), {
      status: response.status,
      statusText: response.statusText,
      headers: { "content-type": "application/json" },
    });
  } catch (error) {
    console.warn("energy_dashboard_wording: keeping the original text", error);
    return response;
  }
};
