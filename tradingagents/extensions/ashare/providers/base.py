"""Base provider interface for A-share data providers.

All A-share providers must implement the methods defined here.
Providers are called via the registry/routing layer.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ProviderError(Exception):
    """Raised by a provider when it cannot fulfill a request.

    The routing layer catches this exception and falls through
    to the next provider in the chain.
    """

    def __init__(self, provider: str, ticker: str, message: str) -> None:
        self.provider = provider
        self.ticker = ticker
        self.message = message
        super().__init__(f"[{provider}] {message}")


class BaseProvider(ABC):
    """Abstract base class for A-share data providers.

    Subclasses must implement all data-fetch methods.
    The routing layer calls providers in order and falls through on failure.
    """

    name: str = "base"

    @abstractmethod
    def get_stock_data(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Fetch OHLCV bar data for a single ticker.

        Args:
            ticker: Normalized ticker with exchange suffix (e.g. "600519.SS")
            start_date: Start date in YYYY-MM-DD format, optional
            end_date: End date in YYYY-MM-DD format, optional
            **kwargs: Additional provider-specific arguments

        Returns:
            Dict with at least "ticker", "data" (list of bars), and "provider" keys.
            Raises ProviderError on failure so routing can fall through.
        """
        ...

    def _error(self, ticker: str, message: str) -> None:
        """Raise a ProviderError to signal routing should fall through."""
        raise ProviderError(self.name, ticker, message)
