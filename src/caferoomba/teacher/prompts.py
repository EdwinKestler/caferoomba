"""Prompt bytes used in the teacher cache key."""

from __future__ import annotations

import hashlib

PROMPT_V1 = """You annotate a coffee-bean drying patio FPV clip.
Return JSON only with keys: patch_visible, boundary_ahead, suggested_action,
turn180_trigger_candidate, brief_visible_evidence, uncertainty.
These are visual annotations, not motor commands or certified contours.
"""


def prompt_sha256(text: str = PROMPT_V1) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
