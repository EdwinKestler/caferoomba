"""CafeRoomba learning and control package. Does not import legacy GPIO robots."""

__version__ = "0.1.0"

# Canonical body-frame convention: positive yaw rate is LEFT (CCW from above).
BODY_YAW_POSITIVE = "left"
# ArduPilot Rover / NED yaw is clockwise-positive when viewed from above.
MAVLINK_YAW_POSITIVE = "right"
