"""One-or-more CPU training steps. Human action is the primary target."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from caferoomba.learning.dataset import iter_examples
from caferoomba.learning.model import build_policy, count_parameters
from caferoomba.schemas import ClipRecord


def _batch(examples: list[dict]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    frames = torch.from_numpy(np.stack([item["frames"] for item in examples]))
    action = torch.tensor([item["action"] for item in examples], dtype=torch.long)
    turn = torch.tensor([item["turn180"] for item in examples], dtype=torch.float32)
    return frames, action, turn


def train_steps(
    clips: list[ClipRecord],
    *,
    output_dir: Path,
    steps: int = 1,
    lr: float = 1e-3,
    backbone: str = "tiny",
    image_size: int = 64,
    in_frames: int = 8,
    seed: int = 0,
    device: str = "cpu",
) -> dict:
    torch.manual_seed(seed)
    examples = list(iter_examples(clips, size=image_size, split="train"))
    if not examples:
        examples = list(iter_examples(clips, size=image_size))
    if not examples:
        raise ValueError("no training examples")
    model = build_policy(backbone=backbone, in_frames=in_frames, image_size=image_size).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    frames, action, turn = _batch(examples[:8])
    frames, action, turn = frames.to(device), action.to(device), turn.to(device)
    history = []
    model.train()
    for _step in range(steps):
        optimizer.zero_grad()
        out = model(frames)
        action_loss = F.cross_entropy(out["action_logits"], action)
        turn_loss = F.binary_cross_entropy_with_logits(out["turn_logit"], turn)
        loss = action_loss + 0.5 * turn_loss
        loss.backward()
        optimizer.step()
        history.append(float(loss.detach()))
    output_dir.mkdir(parents=True, exist_ok=True)
    ckpt = output_dir / "student.pt"
    torch.save(
        {
            "state_dict": model.state_dict(),
            "backbone": backbone,
            "in_frames": in_frames,
            "image_size": image_size,
            "seed": seed,
            "is_synthetic": all(item["is_synthetic"] for item in examples),
            "parameter_count": count_parameters(model),
        },
        ckpt,
    )
    return {
        "checkpoint": str(ckpt),
        "loss": history,
        "parameter_count": count_parameters(model),
        "device": device,
        "backbone": backbone,
        "is_synthetic": all(item["is_synthetic"] for item in examples),
        "evidence_state": "tested_offline",
    }


def load_checkpoint(path: Path, device: str = "cpu") -> nn.Module:
    blob = torch.load(path, map_location=device, weights_only=False)
    model = build_policy(
        backbone=blob["backbone"],
        in_frames=blob["in_frames"],
        image_size=blob["image_size"],
    )
    model.load_state_dict(blob["state_dict"])
    model.eval()
    return model
