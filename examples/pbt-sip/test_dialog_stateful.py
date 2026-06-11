"""Stateful PBT for the SIP Dialog FSM.

The RuleBasedStateMachine generates sequences of SIP signaling events and
checks invariants after each step. The interesting bug is *sequence-dependent*:
no single transition is wrong, but the combination receive_2xx → send_ack →
receive_cancel violates the RFC.

A reference model tracks what state we *should* be in. The invariant compares
the implementation to the model.
"""
from __future__ import annotations

from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    precondition,
    rule,
)

from dialog import Dialog, DialogError, State


class DialogMachine(RuleBasedStateMachine):
    """Drive a Dialog through a generated sequence of SIP events."""

    def __init__(self):
        super().__init__()
        self.dialog = Dialog(call_id="test-call")
        # Reference model: minimal subset we care about.
        self.model_state = State.EARLY
        self.model_ack_sent = False
        # Track whether a final response was received — for the CANCEL rule.
        self.final_response_received = False

    # --- transitions ---------------------------------------------------------

    @rule()
    @precondition(lambda self: self.model_state is State.EARLY)
    def receive_provisional(self):
        try:
            self.dialog.receive_provisional()
        except DialogError:
            pass  # never expected here

    @rule()
    @precondition(lambda self: self.model_state is State.EARLY)
    def receive_2xx(self):
        self.dialog.receive_2xx()
        self.model_state = State.CONFIRMED
        self.final_response_received = True

    @rule()
    @precondition(lambda self: self.model_state is State.EARLY)
    def receive_failure(self):
        self.dialog.receive_failure()
        self.model_state = State.TERMINATED
        self.final_response_received = True

    @rule()
    @precondition(
        lambda self: self.model_state is State.CONFIRMED and not self.model_ack_sent
    )
    def send_ack(self):
        self.dialog.send_ack()
        self.model_ack_sent = True

    @rule()
    @precondition(
        lambda self: self.model_state is State.CONFIRMED and self.model_ack_sent
    )
    def send_bye(self):
        self.dialog.send_bye()
        self.model_state = State.TERMINATED

    @rule()
    @precondition(
        lambda self: self.model_state is State.CONFIRMED and self.model_ack_sent
    )
    def receive_bye(self):
        self.dialog.receive_bye()
        self.model_state = State.TERMINATED

    @rule()
    def receive_cancel(self):
        """Per RFC 3261 §9.2, CANCEL only meaningful before final response.

        The model says: CANCEL after final response is a no-op (or error).
        The buggy implementation says: CANCEL always terminates.
        """
        if self.final_response_received:
            # Spec: CANCEL must NOT affect state in this case.
            self.dialog.receive_cancel()  # buggy: this WILL change the state
            # Model stays as-is — no transition.
        else:
            self.dialog.receive_cancel()
            self.model_state = State.TERMINATED

    # --- invariants ----------------------------------------------------------

    @invariant()
    def state_matches_model(self):
        assert self.dialog.state is self.model_state, (
            f"Impl state {self.dialog.state.name} != "
            f"model state {self.model_state.name}"
        )

    @invariant()
    def terminated_is_sticky(self):
        if self.model_state is State.TERMINATED:
            assert not self.dialog.is_active


# Pytest discovers this — Hypothesis generates random sequences and shrinks.
TestDialogMachine = DialogMachine.TestCase
