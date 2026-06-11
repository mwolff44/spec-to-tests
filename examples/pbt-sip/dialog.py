"""Minimal SIP dialog FSM — illustrative.

States: EARLY → CONFIRMED → TERMINATED

Allowed transitions (per RFC 3261, simplified):
- EARLY:      receive_provisional, receive_2xx, receive_failure, send_cancel
- CONFIRMED:  send_ack (once), send_reinvite, send_bye, receive_bye
- TERMINATED: nothing

Intentional bug for the PBT demo: see `receive_cancel` — a CANCEL is accepted
after the dialog has been CONFIRMED. RFC 3261 §9.2 says CANCEL has no meaning
once the final response is received. Hypothesis stateful testing finds this
via the sequence: receive_2xx, send_ack, receive_cancel.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto


class State(Enum):
    EARLY = auto()
    CONFIRMED = auto()
    TERMINATED = auto()


class DialogError(RuntimeError):
    pass


@dataclass
class Dialog:
    call_id: str
    state: State = State.EARLY
    ack_sent: bool = False

    def receive_provisional(self) -> None:
        if self.state is not State.EARLY:
            raise DialogError(f"provisional in state {self.state.name}")

    def receive_2xx(self) -> None:
        if self.state is not State.EARLY:
            raise DialogError(f"2xx in state {self.state.name}")
        self.state = State.CONFIRMED

    def receive_failure(self) -> None:
        if self.state is not State.EARLY:
            raise DialogError(f"failure in state {self.state.name}")
        self.state = State.TERMINATED

    def send_ack(self) -> None:
        if self.state is not State.CONFIRMED:
            raise DialogError(f"ACK in state {self.state.name}")
        if self.ack_sent:
            raise DialogError("ACK already sent")
        self.ack_sent = True

    def send_bye(self) -> None:
        if self.state is not State.CONFIRMED:
            raise DialogError(f"BYE in state {self.state.name}")
        if not self.ack_sent:
            raise DialogError("BYE before ACK")
        self.state = State.TERMINATED

    def receive_bye(self) -> None:
        if self.state is not State.CONFIRMED:
            raise DialogError(f"receive BYE in state {self.state.name}")
        self.state = State.TERMINATED

    def receive_cancel(self) -> None:
        # BUG: per RFC 3261 §9.2, CANCEL must be ignored once the final
        # response has been received (i.e. state CONFIRMED or TERMINATED).
        # This implementation accepts CANCEL in any state and forces TERMINATED.
        self.state = State.TERMINATED

    @property
    def is_active(self) -> bool:
        return self.state is not State.TERMINATED
