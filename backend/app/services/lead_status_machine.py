"""Lead status state machine for the door-knock workflow.

Implements the transitions from docs/design/2026-04-21-post-pivot-design.md
§4. The state machine:
  - Validates transitions (can't jump from NEW directly to WON).
  - Sets resurface_after for cooldown statuses.
  - Flags INTERESTED transitions as GHL-push-worthy (the router acts on
    that flag, not this module — separation of concerns).

All transitions are idempotent within the same status: setting status
to its current value is a no-op but still updates status_changed_at
for audit trail.

Time-dependence: cooldown math uses UTC everywhere. Tests use
freezegun to pin time.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

# Statuses. Must match the CHECK constraint in migration 025.
STATUSES = (
    "NEW",
    "KNOCKED_NO_ANSWER",
    "KNOCKED_SPOKE_TO_NON_DM",
    "KNOCKED_WRONG_PERSON",
    "KNOCKED_NOT_INTERESTED",
    "INTERESTED",
    "APPOINTMENT_SET",
    "QUOTED",
    "WON",
    "LOST",
)

# Valid transitions: {from_status: frozenset of allowed to_statuses}.
# Any unlisted (from, to) pair is rejected.
VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "NEW": frozenset({
        "KNOCKED_NO_ANSWER",
        "KNOCKED_SPOKE_TO_NON_DM",
        "KNOCKED_WRONG_PERSON",
        "KNOCKED_NOT_INTERESTED",
        "INTERESTED",
    }),
    "KNOCKED_NO_ANSWER": frozenset({
        "NEW",  # manual reset or cooldown expired
        "KNOCKED_SPOKE_TO_NON_DM",  # second attempt got someone
        "KNOCKED_WRONG_PERSON",
        "KNOCKED_NOT_INTERESTED",
        "INTERESTED",
    }),
    "KNOCKED_SPOKE_TO_NON_DM": frozenset({
        "NEW",
        "KNOCKED_NO_ANSWER",
        "KNOCKED_WRONG_PERSON",
        "KNOCKED_NOT_INTERESTED",
        "INTERESTED",
    }),
    "KNOCKED_WRONG_PERSON": frozenset(),  # terminal — removed from rotation
    "KNOCKED_NOT_INTERESTED": frozenset({
        "NEW",  # cooldown expired
        "INTERESTED",  # manual override if they change their mind
    }),
    "INTERESTED": frozenset({
        "APPOINTMENT_SET",
        "LOST",
    }),
    "APPOINTMENT_SET": frozenset({
        "QUOTED",
        "LOST",
    }),
    "QUOTED": frozenset({
        "WON",
        "LOST",
    }),
    "WON": frozenset(),  # terminal
    "LOST": frozenset(),  # terminal
}

# Statuses that trigger a cooldown (resurface_after timestamp).
# The days value is read from the lead_status_cooldowns table; these
# are the defaults M11 seeded.
COOLDOWN_STATUSES = frozenset({"KNOCKED_NO_ANSWER", "KNOCKED_NOT_INTERESTED"})

# Transitions that should trigger a GHL push event.
GHL_PUSH_TRANSITIONS = frozenset({
    # (from_status, to_status) tuples. INTERESTED is the primary push
    # trigger (creates Contact + Opportunity). Later stages update the
    # existing Opportunity.
    ("NEW", "INTERESTED"),
    ("KNOCKED_NO_ANSWER", "INTERESTED"),
    ("KNOCKED_SPOKE_TO_NON_DM", "INTERESTED"),
    ("KNOCKED_NOT_INTERESTED", "INTERESTED"),
    ("INTERESTED", "APPOINTMENT_SET"),
    ("APPOINTMENT_SET", "QUOTED"),
    ("QUOTED", "WON"),
    ("QUOTED", "LOST"),
})


class InvalidTransitionError(ValueError):
    """Raised when an attempted transition isn't in VALID_TRANSITIONS."""


@dataclass
class TransitionResult:
    """What changed + what side effects to trigger."""
    new_status: str
    status_changed_at: datetime
    resurface_after: Optional[datetime]
    should_push_to_ghl: bool

    def to_update_dict(self) -> dict:
        # Shape that can be fed directly to Supabase .update().
        out: dict = {
            "lead_status": self.new_status,
            "status_changed_at": self.status_changed_at.isoformat(),
        }
        # Explicitly set resurface_after (None clears it when moving out of cooldown).
        out["resurface_after"] = (
            self.resurface_after.isoformat() if self.resurface_after else None
        )
        return out


def is_valid_transition(from_status: str, to_status: str) -> bool:
    if from_status not in VALID_TRANSITIONS:
        return False
    if from_status == to_status:
        # Idempotent: allow same-to-same (useful for re-push without
        # actually changing state).
        return True
    return to_status in VALID_TRANSITIONS[from_status]


def compute_transition(
    current_status: str,
    new_status: str,
    cooldown_days_by_key: dict[str, int],
    now: Optional[datetime] = None,
) -> TransitionResult:
    """Validate and compute the effects of a status change.

    Args:
        current_status: What the lead is now.
        new_status: The target status.
        cooldown_days_by_key: Map of status → days (from lead_status_cooldowns).
        now: Current time (injectable for tests). Defaults to UTC now.

    Raises:
        InvalidTransitionError: Transition not allowed per VALID_TRANSITIONS.

    Returns:
        TransitionResult with the new status, timestamp, optional
        resurface_after, and should_push_to_ghl flag.
    """
    if not is_valid_transition(current_status, new_status):
        raise InvalidTransitionError(
            f"Cannot transition from {current_status!r} to {new_status!r}"
        )

    if now is None:
        now = datetime.now(timezone.utc)

    resurface_after: Optional[datetime] = None
    if new_status in COOLDOWN_STATUSES:
        days = cooldown_days_by_key.get(new_status)
        if days is None:
            raise ValueError(
                f"Cooldown days missing for status {new_status!r}. "
                f"Check lead_status_cooldowns table."
            )
        resurface_after = now + timedelta(days=days)

    should_push = (current_status, new_status) in GHL_PUSH_TRANSITIONS

    return TransitionResult(
        new_status=new_status,
        status_changed_at=now,
        resurface_after=resurface_after,
        should_push_to_ghl=should_push,
    )


def is_cooldown_expired(
    lead_status: str,
    resurface_after: Optional[datetime],
    now: Optional[datetime] = None,
) -> bool:
    """Check if a cooldowned lead should be resurfaced to NEW.

    Returns True iff the lead is in a cooldown status AND resurface_after
    is set AND resurface_after <= now.
    """
    if lead_status not in COOLDOWN_STATUSES:
        return False
    if resurface_after is None:
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    # resurface_after from DB is tz-aware; cast now too.
    if resurface_after.tzinfo is None:
        resurface_after = resurface_after.replace(tzinfo=timezone.utc)
    return resurface_after <= now
