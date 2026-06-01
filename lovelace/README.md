# Tapo IR Card (custom Lovelace card)

A self-contained dashboard card for the **Tapo IR Hub** custom integration. It
auto-discovers every hub you've configured and draws each child remote as its
own panel, with one tappable button per stored IR key. No entity IDs to wire up
by hand — devices, names, keys and icons are read live from Home Assistant's
registry, so the same card works for any user, hub and set of remotes.

## Features

- **Auto-discovery** — finds all `tapo_ir` devices; groups child remotes under
  their hub via the device registry (`via_device`).
- **Two layouts** — `grid` (responsive button grid) or `remote` (handset style
  with a D-pad cluster, volume/channel rockers and a utility row).
- **Hub header** — the hub's friendly name, diagnostic chips (Discovered
  devices / Last scan) and a one-tap **Rescan** button.
- **Collapsible remotes**, include/exclude filters, multi-hub support.
- **Visual editor** (GUI) plus full YAML config.
- Press feedback animation; buttons auto-disable when unavailable.

## Install

1. Copy `tapo-ir-card.js` into your HA config's `www` folder, i.e.
   `/config/www/tapo-ir-card.js`.
2. Add it as a dashboard resource:
   **Settings → Dashboards → ⋮ → Resources → Add resource**
   - URL: `/local/tapo-ir-card.js`
   - Type: **JavaScript Module**

   (Or in YAML mode, under `lovelace: resources:` add
   `- url: /local/tapo-ir-card.js` `type: module`.)
3. Hard-refresh the browser (Ctrl/Cmd-Shift-R).

Then **Add card → search "Tapo IR Card"**, or add it by YAML (below).

## Minimal usage

```yaml
type: custom:tapo-ir-card
```

That's it — every hub and remote shows up automatically.

## Configuration

| Option              | Type            | Default  | Description |
|---------------------|-----------------|----------|-------------|
| `title`             | string          | —        | Optional heading at the top of the card. |
| `layout`            | `grid`/`remote` | `grid`   | `grid` = button grid; `remote` = handset arrangement. |
| `columns`           | number (1–6)    | `3`      | Columns in grid layouts. |
| `show_hub`          | boolean         | `true`   | Show the hub header row. |
| `show_diagnostics`  | boolean         | `true`   | Show the Discovered-devices / Last-scan chips (tap a chip for more-info). |
| `show_rescan`       | boolean         | `true`   | Show the hub Rescan button. |
| `collapsible`       | boolean         | `false`  | Make each remote panel collapsible (tap its header). |
| `default_collapsed` | boolean         | `false`  | Start remotes collapsed (needs `collapsible`). |
| `show_empty`        | boolean         | `false`  | Also render hubs that currently expose no remotes. |
| `hub`               | string / list   | —        | Limit the card to one or more hubs (by friendly name or device id). |
| `include`           | string / list   | —        | Only show these remotes (by name or device id). |
| `exclude`           | string / list   | —        | Hide these remotes (by name or device id). |

### Remote (handset) layout

With `layout: remote` the card recognises common keys by their label and
arranges them like a physical remote:

- **Utility row** — Power, Source/Input, Back, Settings, Menu, Home, Mute.
- **D-pad** — Up / Down / Left / Right with a center OK/Select.
- **Rockers** — `+`/`-` (Vol) and Channel Up/Down.
- Anything else falls into a grid beneath.

If a remote has none of those keys, it automatically falls back to a grid, so
the layout is always sensible.

## Examples

A clean handset for the living-room AC only:

```yaml
type: custom:tapo-ir-card
title: Air Conditioner
layout: remote
include: Living Room AC
show_diagnostics: false
```

Compact, collapsible grid of every remote with 4 columns:

```yaml
type: custom:tapo-ir-card
layout: grid
columns: 4
collapsible: true
default_collapsed: true
```

Two specific remotes, hub header hidden:

```yaml
type: custom:tapo-ir-card
show_hub: false
include:
  - PC Monitors
  - Soundbar
```

## Combining with native visibility

This card focuses on rendering. For *conditional* display use Home Assistant's
built-in card **Visibility** tab (Settings on the card → Visibility), or wrap it
in a `conditional` card — e.g. only show the AC remote when someone's home. The
two compose cleanly.

## Requirements & notes

- Requires the **Tapo IR Hub** custom integration (provides the devices,
  button entities and hub diagnostics this card reads).
- Needs a reasonably recent Home Assistant frontend (uses the `hass.entities` /
  `hass.devices` registries and `ha-form`), i.e. 2023.4+.
- No external dependencies and no build step — it's a single vanilla JS module.
