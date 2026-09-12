"""Held-out metrics. Fixture scores are software checks, not robot performance."""

from __future__ import annotations

from collections import Counter

import numpy as np
import torch

from caferoomba.data.splits import detect_split_leakage
from caferoomba.learning.dataset import iter_examples
from caferoomba.schemas import CLASS_ORDER, ClipRecord


def _model_device(model: torch.nn.Module) -> torch.device:
    try:
        return next(model.parameters()).device
    except StopIteration:
        return torch.device("cpu")


def _binary_metrics(truth: list[int], predicted: list[int]) -> dict:
    matrix = np.zeros((2, 2), dtype=int)
    for actual, estimate in zip(truth, predicted, strict=True):
        matrix[actual, estimate] += 1
    tn, fp = (int(value) for value in matrix[0])
    fn, tp = (int(value) for value in matrix[1])
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "confusion": matrix.tolist(),
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": (tp + tn) / len(truth) if truth else 0.0,
        "support": len(truth),
        # String keys survive JSON report round-trips without changing equality.
        "true": dict(Counter(str(value) for value in truth)),
        "pred": dict(Counter(str(value) for value in predicted)),
    }


def evaluate_clips(
    model: torch.nn.Module,
    clips: list[ClipRecord],
    *,
    image_size: int,
    split: str | None = None,
    device: str | torch.device | None = None,
) -> dict:
    """Evaluate clips, with strict run-disjoint checks for held-out splits.

    ``split=None`` retains the original smoke-test API. Passing ``"val"`` or
    ``"test"`` requires a non-empty requested split and rejects any run that
    appears under more than one split label in ``clips``.
    """

    if split not in {None, "train", "val", "test"}:
        raise ValueError(f"unknown split {split!r}")
    if image_size < 1:
        raise ValueError("image_size must be >= 1")
    unassigned = any(clip.split not in {"train", "val", "test"} for clip in clips)
    if split in {"val", "test"} and unassigned:
        raise ValueError("strict held-out evaluation requires split labels on every clip")
    leakage = detect_split_leakage(clips)
    if split in {"val", "test"} and leakage:
        raise ValueError(f"run leakage across splits: {', '.join(sorted(leakage))}")
    selected = clips if split is None else [clip for clip in clips if clip.split == split]
    if split in {"val", "test"} and not selected:
        raise ValueError(f"held-out split {split!r} is empty")
    if not selected:
        raise ValueError("no evaluation examples")

    target_device = torch.device(device) if device is not None else _model_device(model)
    model.to(target_device)
    model.eval()
    y_true: list[int] = []
    y_pred: list[int] = []
    turn_true: list[int] = []
    turn_pred: list[int] = []
    with torch.no_grad():
        for example in iter_examples(selected, size=image_size):
            frames = torch.from_numpy(example["frames"][None, ...]).to(target_device)
            out = model(frames)
            if not isinstance(out, dict):
                raise ValueError("model output must be a mapping")
            action_logits = out.get("action_logits")
            turn_logit = out.get("turn_logit")
            if (
                not isinstance(action_logits, torch.Tensor)
                or tuple(action_logits.shape) != (1, len(CLASS_ORDER))
            ):
                raise ValueError("model returned invalid action_logits shape")
            if not isinstance(turn_logit, torch.Tensor) or tuple(turn_logit.shape) != (1,):
                raise ValueError("model returned invalid turn_logit shape")
            if not torch.isfinite(action_logits).all().item() or not torch.isfinite(
                turn_logit
            ).all().item():
                raise ValueError("model returned non-finite logits")
            pred = int(action_logits[0].argmax().item())
            y_true.append(int(example["action"]))
            y_pred.append(pred)
            turn_true.append(int(example["turn180"] > 0.5))
            turn_pred.append(int((torch.sigmoid(turn_logit[0]) > 0.5).item()))
    matrix = np.zeros((len(CLASS_ORDER), len(CLASS_ORDER)), dtype=int)
    for truth, pred in zip(y_true, y_pred, strict=True):
        matrix[truth, pred] += 1
    per_class = {}
    for index, name in enumerate(CLASS_ORDER):
        tp = int(matrix[index, index])
        fp = int(matrix[:, index].sum() - tp)
        fn = int(matrix[index, :].sum() - tp)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[name] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": int(matrix[index, :].sum()),
        }
    macro = float(np.mean([row["f1"] for row in per_class.values()]))
    return {
        "n": len(y_true),
        "split": split,
        "device": str(target_device),
        "accuracy": float(np.mean(np.array(y_true) == np.array(y_pred))),
        "macro_f1": macro,
        "per_class": per_class,
        "confusion": matrix.tolist(),
        "turn180": _binary_metrics(turn_true, turn_pred),
        "label_counts": dict(Counter(CLASS_ORDER[index] for index in y_true)),
        "is_synthetic": all(clip.source.is_synthetic for clip in selected),
        "evidence_state": "tested_offline",
        "note": "fixture metrics verify software only; not autonomous robot performance",
    }
