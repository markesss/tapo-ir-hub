# Tapo IR Hub (custom integration)

A native Home Assistant integration for the **Tapo H1xx IR hub** (e.g. H110). It
talks to the hub directly over its local KLAP API (via `plugp100`) from inside
Home Assistant's own event loop — no bridge, no add-on, no MQTT.

It models the hub the way HA expects:

- The **hub** appears as its own HA *device* (the system-wide controller). It
  carries a **Rescan devices** button and two diagnostic sensors
  (**Discovered devices**, **Last scan**).
- Each **child IR remote** stored on the hub becomes its own HA *device*, linked
  to the hub via `via_device` (so they nest under the hub).
- Each **mapped key** on a remote becomes a `button` *entity* on that remote's
  device. Pressing it fires the stored IR code (`sendIrCmdById`).

Everything is read live from the hub — the integration is not tied to any
specific remote, product, or account. Any user can enter their own Tapo
credentials and get all of their remotes and buttons.

## Install

1. Copy the `tapo_ir` folder into `/config/custom_components/` on your HA
   instance (so you have `/config/custom_components/tapo_ir/manifest.json`).
2. Restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and search for
   **Tapo IR Hub**.
4. Enter the hub's **local IP address** and your **Tapo account** email/password.

The integration validates the credentials by connecting and enumerating the
hub's remotes, then creates the hub device, all child remote devices, and a
button per key automatically.

## The async re-query task

A `DataUpdateCoordinator` re-queries the hub on an interval (default **300 s**,
minimum 30 s). When you add or rename a remote in the Tapo app, the new remotes
and buttons show up automatically on the next scan. You can also press the hub's
**Rescan devices** button to refresh immediately.

Adjust the interval in the integration's **Configure** (options) dialog.

## Name overrides

Some remotes store a junk nickname (the hub sometimes uses a raw key id as the
remote's name). The integration humanizes those to `IR Remote <id>`. To give a
remote a friendly name, open **Configure** and set **Name overrides** to a JSON
object mapping the child `device_id` to a name:

```json
{ "802DF9...0B0002": "Living Room AC" }
```

Find the `device_id` values in the hub's **Discovered devices** sensor
attributes.

## Relationship to the older artifacts

This repository also contains earlier approaches that remain valid as
alternatives:

- `tapo_ir_bridge.py` / `addon-tapo_ir_bridge/` — a standalone HTTP bridge
  (and HA add-on) exposing `/discover`, `/keys`, `/ir`.
- `appdaemon/` — an AppDaemon app that publishes the same control surface.
- `tapo_ir_generate.py` — generates `rest_command` + template button YAML.

This custom integration supersedes all of them for most users: it's the only
approach that creates true HA *devices* and *entities* in the registry.
