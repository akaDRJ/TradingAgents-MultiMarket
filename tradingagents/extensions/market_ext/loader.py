from __future__ import annotations

import importlib
import os
from typing import Iterable

from .module import ExtensionModule
from .registry import get_extension, register_module


DEFAULT_MODULES = (
    "tradingagents.extensions.ashare",
    "tradingagents.extensions.crypto",
)


def configured_module_names() -> tuple[str, ...]:
    raw = os.getenv("TRADINGAGENTS_EXTENSION_MODULES")
    if raw is None:
        return DEFAULT_MODULES

    return tuple(name.strip() for name in raw.split(",") if name.strip())


def _module_from_import(module_name: str) -> ExtensionModule:
    imported = importlib.import_module(module_name)
    get_module = getattr(imported, "get_extension_module", None)
    if not callable(get_module):
        raise ValueError(f"Extension module '{module_name}' must expose get_extension_module()")

    module = get_module()
    if not isinstance(module, ExtensionModule):
        raise TypeError(
            f"Extension module '{module_name}' returned {type(module)!r}, expected ExtensionModule"
        )
    return module


def load_extension_modules(module_names: Iterable[str] | None = None, *, strict: bool = True) -> None:
    for module_name in module_names or configured_module_names():
        try:
            module = _module_from_import(module_name)
        except (TypeError, ValueError):
            if strict:
                raise
            continue
        if get_extension(module.name) is None:
            register_module(module)
