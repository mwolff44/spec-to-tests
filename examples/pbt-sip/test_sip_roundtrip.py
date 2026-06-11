"""Round-trip property tests for sip_message.py.

Reference properties:
- parse(format(msg)) == msg          (round-trip — the canonical PBT property)
- Adding a header increases length   (invariant — sanity check)
- format() always ends with CRLFCRLF (structural invariant)

Example-based tests (also present) cover the happy path.
Hypothesis covers everything else — including the asymmetry bug in parse().
"""
from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from sip_message import CRLF, ParseError, SipRequest, parse


# --- Strategies --------------------------------------------------------------

METHODS = st.sampled_from(["INVITE", "ACK", "BYE", "CANCEL", "OPTIONS", "REGISTER"])

token = st.text(
    alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E,
                           blacklist_characters=':@ \t"<>'),
    min_size=1,
    max_size=20,
)

uri = st.builds(lambda u, h: f"sip:{u}@{h}.example.com", token, token)

header_name = st.text(
    alphabet=st.characters(min_codepoint=0x41, max_codepoint=0x7A,
                           whitelist_categories=("L",)),
    min_size=1, max_size=16,
)

# Permissive header value: ASCII printable except CR/LF.
# Composite to give the generator a fair chance of producing values whose
# *boundaries* are whitespace — that's where the round-trip bug hides.
_inner = st.text(
    alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
    min_size=0, max_size=30,
)


@st.composite
def header_value_strat(draw):
    prefix = draw(st.sampled_from(["", " ", "  "]))
    suffix = draw(st.sampled_from(["", " "]))
    return prefix + draw(_inner) + suffix


header_value = header_value_strat()

headers_strategy = st.dictionaries(header_name, header_value, max_size=8)


@st.composite
def sip_requests(draw):
    return SipRequest(
        method=draw(METHODS),
        uri=draw(uri),
        version="SIP/2.0",
        headers=draw(headers_strategy),
    )


# --- Example-based tests (the easy ones) ------------------------------------

def test_invite_roundtrip_happy_path():
    msg = SipRequest(
        method="INVITE",
        uri="sip:bob@example.com",
        version="SIP/2.0",
        headers={"From": "<sip:alice@example.com>", "Call-ID": "abc123"},
    )
    assert parse(msg.format()) == msg


def test_parse_missing_separator():
    with pytest.raises(ParseError):
        parse("INVITE sip:x@y SIP/2.0\r\n")  # no blank line


# --- Property-based tests ---------------------------------------------------

@given(sip_requests())
@settings(max_examples=500)
def test_format_then_parse_is_identity(msg):
    """parse(format(msg)) == msg — the canonical round-trip."""
    text = msg.format()
    parsed = parse(text)
    assert parsed == msg


@given(sip_requests())
def test_format_ends_with_blank_line(msg):
    text = msg.format()
    assert text.endswith(CRLF + CRLF)


@given(sip_requests(), header_name, header_value)
def test_adding_header_increases_header_count(msg, name, value):
    # Avoid colliding with an existing header
    if name in msg.headers:
        msg.headers[name] = value
        assert name in msg.headers
        return
    before = len(msg.headers)
    msg.headers[name] = value
    assert len(msg.headers) == before + 1
