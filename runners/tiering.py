from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_TIER_NAMES = ("cheap", "expensive")
GPT_PATTERN = re.compile(r"gpt|gpt-oss", re.IGNORECASE)


@dataclass(frozen=True)
class TierSpec:
    name: str
    provider: str
    model: str
    label: str

    @property
    def slug_label(self) -> str:
        value = self.label or self.model or self.name
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or self.name


def load_tier_specs(path: str | Path) -> dict[str, TierSpec]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    specs: dict[str, TierSpec] = {}
    for name, payload in data.items():
        specs[name] = TierSpec(
            name=name,
            provider=str(payload["provider"]),
            model=str(payload["model"]),
            label=str(payload.get("label") or payload["model"]),
        )
    return specs


def apply_tier_overrides(
    tier_specs: dict[str, TierSpec],
    *,
    model_overrides: dict[str, str] | None = None,
    provider_overrides: dict[str, str] | None = None,
) -> dict[str, TierSpec]:
    updated: dict[str, TierSpec] = {}
    for name, spec in tier_specs.items():
        model = (model_overrides or {}).get(name, spec.model)
        provider = (provider_overrides or {}).get(name, spec.provider)
        label = spec.label
        if model != spec.model or provider != spec.provider:
            label = model
        updated[name] = TierSpec(
            name=name,
            provider=provider,
            model=model,
            label=label,
        )
    return updated


def parse_key_value_overrides(values: list[str] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError(f"Expected KEY=VALUE override, got: {value}")
        key, raw_value = value.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Override key cannot be empty: {value}")
        result[key] = raw_value.strip()
    return result


def classify_model_tier(model: str | None) -> tuple[str, str]:
    normalized = str(model or "").strip().lower()
    if not normalized:
        return "unclassified", "missing-model"
    if "openai/gpt-oss-120b:nitro" in normalized:
        return "expensive", "historical-gpt-oss-120b-nitro-exception"
    if "minimax" in normalized:
        return "expensive", "minimax-family"
    if "deepseek" in normalized:
        return "expensive", "deepseek-family"
    if GPT_PATTERN.search(normalized):
        return "cheap", "gpt-family-non-nitro"
    return "unclassified", "no-known-tier-rule"


def classify_role_tiers(models: dict[str, Any]) -> dict[str, str]:
    return {
        role: classify_model_tier(str(model) if model is not None else None)[0]
        for role, model in models.items()
    }


def tier_config_id_from_roles(role_tiers: dict[str, str]) -> str | None:
    generator = role_tiers.get("generator")
    reflector = role_tiers.get("reflector")
    curator = role_tiers.get("curator")
    if not generator or not reflector or not curator:
        return None
    trio = (generator, reflector, curator)
    if trio == ("cheap", "cheap", "cheap"):
        return "all_cheap"
    if trio == ("expensive", "expensive", "expensive"):
        return "all_expensive"
    if trio == ("expensive", "cheap", "cheap"):
        return "expensive_generator"
    if trio == ("cheap", "expensive", "cheap"):
        return "expensive_reflector"
    if trio == ("cheap", "cheap", "expensive"):
        return "expensive_curator"
    return None


def tier_metadata_for_models(models: dict[str, Any]) -> dict[str, Any]:
    role_tiers: dict[str, str] = {}
    sources: dict[str, str] = {}
    for role, model in models.items():
        tier, source = classify_model_tier(str(model) if model is not None else None)
        role_tiers[role] = tier
        sources[role] = source
    return {
        "role_tiers": role_tiers,
        "tier_config_id": tier_config_id_from_roles(role_tiers),
        "classification_sources": sources,
    }
