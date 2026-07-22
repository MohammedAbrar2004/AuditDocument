"""Loaded-once singletons (v2_phase5.md SS4): the BGE-M3 model and the
checklist-persistent scope (parsed items + item embeddings for both
checklists, Phase 3's output). Populated once by main.py's startup hook,
read by routers -- never reloaded per request.
"""
import json

import numpy as np

from app.config import settings
from app.pipeline.phase3.embed import load_model

CHECKLIST_PREFIXES = ("AQB", "AEC")


class AppState:
    def __init__(self):
        self.model = None
        self.checklists: dict[str, dict] = {}

    def load(self) -> None:
        self.model = load_model(settings.MODEL_DIR)

        phase3_dir = settings.ARTIFACTS_DIR / "phase3"
        for prefix in CHECKLIST_PREFIXES:
            data = json.loads(
                (phase3_dir / f"checklist_{prefix.lower()}.json").read_text(encoding="utf-8")
            )
            embeddings = np.load(phase3_dir / f"item_embeddings_{prefix.lower()}.npy")
            items = data["items"]
            if embeddings.shape[0] != len(items):
                raise ValueError(
                    f"item_embeddings_{prefix.lower()}.npy has {embeddings.shape[0]} rows, "
                    f"checklist_{prefix.lower()}.json has {len(items)} items -- misaligned."
                )
            self.checklists[prefix] = {
                "source_pdf": data["source_pdf"],
                "items": items,
                "embeddings": embeddings,
            }


app_state = AppState()
