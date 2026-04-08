from __future__ import annotations

from typing import Callable


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, dict[str, Callable]] = {}
        self._provider_methods: dict[str, set[str]] = {}

    def register(self, provider: str, method: str, func: Callable) -> None:
        if provider not in self._providers:
            self._providers[provider] = {}
            self._provider_methods[provider] = set()
        self._providers[provider][method] = func
        self._provider_methods[provider].add(method)

    def get(self, provider: str, method: str):
        return self._providers.get(provider, {}).get(method)

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def list_methods(self, provider: str) -> list[str]:
        return list(self._provider_methods.get(provider, set()))


_global_registry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    return _global_registry


def register_provider(provider: str, method: str, func) -> None:
    _global_registry.register(provider, method, func)
