"""Minimal SIP request parser/formatter — illustrative, not RFC-complete.

Scope: request-line + headers + empty body. No multi-value headers, no folding.

Intentional bug for the PBT demo: see `parse()` — header value handling
loses information on certain inputs. Hypothesis finds this in seconds.
"""
from __future__ import annotations
from dataclasses import dataclass, field

CRLF = "\r\n"


@dataclass
class SipRequest:
    method: str
    uri: str
    version: str
    headers: dict[str, str] = field(default_factory=dict)

    def format(self) -> str:
        lines = [f"{self.method} {self.uri} {self.version}"]
        for name, value in self.headers.items():
            lines.append(f"{name}: {value}")
        return CRLF.join(lines) + CRLF + CRLF


class ParseError(ValueError):
    pass


def parse(text: str) -> SipRequest:
    if CRLF + CRLF not in text:
        raise ParseError("missing CRLF CRLF separator")

    head, _ = text.split(CRLF + CRLF, 1)
    lines = head.split(CRLF)
    if not lines:
        raise ParseError("empty request")

    request_line = lines[0]
    parts = request_line.split(" ", 2)
    if len(parts) != 3:
        raise ParseError(f"invalid request line: {request_line!r}")
    method, uri, version = parts

    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" not in line:
            raise ParseError(f"invalid header line: {line!r}")
        name, value = line.split(":", 1)
        # BUG: strip() removes ALL leading/trailing whitespace, but format()
        # only adds a single space after the colon. Any whitespace at the
        # boundaries of the original value is silently lost on the round-trip.
        # Hypothesis finds this within seconds once the strategy can produce
        # values that start or end with a space.
        headers[name] = value.strip()

    return SipRequest(method=method, uri=uri, version=version, headers=headers)
