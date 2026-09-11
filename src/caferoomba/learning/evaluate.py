"""Held-out metrics. Fixture scores are software checks, not robot performance."""

from __future__ import annotations

from collections import Counter

import numpy as np
import torch

from caferoomba.learning.dataset import iter_examples
from caferoomba.schemas import CLASS_ORDER, ClipRecord


def evaluate_clips(model: torch.nn.Module, clips: list[ClipRecord], *, image_size: int) -> dict:
    model.eval()
    y_true: list[int] = []
    y_pred: list[int] = []
    turn_true: list[int] = []
    turn_pred: list[int] = []
    with torch.no_grad():
        for example in iter_examples(clips, size=image_size):
            frames = torch.from_numpy(example["frames"][None, ...])
            out = model(frames)
            pred = int(out["action_logits"][0].argmax())
            y_true.append(int(example["action"]))
            y_pred.append(pred)
            turn_true.append(int(example["turn180"] > 0.5))
            turn_pred.append(int(torch.sigmoid(out["turn_logit"][0]) > 0.5))
    matrix = np.zeros((4, 4), dtype=int)
    for truth, pred in zip(y_true, y_pred, strict=True):
        matrix[truth, pred] += 1
    per_class = {}
    for index, name in enumerate(CLASS_ORDER):
        tp = int(matrix[index, index])
        fp = int(matrix[:, index].sum() - tp)
        fn = int(matrix[index, :].sum() - tp)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_class[name] = {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "support": int(matrix[index, :].sum()),
        }
    macro = float(np.mean([row["f1"] for row in per_class.values()]))
    return {
        "n": len(y_true),
        "accuracy": float(np.mean(np.array(y_true) == np.array(y_pred))) if y_true else 0.0,
        "macro_f1": macro,
        "per_class": per_class,
        "confusion": matrix.tolist(),
        "turn180": {
            "true": dict(Counter(turn_true)),
            "pred": dict(Counter(turn_pred)),
        },
        "label_counts": dict(Counter(CLASS_ORDER[i] for i in y_true)),
        "is_synthetic": all(clip.source.is_synthetic for clip in clips),
        "evidence_state": "tested_offline",
        "note": "fixture metrics verify software only; not autonomous robot performance",
    }
