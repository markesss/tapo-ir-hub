# Tapo IR Hub for Home Assistant

[![hacs][hacs-badge]][hacs-url]
[![release][release-badge]][release-url]
[![license][license-badge]](LICENSE)

A **native Home Assistant integration** for the **Tapo H1xx IR hub** (e.g.
**H110**). It talks to the hub directly over its local KLAP API — no bridge, no
add-on, no MQTT — and turns every stored IR profile into proper Home Assistant
devices and entities. A matching custom **Lovelace card** renders each remote's
keys as tappable buttons.

> Why this exists: bridging the hub via Matter only exposes a few low-level
> switches and **hides the onboard IR remotes entirely**. This integration
> unlocks them — every child remote, with every mapped key, fully under your
> control. Everything is read live from your hub, so it works for **any** user,
> hub and set of remotes with no hardcoding.

---

## ⚡ Quick add to Home Assistant

**1. Add this repository to HACS** (opens your local Home Assistant):

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.][my-hacs-badge]][my-hacs-url]

> In HACS, after the repo opens: **Download**, then **restart Home Assistant**.
> (If the button can't find the repo automatically, in HACS choose
> **⋮ → Custom repositories**, paste
> `https://github.com/Loadst0ne/tapo-ir-hub`, category **Integration**.)

**2. Add the integration** (opens your local Home Assistant to the setup dialog):

[![Open your Home Assistant instance and start setting up a new integration.][my-config-badge]][my-config-url]

Enter your hub's **local IP** and your **Tapo account** email + password. The
integration validates the credentials, then creates the hub device, every child
remote device, and a button per key automatically.

---

## What you get

When set up, the integration models the hub exactly the way Home Assistant
expects:

- **The hub** becomes its own HA *device* (the system-wide controller). It
  carries a **Rescan devices** button and two diagnostic sensors
  (**Discovered devices**, **Last scan**).
- **Each child IR remote** becomes its own HA *device*, nested under the hub
  (`via_device`).
- **Each mapped key** becomes a `button` *entity* on that remote's device.
  Pressing it fires the stored IR code (`sendIrCmdById`).

### The async re-query task

A `DataUpdateCoordinator` re-queries the hub on an interval (default **300 s**,
min 30 s). Add or rename a remote in the Tapo app and the new remotes/buttons
appear on the next scan — or press the hub's **Rescan devices** button for an
immediate refresh. Adjust the interval (and optional name overrides) under the
integration's **Configure** dialog.

---

## 🎛️ The Lovelace card (optional but recommended)

A self-contained custom card that **auto-discovers** your hubs and draws each
remote as a panel of tappable buttons. Two layouts: a responsive **grid** and a
handset-style **remote** (D-pad cluster, volume/channel rockers, utility row).
Includes a visual (GUI) editor, collapsible panels, hub diagnostics chips and
include/exclude filters.

**Install the card:**

1. Copy `lovelace/tapo-ir-card.js` into your config's `www` folder
   → `/config/www/tapo-ir-card.js`.
2. Add it as a dashboard resource — or use the button below:

   [![Open your Home Assistant instance and show your dashboard resources.][my-resources-badge]][my-resources-url]

   - URL: `/local/tapo-ir-card.js`  •  Type: **JavaScript Module**
3. Hard-refresh the browser, then **Add card → "Tapo IR Card"**.

Minimal usage:

```yaml
type: custom:tapo-ir-card
```

Full card options and examples: [`lovelace/README.md`](lovelace/README.md).

---

## Requirements

- A **Tapo H1xx IR hub** reachable on your LAN by IP.
- Your **Tapo (TP-Link) account** credentials (used locally to open the hub's
  KLAP session; nothing leaves your network).
- Home Assistant **2023.4** or newer. The `plugp100` dependency installs
  automatically via HACS.

### Running alongside petretiandrea's "Tapo" integration

Both this integration and the popular
[petretiandrea **Tapo**](https://github.com/petretiandrea/home-assistant-tapo-p100)
integration use the same `plugp100` library. Home Assistant installs Python
dependencies into a single shared environment, so if two integrations pinned
*incompatible* `plugp100` versions they would repeatedly reinstall over each
other on every restart — which can leave one of them failing to load (it may
even show *"this integration doesn't support configuration via the UI"*).

To prevent that, this integration deliberately accepts a **range**
(`plugp100>=5.1.7,<7.0.0.dev0`) instead of an exact pin, so it happily reuses
whatever compatible `plugp100` the other integration already installed. The two
can coexist on the same Home Assistant without fighting.

## How it works (under the hood)

The hub speaks TP-Link's local **KLAP** protocol. This integration uses
[`plugp100`](https://github.com/petretiandrea/plugp100) inside Home Assistant's
event loop to:

1. `get_device_info` — identify the hub (id, model, firmware, MAC).
2. `get_child_device_list` — enumerate child IR remotes and their key maps
   (each key's `name` is the id fired by `sendIrCmdById`; the base64
   `display_name` is the human label).
3. `control_child(... sendIrCmdById ...)` — transmit a stored IR code.

Junk hub-supplied nicknames (raw key-id-shaped names) are humanized to
`IR Remote <id>`; you can override any name from the options dialog.

## Privacy / safety

- Credentials are stored only in your Home Assistant config entry and used
  locally against the hub. Never commit a real `tapo_secrets.json`.
- No telemetry, no cloud calls.

## License

[MIT](LICENSE) © Loadst0ne

---

<!-- badges -->
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[hacs-url]: https://hacs.xyz/
[release-badge]: https://img.shields.io/github/v/release/Loadst0ne/tapo-ir-hub?style=for-the-badge
[release-url]: https://github.com/Loadst0ne/tapo-ir-hub/releases
[license-badge]: https://img.shields.io/github/license/Loadst0ne/tapo-ir-hub?style=for-the-badge

<!-- my home assistant buttons -->
[my-hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[my-hacs-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=Loadst0ne&repository=tapo-ir-hub&category=integration
[my-config-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
[my-config-url]: https://my.home-assistant.io/redirect/config_flow_start/?domain=tapo_ir
[my-resources-badge]: https://my.home-assistant.io/badges/lovelace_resources.svg
[my-resources-url]: https://my.home-assistant.io/redirect/lovelace_resources/
