"""Independent fail-closed supervisor. Softmax confidence is not a safety signal."""

from __future__ import annotations

import math

from caferoomba.schemas import ActionLabel, Intent, SafetyDecision


def supervise(
    intent: Intent,
    *,
    now_ms: int,
    observation_age_ms: int | None,
    max_observation_age_ms: int = 300,
    operator_stop: bool = False,
    heartbeat_ok: bool = True,
    nan_prediction: bool = False,
    required_sensor_missing: bool = False,
    max_speed_mps: float = 0.8,
    max_abs_yaw_rad_s: float = 1.2,
    geofence_ok: bool = True,
    footprint_clear: bool = True,
) -> SafetyDecision:
    reasons: list[str] = []
    if operator_stop:
        reasons.append("operator_stop")
    if not heartbeat_ok:
        reasons.append("lost_heartbeat")
    if nan_prediction:
        reasons.append("nan_prediction")
    if required_sensor_missing:
        reasons.append("missing_required_sensor")
    if observation_age_ms is None or observation_age_ms > max_observation_age_ms:
        reasons.append("stale_observation")
    if now_ms > intent.expires_at_ms:
        reasons.append("expired_intent")
    if not intent.valid:
        reasons.append("invalid_intent")
    if intent.speed_mps is not None and (
        not math.isfinite(intent.speed_mps) or abs(intent.speed_mps) > max_speed_mps
    ):
        reasons.append("speed_limit")
    if intent.yaw_rate_rad_s is not None and (
        not math.isfinite(intent.yaw_rate_rad_s)
        or abs(intent.yaw_rate_rad_s) > max_abs_yaw_rad_s
    ):
        reasons.append("yaw_limit")
    if not geofence_ok:
        reasons.append("geofence")
    if not footprint_clear:
        reasons.append("footprint_blocked")
    if reasons:
        return SafetyDecision(
            allow=False, action=ActionLabel.STOP, reasons=reasons, fail_closed=True
        )
    return SafetyDecision(allow=True, action=intent.action, reasons=[], fail_closed=True)
