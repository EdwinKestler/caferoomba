from pathlib import Path


def test_cube_script_never_lists_arm_commands():
    source = Path("scripts/capture_cube.py").read_text(encoding="utf-8")
    assert "MAV_CMD_COMPONENT_ARM_DISARM" not in source
    assert "arm_attempted" in source
    assert "HEARTBEAT" in source


def test_realsense_script_does_not_import_rover_gpio():
    source = Path("scripts/capture_realsense.py").read_text(encoding="utf-8")
    assert "pigpio" not in source
    assert "rover.robot" not in source
