"""Runtime composition root. No module opens hardware as an import side effect."""
from __future__ import annotations

from caferoomba.app.config import CompanionConfig


def apply_overrides(config: CompanionConfig, *, camera=None, vehicle=None,
                    camera_device=None, vehicle_device=None, policy_path=None,
                    record_dir=None) -> CompanionConfig:
    updated = config.model_copy(deep=True)
    if camera is not None:
        updated.camera.backend = camera
    if vehicle is not None:
        updated.vehicle.backend = vehicle
    if camera_device is not None:
        updated.camera.device = camera_device
    if vehicle_device is not None:
        updated.vehicle.device = vehicle_device
    if policy_path is not None:
        updated.policy.onnx_path = policy_path
    if record_dir is not None:
        updated.loop.record_dir = record_dir
    return CompanionConfig.model_validate(updated.model_dump())


def build_camera(config: CompanionConfig):
    from caferoomba.perception.fake import FakeCamera
    from caferoomba.perception.worker import LatestCamera
    camera = config.camera
    if camera.backend == "fake":
        return FakeCamera(width=camera.width, height=camera.height)
    kwargs = dict(width=camera.capture_width, height=camera.capture_height,
                  fps=camera.fps, timeout_ms=camera.read_timeout_ms)
    if camera.backend == "realsense":
        from caferoomba.perception.realsense import RealSenseCamera
        native = RealSenseCamera(**kwargs,
                                 serial_number=camera.serial_number,
                                 allow_infrared_diagnostics=camera.allow_infrared_diagnostics)
    elif camera.backend == "usb":
        from caferoomba.perception.process import ProcessCamera
        from caferoomba.perception.usb import UsbCamera
        if not camera.device:
            raise ValueError("USB camera requires an explicit /dev/v4l/by-id device path")
        native = UsbCamera(device=camera.device, **kwargs)
        return ProcessCamera(native)
    elif camera.backend == "imx219":
        from caferoomba.perception.csi_imx219 import Imx219Camera
        native = Imx219Camera(sensor_id=camera.sensor_id, **kwargs)
    else:
        raise ValueError("unknown camera backend")
    return LatestCamera(native)


def build_vehicle(config: CompanionConfig):
    if config.vehicle.allow_commands:
        raise RuntimeError("vehicle commands are not enabled in this shadow integration")
    if config.vehicle.backend == "dry-run":
        from caferoomba.vehicle.dry_run import DryRunVehicle
        return DryRunVehicle()
    if config.vehicle.backend == "serial-passive":
        from caferoomba.vehicle.serial_passive import PassiveSerialVehicle
        return PassiveSerialVehicle(config.vehicle)
    if config.vehicle.backend == "mavsdk":
        from caferoomba.vehicle.mavsdk_telemetry import MavsdkTelemetryVehicle
        return MavsdkTelemetryVehicle(config.vehicle)
    raise ValueError("unknown vehicle backend")
