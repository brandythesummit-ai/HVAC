"""Unit tests for the lead state machine.

The state machine is correctness-critical: it decides what happens
to each lead after a door-knock. Invalid transitions corrupt the
workflow; incorrect cooldown math means leads resurface at the
wrong time (too early = annoying, too late = missed follow-up).
"""
from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time

from app.services.lead_status_machine import (
    COOLDOWN_STATUSES,
    GHL_PUSH_TRANSITIONS,
    STATUSES,
    VALID_TRANSITIONS,
    InvalidTransitionError,
    compute_transition,
    is_cooldown_expired,
    is_valid_transition,
)

DEFAULT_COOLDOWNS = {
    "KNOCKED_NO_ANSWER": 7,
    "KNOCKED_NOT_INTERESTED": 180,
}


class TestStatusesList:
    def test_all_ten_statuses_defined(self):
        assert len(STATUSES) == 10

    def test_all_statuses_are_uppercase(self):
        for s in STATUSES:
            assert s == s.upper()

    def test_every_status_has_entry_in_valid_transitions(self):
        for s in STATUSES:
            assert s in VALID_TRANSITIONS, f"{s} missing from VALID_TRANSITIONS"


class TestIsValidTransition:
    def test_new_to_interested_valid(self):
        assert is_valid_transition("NEW", "INTERESTED") is True

    def test_new_to_won_invalid(self):
        # Can't skip knocking + appointment + quote
        assert is_valid_transition("NEW", "WON") is False

    def test_same_status_is_valid_idempotent(self):
        assert is_valid_transition("NEW", "NEW") is True
        assert is_valid_transition("INTERESTED", "INTERESTED") is True

    def test_terminal_statuses_have_no_exits(self):
        # KNOCKED_WRONG_PERSON, WON, LOST — nowhere to go
        assert is_valid_transition("WON", "QUOTED") is False
        assert is_valid_transition("LOST", "NEW") is False
        assert is_valid_transition("KNOCKED_WRONG_PERSON", "NEW") is False

    def test_unknown_from_status_invalid(self):
        assert is_valid_transition("UNKNOWN", "NEW") is False

    def test_cooldown_recovery_to_new_valid(self):
        # The cron that expires cooldowns transitions KNOCKED_* → NEW
        assert is_valid_transition("KNOCKED_NO_ANSWER", "NEW") is True
        assert is_valid_transition("KNOCKED_NOT_INTERESTED", "NEW") is True


class TestComputeTransitionValid:
    @freeze_time("2026-04-22 18:00:00")
    def test_new_to_knocked_not_interested_sets_180_day_cooldown(self):
        result = compute_transition("NEW", "KNOCKED_NOT_INTERESTED",
                                      DEFAULT_COOLDOWNS)
        assert result.new_status == "KNOCKED_NOT_INTERESTED"
        # 180 days from 2026-04-22 18:00 UTC = 2026-10-19 18:00 UTC
        expected = datetime(2026, 10, 19, 18, 0, 0, tzinfo=timezone.utc)
        assert result.resurface_after == expected
        # This transition doesn't push to GHL
        assert result.should_push_to_ghl is False

    @freeze_time("2026-04-22 18:00:00")
    def test_new_to_knocked_no_answer_sets_7_day_cooldown(self):
        result = compute_transition("NEW", "KNOCKED_NO_ANSWER", DEFAULT_COOLDOWNS)
        expected = datetime(2026, 4, 29, 18, 0, 0, tzinfo=timezone.utc)
        assert result.resurface_after == expected

    def test_new_to_interested_triggers_ghl_push(self):
        result = compute_transition("NEW", "INTERESTED", DEFAULT_COOLDOWNS)
        assert result.new_status == "INTERESTED"
        assert result.should_push_to_ghl is True
        assert result.resurface_after is None  # not a cooldown status

    def test_non_cooldown_status_has_no_resurface(self):
        result = compute_transition("INTERESTED", "APPOINTMENT_SET",
                                      DEFAULT_COOLDOWNS)
        assert result.resurface_after is None

    def test_transition_clears_prior_resurface(self):
        # Moving out of a cooldown status back to NEW: resurface_after
        # must be explicitly None to clear the DB field.
        result = compute_transition("KNOCKED_NOT_INTERESTED", "NEW",
                                      DEFAULT_COOLDOWNS)
        assert result.resurface_after is None
        assert result.to_update_dict()["resurface_after"] is None

    def test_to_update_dict_has_all_required_fields(self):
        result = compute_transition("NEW", "INTERESTED", DEFAULT_COOLDOWNS)
        d = result.to_update_dict()
        assert "lead_status" in d
        assert "status_changed_at" in d
        assert "resurface_after" in d
        # ISO string, not datetime
        assert isinstance(d["status_changed_at"], str)


class TestComputeTransitionInvalid:
    def test_new_to_won_raises(self):
        with pytest.raises(InvalidTransitionError):
            compute_transition("NEW", "WON", DEFAULT_COOLDOWNS)

    def test_terminal_to_anywhere_raises(self):
        for from_status in ("WON", "LOST", "KNOCKED_WRONG_PERSON"):
            for to_status in ("NEW", "INTERESTED", "APPOINTMENT_SET"):
                with pytest.raises(InvalidTransitionError):
                    compute_transition(from_status, to_status, DEFAULT_COOLDOWNS)

    def test_missing_cooldown_config_raises(self):
        # Empty cooldown config + cooldown-requiring target → ValueError
        with pytest.raises(ValueError, match="Cooldown days missing"):
            compute_transition("NEW", "KNOCKED_NOT_INTERESTED", {})


class TestGhlPushTrigger:
    def test_all_ghl_push_pairs_are_valid_transitions(self):
        for from_s, to_s in GHL_PUSH_TRANSITIONS:
            assert is_valid_transition(from_s, to_s), (
                f"GHL push transition {from_s}→{to_s} isn't a valid transition"
            )

    def test_interested_from_any_knock_triggers_push(self):
        for from_status in ("NEW", "KNOCKED_NO_ANSWER",
                              "KNOCKED_SPOKE_TO_NON_DM", "KNOCKED_NOT_INTERESTED"):
            result = compute_transition(from_status, "INTERESTED", DEFAULT_COOLDOWNS)
            assert result.should_push_to_ghl is True, f"{from_status}→INTERESTED didn't push"

    def test_won_triggers_final_push(self):
        result = compute_transition("QUOTED", "WON", DEFAULT_COOLDOWNS)
        assert result.should_push_to_ghl is True


class TestIsCooldownExpired:
    @freeze_time("2026-04-22 18:00:00")
    def test_future_resurface_not_expired(self):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        assert is_cooldown_expired("KNOCKED_NOT_INTERESTED", future) is False

    @freeze_time("2026-04-22 18:00:00")
    def test_past_resurface_is_expired(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        assert is_cooldown_expired("KNOCKED_NOT_INTERESTED", past) is True

    def test_none_resurface_not_expired(self):
        assert is_cooldown_expired("KNOCKED_NOT_INTERESTED", None) is False

    def test_non_cooldown_status_never_expired(self):
        past = datetime.now(timezone.utc) - timedelta(days=100)
        # Even if timestamp is way past, non-cooldown status returns False
        assert is_cooldown_expired("INTERESTED", past) is False

    @freeze_time("2026-04-22 18:00:00")
    def test_naive_datetime_coerced_to_utc(self):
        naive_past = datetime(2026, 4, 21, 18, 0, 0)  # no tzinfo
        assert is_cooldown_expired("KNOCKED_NOT_INTERESTED", naive_past) is True
