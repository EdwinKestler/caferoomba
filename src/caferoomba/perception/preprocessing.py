"""Shared image preprocessing for offline clips and runtime observations."""
from __future__ import annotations
import numpy as np
from PIL import Image


def rgb_tensor(rgb: np.ndarray, size: int) -> np.ndarray:
    """HWC uint8 RGB -> CHW float32 [0,1], using explicit bicubic resize."""
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
        raise ValueError("expected HWC uint8 RGB, not grayscale/depth/float")
    image = Image.fromarray(rgb).resize((size, size), Image.Resampling.BICUBIC)
    return (np.asarray(image, dtype=np.float32) / 255.0).transpose(2, 0, 1)
