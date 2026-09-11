"""Records intents; never opens serial or GPIO."""

from __future__ import annotations

from caferoomba.control.safety import supervise
from caferoomba.schemas import Intent, SafetyDecision


class DryRunAdapter:
    def __init__(self) -> None:
        self.sent: list[Intent] = []
        self.decisions: list[SafetyDecision] = []

    def apply(self, intent: Intent, **safety_kwargs) -> SafetyDecision:
        decision = supervise(intent, **safety_kwargs)
        self.decisions.append(decision)
        if decision.allow:
            self.sent.append(intent)
        return decision
