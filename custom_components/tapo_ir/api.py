"""Async access layer for a Tapo IR hub (KLAP/plugp100).

This module is deliberately free of any Home Assistant imports so its parsing and
naming helpers can be unit-tested standalone. It owns the hub connection, fires
individual IR keys, and enumerates every child IR remote with its decoded keys.

Nothing here is tied to a specific remote or account: all devices/keys are read
live from whatever hub the supplied credentials open.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import re
from typing import Any

from plugp100.common.credentials import AuthCredential
from plugp100.devices.device_factory import (
    connect,
    DeviceConnectConfiguration,
)
from plugp100.api.requests.tapo_request import TapoRequest

_LOGGER = logging.getLogger(__name__)


class TapoIrError(Exception):
    """Base error for the Tapo IR API."""


class TapoIrAuthError(TapoIrError):
    """Raised when the hub rejects the supplied credentials."""


class TapoIrConnectionError(TapoIrError):
    """Raised when the hub cannot be reached or a request fails."""


# ----------------------------------------------------------------------------
# Pure helpers (no I/O, no HA) — safe to unit-test on their own.
# ----------------------------------------------------------------------------
def decode_b64(value: str) -> str:
    """Decode a base64 label, falling back to the raw value."""
    try:
        return base64.b64decode(value).decode("utf-8")
    except Exception:  # noqa: BLE001 - any malformed value falls back
        return value


def slugify(value: str) -> str:
    """Lower-case, symbol-aware slug used for stable unique ids."""
    value = (value or "").strip().lower()
    value = value.replace("+", " plus ").replace("-", " minus ")
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value or "key"


# Tapo key ids look like 8-char mixed-case alphanumerics (e.g. "Gi4Hp70J").
_KEY_ID_RE = re.compile(r"^[A-Za-z0-9]{8}$")


def _looks_like_junk_nickname(nickname: str, key_names: list[str]) -> bool:
    """A nickname is 'junk' if empty, equal to one of the device's own key ids,
    or just shaped like a raw key id (mixed-case 8-char token)."""
    if not nickname:
        return True
    if nickname in set(key_names):
        return True
    return bool(
        _KEY_ID_RE.match(nickname)
        and any(c.islower() for c in nickname)
        and any(c.isupper() for c in nickname)
        and any(c.isdigit() for c in nickname)
    )


def humanize_device_name(
    device_id: str,
    nickname: str,
    key_names: list[str],
    overrides: dict[str, str] | None = None,
) -> str:
    """Resolve a friendly device name without baking in any product:
    user override (by device_id) -> meaningful hub nickname -> generic fallback.
    """
    override = (overrides or {}).get(device_id)
    if override:
        return override
    if not _looks_like_junk_nickname(nickname, key_names):
        return nickname
    return f"IR Remote {device_id[-4:]}"


_ICON_HINTS: list[tuple[str, str]] = [
    ("power", "mdi:power"),
    ("mute", "mdi:volume-mute"),
    ("cool", "mdi:snowflake"),
    ("heat", "mdi:fire"),
    ("fan", "mdi:fan"),
    ("source", "mdi:import"),
    ("input", "mdi:import"),
    ("settings", "mdi:cog"),
    ("menu", "mdi:menu"),
    ("back", "mdi:arrow-left-circle"),
    ("select", "mdi:checkbox-marked-circle"),
    ("ok", "mdi:checkbox-marked-circle"),
    ("up", "mdi:chevron-up"),
    ("down", "mdi:chevron-down"),
    ("left", "mdi:chevron-left"),
    ("right", "mdi:chevron-right"),
    ("+", "mdi:plus"),
    ("-", "mdi:minus"),
    ("hi", "mdi:speedometer"),
    ("lo", "mdi:speedometer-slow"),
]


def pick_icon(label: str) -> str:
    """Best-effort Material Design icon for a key label."""
    low = (label or "").lower()
    for keyword, icon in _ICON_HINTS:
        if keyword == low or keyword in low.split():
            return icon
    return "mdi:remote"


def parse_child_devices(
    raw: dict[str, Any], overrides: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    """Turn a raw get_child_device_list payload into a clean, sorted list of IR
    remote devices, each with decoded + slugified keys. Pure function."""
    devices: list[dict[str, Any]] = []
    for child in raw.get("child_device_list", []):
        if child.get("category") != "ir.remote":
            continue
        device_id = child["device_id"]
        key_list = child.get("key_list", [])
        nickname = humanize_device_name(
            device_id,
            decode_b64(child.get("nickname", "")),
            [k.get("name", "") for k in key_list],
            overrides,
        )
        keys: list[dict[str, Any]] = []
        seen: dict[str, int] = {}
        for key in key_list:
            label = decode_b64(key.get("display_name", "")) or key.get("name", "")
            key_slug = slugify(label)
            if key_slug in seen:
                seen[key_slug] += 1
                key_slug = f"{key_slug}_{seen[key_slug]}"
            else:
                seen[key_slug] = 1
            keys.append(
                {
                    "name": key["name"],  # the id sendIrCmdById needs
                    "label": label,
                    "slug": key_slug,
                    "icon": pick_icon(label),
                }
            )
        devices.append(
            {
                "device_id": device_id,
                "name": nickname,
                "slug": slugify(nickname),
                "model": child.get("model"),
                "key_count": child.get("key_sum", len(keys)),
                "keys": keys,
            }
        )
    devices.sort(key=lambda d: d["name"].lower())
    return devices


# ----------------------------------------------------------------------------
# Connection-owning client.
# ----------------------------------------------------------------------------
class TapoIrApi:
    """Owns the hub connection and exposes fire + enumerate."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        overrides: dict[str, str] | None = None,
    ) -> None:
        self._host = host
        self._username = username
        self._password = password
        self.overrides = overrides or {}
        self._device: Any = None
        self._lock = asyncio.Lock()
        self.hub_id: str | None = None
        self.hub_name: str = "Tapo IR Hub"
        self.hub_model: str | None = None
        self.hub_mac: str | None = None
        self.hub_fw: str | None = None

    @property
    def host(self) -> str:
        return self._host

    async def _get_client(self) -> Any:
        if self._device is None:
            cfg = DeviceConnectConfiguration(
                host=self._host,
                credentials=AuthCredential(self._username, self._password),
            )
            self._device = await connect(cfg)
        return self._device.client

    async def _request(self, request: TapoRequest) -> dict[str, Any]:
        """Execute a raw request, reconnecting on a stale KLAP session.

        A reused KLAP session can desync (surfacing as a decrypt/"Invalid
        padding" error or a non-success result). On any failure we drop the
        session and re-handshake before the next attempt.
        """
        async with self._lock:
            last_err: Exception | None = None
            for _attempt in (1, 2, 3):
                try:
                    client = await self._get_client()
                    res = await client.execute_raw_request(request)
                    if res.is_success():
                        return res.get()
                    last_err = TapoIrConnectionError(str(res.error()))
                except Exception as err:  # noqa: BLE001
                    last_err = err
                self._device = None  # force a fresh handshake next attempt
            raise TapoIrConnectionError(repr(last_err))

    async def async_connect(self) -> None:
        """Validate credentials and capture hub identity (id/mac/model/fw)."""
        try:
            info = await self._request(TapoRequest.get_device_info())
        except TapoIrConnectionError as err:
            msg = str(err).lower()
            # plugp100 reports bad credentials via the handshake failing; surface
            # those as an auth error so the config flow shows the right message.
            if any(
                token in msg
                for token in ("auth", "credential", "login", "password", "1501")
            ):
                raise TapoIrAuthError(str(err)) from err
            raise
        self.hub_id = info.get("device_id") or info.get("mac") or self._host
        self.hub_mac = info.get("mac")
        self.hub_model = info.get("model")
        self.hub_fw = info.get("fw_ver") or info.get("hw_ver")
        nickname = decode_b64(info.get("nickname", "")) if info.get("nickname") else ""
        if nickname:
            self.hub_name = nickname

    async def async_enumerate(self) -> list[dict[str, Any]]:
        """Return every child IR remote with its decoded keys (sorted)."""
        raw = await self._request(TapoRequest.get_child_device_list(0))
        return parse_child_devices(raw, self.overrides)

    async def async_fire(self, device_id: str, key_name: str) -> dict[str, Any]:
        """Fire a single stored IR key on a child remote."""
        inner = TapoRequest(
            method="multipleRequest",
            params={
                "requests": [
                    {"method": "sendIrCmdById", "params": {"name": key_name}}
                ]
            },
        )
        return await self._request(TapoRequest.control_child(device_id, inner))

    async def async_close(self) -> None:
        async with self._lock:
            device = self._device
            self._device = None
        if device is not None:
            try:
                await device.client.close()
            except Exception:  # noqa: BLE001
                pass
