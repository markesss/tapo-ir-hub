# Tapo IR Hub

Native Home Assistant integration for the **Tapo H1xx IR hub** (e.g. H110).
Talks to the hub locally over KLAP — no bridge, add-on or MQTT — and exposes:

- the **hub** as a device (with a **Rescan** button + diagnostic sensors),
- each **child IR remote** as its own device,
- each **mapped key** as a `button` entity that fires the stored IR code.

A background task re-queries the hub so new/renamed remotes appear
automatically. An optional custom **Lovelace card** (`lovelace/tapo-ir-card.js`)
renders each remote's keys as tappable buttons in a grid or handset layout.

After downloading, **restart Home Assistant**, then add the integration with
your hub's local IP and your Tapo account credentials.
