"""Navigation intent boundary. No VLM-to-PWM path."""

from __future__ import annotations

from caferoomba.schemas import ActionLabel, Intent

# Body-frame left-positive yaw. MAVLink NED adapters must negate this.
YAW_RATE_LEFT_RAD_S = 0.4
SPEED_STRAIGHT_MPS = 0.4


def intent_from_policy(
    *,
    action: ActionLabel,
    now_ms: int,
    ttl_ms: int = 250,
    turn180_score: float = 0.0,
    source: str = "student",
) -> Intent:
    yaw = None
    speed = 0.0
    if action is ActionLabel.LEFT:
        yaw = YAW_RATE_LEFT_RAD_S
        speed = SPEED_STRAIGHT_MPS * 0.5
    elif action is ActionLabel.RIGHT:
        yaw = -YAW_RATE_LEFT_RAD_S
        speed = SPEED_STRAIGHT_MPS * 0.5
    elif action is ActionLabel.STRAIGHT:
        yaw = 0.0
        speed = SPEED_STRAIGHT_MPS
    return Intent(
        action=action,
        yaw_rate_rad_s=yaw,
        speed_mps=speed,
        issued_at_ms=now_ms,
        expires_at_ms=now_ms + ttl_ms,
        source=source,
        valid=True,
        turn180_trigger=turn180_score >= 0.5 and action != ActionLabel.STOP,
        coordinate_frame="body",
    )


def to_mavlink_yaw_rate(body_yaw_rate_rad_s: float | None) -> float | None:
    """NED/ArduPilot Rover yaw is opposite body-left-positive."""
    if body_yaw_rate_rad_s is None:
        return None
    return -float(body_yaw_rate_rad_s)
