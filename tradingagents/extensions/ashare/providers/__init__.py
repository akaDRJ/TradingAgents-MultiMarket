"""A-share data providers.

This module provides data provider adapters for A-share markets.
Each provider implements the BaseProvider interface and registers
itself with the global registry when imported.

Providers are tried in order via the routing layer until one succeeds.
All providers fail gracefully if their underlying package is unavailable.

Usage:
    # Providers auto-register on import
    from tradingagents.extensions.ashare.providers import (
        tushare, akshare, baostock
    )

    # Or import the registry directly
    from tradingagents.extensions.ashare import get_registry
    registry = get_registry()
    print(registry.list_providers())  # ["tushare", "akshare", "baostock"]
"""

from tradingagents.extensions.ashare.registry import register_provider

# Import providers to trigger registration
# Each module registers its get_stock_data method with the global registry
from . import tushare as _tushare_mod
from . import akshare as _akshare_mod
from . import baostock as _baostock_mod

# Re-export for convenience
from .base import BaseProvider
from .tushare import TushareProvider
from .akshare import AKShareProvider
from .baostock import BaoStockProvider

__all__ = [
    "BaseProvider",
    "TushareProvider",
    "AKShareProvider",
    "BaoStockProvider",
]


def _register_providers() -> None:
    """Register all provider methods with the global registry."""
    # Tushare
    tushare_instance = _tushare_mod.get_provider()
    register_provider("tushare", "get_stock_data", tushare_instance.get_stock_data)

    # AKShare
    akshare_instance = _akshare_mod.get_provider()
    register_provider("akshare", "get_stock_data", akshare_instance.get_stock_data)
    register_provider("akshare", "get_fundamentals", akshare_instance.get_fundamentals)
    register_provider("akshare", "get_balance_sheet", akshare_instance.get_balance_sheet)
    register_provider("akshare", "get_cashflow", akshare_instance.get_cashflow)
    register_provider("akshare", "get_income_statement", akshare_instance.get_income_statement)

    # BaoStock
    baostock_instance = _baostock_mod.get_provider()
    register_provider("baostock", "get_stock_data", baostock_instance.get_stock_data)


# Auto-register on import
_register_providers()
