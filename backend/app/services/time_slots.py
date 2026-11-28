"""Custom exam timings (time slots) of an exam center.

A slot replaces three timetable columns on the admit card - उपकेंद्रावरील
उपस्थिती (reporting), परीक्षा कक्षातील शेवटच्या प्रवेशाची वेळ (last_entry) and
परीक्षेचा प्रत्यक्ष कालावधी (duration) - in every exam-date row. Everything
else on the card still comes from ticket_template/config.json, and a student
without a slot gets config.json's timing exactly as before.

An admit card stores a copy of its timing (HallTicket.timing_*), taken when
the card is generated or when the student is moved to another slot, so
editing a slot later only affects cards generated afterwards."""

from app.models import ExamCenterTimeSlot, HallTicket
from app.services.pdf_generator import TIMING_FIELDS, TicketConfig
from app.validators import clean_name

TIMING_MAX_LENGTH = 40


def default_timing(config: TicketConfig) -> dict[str, str]:
    """The timing printed when a student has no slot (config.json's first
    timetable row - every row has the same times). Line breaks inside a
    cell become spaces, the way an admin would type them."""
    first = config.schedule[0] if config.schedule else {}
    return {f: clean_name(str(first.get(f, "") or "")) for f in TIMING_FIELDS}


def slot_timing(slot: ExamCenterTimeSlot | None) -> dict[str, str] | None:
    if slot is None:
        return None
    return {f: getattr(slot, f) for f in TIMING_FIELDS}


def ticket_timing(ticket: HallTicket) -> dict[str, str] | None:
    """The custom timing printed on this card, or None for the default."""
    timing = {
        "reporting": ticket.timing_reporting,
        "last_entry": ticket.timing_last_entry,
        "duration": ticket.timing_duration,
    }
    return timing if all(timing.values()) else None


def set_ticket_timing(ticket: HallTicket, slot: ExamCenterTimeSlot | None) -> None:
    """Copies `slot`'s timing onto the card (None = back to default timing)."""
    timing = slot_timing(slot) or {}
    ticket.timing_reporting = timing.get("reporting")
    ticket.timing_last_entry = timing.get("last_entry")
    ticket.timing_duration = timing.get("duration")


def timing_label(timing: dict[str, str] | None) -> str:
    """One-line description for upload results and change lists."""
    if not timing:
        return "Default timing"
    return " / ".join(timing[f] for f in TIMING_FIELDS)


def validate_timing(reporting: str, last_entry: str, duration: str) -> tuple[dict[str, str], dict[str, str]]:
    """Returns (clean_values, field_errors)."""
    values = {"reporting": clean_name(reporting), "last_entry": clean_name(last_entry), "duration": clean_name(duration)}
    errors: dict[str, str] = {}
    for field_name, value in values.items():
        if not value:
            errors[field_name] = "This field is required."
        elif len(value) > TIMING_MAX_LENGTH:
            errors[field_name] = f"Must be at most {TIMING_MAX_LENGTH} characters."
    return values, errors
