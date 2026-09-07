"""Tests for the Smart Cooking event log parser."""

from safera_sense_ble import CookingEventType, parse_event_log


def test_parse_captured_timeline() -> None:
    # Real capture: FRYING_START + COOKING_START at the same device clock.
    raw = bytes.fromhex("0200037e667000017e667000")
    events = parse_event_log(raw)
    assert len(events) == 2
    assert events[0].event_type == CookingEventType.FRYING_START
    assert events[1].event_type == CookingEventType.COOKING_START
    assert events[0].timestamp == 0x0070667E
    assert events[0].name == "frying_start"


def test_empty_log() -> None:
    assert parse_event_log(bytes.fromhex("0000")) == []
    assert parse_event_log(b"") == []


def test_truncated_entry_is_ignored() -> None:
    # Declares 2 events but only one full entry follows.
    raw = bytes.fromhex("0200037e667000")
    events = parse_event_log(raw)
    assert len(events) == 1
    assert events[0].event_type == CookingEventType.FRYING_START


def test_unknown_code_gets_placeholder_name() -> None:
    raw = bytes.fromhex("01002a00000000")  # type 0x2a = 42, unknown
    events = parse_event_log(raw)
    assert events[0].name == "event_42"


def test_negative_event_type() -> None:
    raw = bytes.fromhex("0100ff00000000")  # 0xff signed = -1 = ROUTINE
    events = parse_event_log(raw)
    assert events[0].event_type == CookingEventType.ROUTINE
    assert events[0].name == "routine"
