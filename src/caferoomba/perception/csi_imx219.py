"""IMX219 on Orin MIPI CSI-2. Unavailable on this x86 host."""

from __future__ import annotations

from caferoomba.perception.camera import FrameSet


class Imx219Camera:
    name = "imx219"

    def open(self) -> None:
        raise RuntimeError(
            "IMX219 CSI is Orin-only (PR5). Use camera.backend: fake on this host."
        )

    def read(self) -> FrameSet:
        raise RuntimeError("Imx219Camera is not open")

    def close(self) -> None:
        return

    def is_open(self) -> bool:
        return False
