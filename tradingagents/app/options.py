from __future__ import annotations

from typing import Dict, List, Tuple

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.llm_clients.model_catalog import get_model_options

ModelChoice = Tuple[str, str]

DEFAULT_ANALYSTS = ("market", "social", "news", "fundamentals")

PROVIDER_CHOICES = (
    ("OpenAI", "openai", "https://api.openai.com/v1"),
    ("Google", "google", None),
    ("Anthropic", "anthropic", "https://api.anthropic.com/"),
    ("MiniMax", "minimax", "https://api.minimaxi.com/anthropic"),
    ("xAI", "xai", "https://api.x.ai/v1"),
    ("OpenRouter", "openrouter", "https://openrouter.ai/api/v1"),
    ("Ollama", "ollama", "http://localhost:11434/v1"),
)

RESEARCH_DEPTH_CHOICES = (
    ("Shallow", 1),
    ("Medium", 3),
    ("Deep", 5),
)

OUTPUT_LANGUAGE_CHOICES = (
    "English",
    "Chinese",
    "Japanese",
    "Korean",
    "Hindi",
    "Spanish",
    "Portuguese",
    "French",
    "German",
    "Arabic",
    "Russian",
)

PROVIDER_SETTING_CHOICES: Dict[str, List[ModelChoice]] = {
    "openai": [
        ("Medium (Default)", "medium"),
        ("High", "high"),
        ("Low", "low"),
    ],
    "anthropic": [
        ("High (recommended)", "high"),
        ("Medium", "medium"),
        ("Low", "low"),
    ],
    "google": [
        ("Enable Thinking", "high"),
        ("Minimal / Disable Thinking", "minimal"),
    ],
}


def get_provider_backend_url(provider: str) -> str | None:
    for _, value, backend_url in PROVIDER_CHOICES:
        if value == provider:
            return backend_url
    raise KeyError(provider)


def get_default_models(provider: str) -> tuple[str, str]:
    provider_lower = provider.lower()
    return (
        get_model_options(provider_lower, "quick")[0][1],
        get_model_options(provider_lower, "deep")[0][1],
    )


def get_default_request_values() -> dict:
    return {
        "llm_provider": DEFAULT_CONFIG["llm_provider"],
        "backend_url": DEFAULT_CONFIG["backend_url"],
        "quick_model": DEFAULT_CONFIG["quick_think_llm"],
        "deep_model": DEFAULT_CONFIG["deep_think_llm"],
        "output_language": DEFAULT_CONFIG["output_language"],
        "research_depth": DEFAULT_CONFIG["max_debate_rounds"],
        "analysts": DEFAULT_ANALYSTS,
    }
