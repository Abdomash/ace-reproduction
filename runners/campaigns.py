from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tiering import TierSpec, load_tier_specs


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGNS_ROOT = REPO_ROOT / "runners" / "campaigns"


@dataclass(frozen=True)
class Campaign:
    campaign_id: str
    root: Path
    manifest: dict[str, Any]
    tier_specs: dict[str, TierSpec]
    configs: dict[str, dict[str, Any]]
    samples: dict[str, dict[str, Any]]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_campaign(campaign_id: str = "ace_repr_v1") -> Campaign:
    root = CAMPAIGNS_ROOT / campaign_id
    manifest = _load_json(root / "campaign.json")
    tier_specs = load_tier_specs(root / manifest.get("tiers_path", "tiers.json"))
    configs = _load_json(root / manifest.get("configs_path", "configs.json"))
    samples_dir = root / manifest.get("samples_dir", "samples")
    samples = {
        path.stem: _load_json(path)
        for path in sorted(samples_dir.glob("*.json"))
    }
    return Campaign(
        campaign_id=manifest.get("campaign_id", campaign_id),
        root=root,
        manifest=manifest,
        tier_specs=tier_specs,
        configs=configs,
        samples=samples,
    )
