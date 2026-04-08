from tradingagents.extensions.ashare.registry import ProviderRegistry


_global_registry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    return _global_registry


def register_provider(provider: str, method: str, func) -> None:
    _global_registry.register(provider, method, func)
