"""Test configuration: stub out homeassistant modules so unit tests can run
without a full HA installation."""
from __future__ import annotations

import sys
import types


def _make_stub(*names: str) -> None:
    """Create empty stub modules for the given dotted names."""
    for name in names:
        parts = name.split(".")
        for i in range(1, len(parts) + 1):
            mod_name = ".".join(parts[:i])
            if mod_name not in sys.modules:
                sys.modules[mod_name] = types.ModuleType(mod_name)


_make_stub(
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.device_registry",
    "homeassistant.components",
    "homeassistant.components.sensor",
    "homeassistant.components.binary_sensor",
    "homeassistant.components.number",
    "homeassistant.components.select",
)

# Provide minimal stubs for symbols used in __init__.py / const.py
ha = sys.modules["homeassistant"]
ce = sys.modules["homeassistant.config_entries"]
ce.ConfigEntry = object  # type: ignore[attr-defined]

const = sys.modules["homeassistant.const"]
const.CONF_HOST = "host"  # type: ignore[attr-defined]
const.CONF_PORT = "port"  # type: ignore[attr-defined]

core = sys.modules["homeassistant.core"]
core.HomeAssistant = object  # type: ignore[attr-defined]
core.callback = lambda f: f  # type: ignore[attr-defined]

exc = sys.modules["homeassistant.exceptions"]
exc.ConfigEntryNotReady = Exception  # type: ignore[attr-defined]

# DeviceInfo stub
dr = sys.modules["homeassistant.helpers.device_registry"]


class _DeviceInfo(dict):
    """Minimal DeviceInfo stub that stores kwargs as a dict."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


dr.DeviceInfo = _DeviceInfo  # type: ignore[attr-defined]
