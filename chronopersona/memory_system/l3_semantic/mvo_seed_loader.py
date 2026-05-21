"""MVO seed loader implementation."""

import os
from typing import Any, Dict

import yaml

from loguru import logger


class MVOSeedLoader:
    """Load MVO seeds from YAML configs idempotently."""

    def __init__(self, config_dir: str = "configs/mvo_extensions") -> None:
        self._config_dir = config_dir

    def load(self, domain: str, branch_id: str) -> Dict[str, Any]:
        if not domain or not branch_id:
            raise ValueError("domain and branch_id must not be empty")
        path = os.path.join(self._config_dir, f"{domain}.yaml")
        if not os.path.exists(path):
            logger.warning("MVO seed not found: {}", path)
            return {"concepts": 0, "patterns": 0}

        with open(path) as f:
            data = yaml.safe_load(f)

        concepts = data.get("concepts", [])
        patterns = data.get("intent_patterns", [])
        logger.info(
            "MVO seed loaded: domain={} branch={} concepts={} patterns={}",
            domain, branch_id, len(concepts), len(patterns)
        )
        return {"concepts": len(concepts), "patterns": len(patterns)}
