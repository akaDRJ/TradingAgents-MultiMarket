# 2026-04-09 Release Notes

## Summary

This update adds a shared market-extension seam, keeps the A-share path upstream-compatible, and introduces first-version crypto spot analysis support.

## Major Changes

- Added a shared `market_ext` dispatcher so market-specific capabilities can live in extension modules instead of spreading across upstream files.
- Migrated the existing A-share extension onto the shared dispatcher while preserving A-share behavior and keeping HK tickers on the upstream vendor path.
- Added `extensions/crypto` with:
  - crypto market detection and normalization
  - Binance Spot public market-data provider
  - CoinGecko market/fundamentals provider
  - explicit unsupported-method handling
- Added crypto news routing through a lightweight public RSS-backed provider.
- Added market-aware analyst prompt instructions for crypto fundamentals and crypto social analysis.

## Docker / Runtime

- Core crypto functionality remains Docker-safe.
- No host-only dependencies such as `autocli` or `agent-reach` are required in the runtime path.
- `COINGECKO_API_KEY` remains optional; the default path is designed to run without it.

## Verification

Verified locally with:

```bash
uv run python -m unittest \
  tests.test_market_extension_dispatch \
  tests.test_ashare_interface \
  tests.test_ashare_routing \
  tests.test_ashare_indicators \
  tests.test_ashare_providers \
  tests.test_ashare_shared_dispatcher \
  tests.test_ashare_fundamentals \
  tests.test_ashare_news \
  tests.test_crypto_market_detection \
  tests.test_crypto_normalization \
  tests.test_crypto_binance_provider \
  tests.test_crypto_coingecko_provider \
  tests.test_crypto_interface_routing \
  tests.test_crypto_public_news_provider \
  tests.test_market_specific_instruction \
  tests.test_news_analyst_context \
  -v
```

Result: `Ran 48 tests ... OK`

## Follow-up Note

- Refreshed `uv.lock` so it matches the current project dependency set, including the A-share provider stack already declared in `pyproject.toml`.
