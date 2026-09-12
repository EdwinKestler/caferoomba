"""Exportable temporal student. Tiny backbone is for CPU fixtures only."""

from __future__ import annotations

import torch
from torch import nn

from caferoomba.schemas import CLASS_ORDER


class TinyTemporalPolicy(nn.Module):
    """Causal-enough 2D encoder + temporal conv. Not MobileNet; fixture/export smoke."""

    def __init__(self, *, in_frames: int = 8, image_size: int = 64) -> None:
        super().__init__()
        self.in_frames = in_frames
        self.image_size = image_size
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 16, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.temporal = nn.Conv1d(32, 32, kernel_size=3, padding=0)
        self.action_head = nn.Linear(32, len(CLASS_ORDER))
        self.turn_head = nn.Linear(32, 1)
        self.aux_head = nn.Linear(32, 2)

    def forward(self, frames: torch.Tensor) -> dict[str, torch.Tensor]:
        # frames: B, T, C, H, W — only provided past/current frames.
        batch, time, channels, height, width = frames.shape
        encoded = self.encoder(frames.reshape(batch * time, channels, height, width))
        encoded = encoded.view(batch, time, 32).transpose(1, 2)
        temporal = torch.relu(self.temporal(encoded))
        pooled = temporal.mean(dim=-1)
        return {
            "action_logits": self.action_head(pooled),
            "turn_logit": self.turn_head(pooled).squeeze(-1),
            "aux_logits": self.aux_head(pooled),
        }


def build_policy(*, backbone: str = "tiny", in_frames: int = 8, image_size: int = 64) -> nn.Module:
    if backbone == "tiny":
        return TinyTemporalPolicy(in_frames=in_frames, image_size=image_size)
    if backbone == "mobilenet_v3_small":
        from torchvision.models import mobilenet_v3_small

        class MobileNetTemporal(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.in_frames = in_frames
                self.image_size = image_size
                # Checkpoint construction must be offline-safe. A caller that wants
                # pretrained weights can load them explicitly before training.
                net = mobilenet_v3_small(weights=None)
                self.features = net.features
                self.pool = nn.AdaptiveAvgPool2d(1)
                self.temporal = nn.Conv1d(576, 128, kernel_size=3, padding=0)
                self.action_head = nn.Linear(128, len(CLASS_ORDER))
                self.turn_head = nn.Linear(128, 1)
                self.aux_head = nn.Linear(128, 2)

            def forward(self, frames: torch.Tensor) -> dict[str, torch.Tensor]:
                batch, time, channels, height, width = frames.shape
                feats = self.pool(
                    self.features(frames.reshape(batch * time, channels, height, width))
                ).view(batch, time, 576).transpose(1, 2)
                temporal = torch.relu(self.temporal(feats)).mean(dim=-1)
                return {
                    "action_logits": self.action_head(temporal),
                    "turn_logit": self.turn_head(temporal).squeeze(-1),
                    "aux_logits": self.aux_head(temporal),
                }

        return MobileNetTemporal()
    raise ValueError(f"unknown backbone {backbone}")


def count_parameters(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
