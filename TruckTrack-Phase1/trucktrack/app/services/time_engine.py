"""Pure time/state rules shared by services and dependency-free unit tests."""
from datetime import datetime, timezone

EVENTS = ('ORIGIN_DEPARTURE', 'DESTINATION_ARRIVAL', 'DESTINATION_DEPARTURE', 'ORIGIN_ARRIVAL')
STATES = ('SCHEDULED', 'OUTBOUND', 'AT_DESTINATION', 'RETURNING', 'COMPLETED')


def utcnow():
    return datetime.now(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def iso(value):
    return aware(value).isoformat() if value else None


def travel(start, end, expected, tolerance):
    if start is None:
        return {'actual_minutes': None, 'delay_minutes': 0, 'status': 'NOT_STARTED', 'expected_minutes': expected, 'tolerance_minutes': tolerance}
    minutes = max(0, (aware(end or utcnow()) - aware(start)).total_seconds() / 60)
    return {'actual_minutes': round(minutes, 2), 'delay_minutes': round(max(0, minutes - expected), 2),
            'status': 'DELAYED' if minutes > expected + tolerance else 'ON_TIME',
            'expected_minutes': expected, 'tolerance_minutes': tolerance}


def validate_sequence(existing, event_type, event_time):
    if len(existing) >= 4 or EVENTS[len(existing)] != event_type:
        raise ValueError('Duplicate or invalid event sequence')
    if existing and aware(event_time) < aware(existing[-1]):
        raise ValueError('Event time cannot precede the previous event')


def validate_correction(times, index, value, now=None):
    value = aware(value)
    if value > aware(now or utcnow()):
        raise ValueError('Event time cannot be in the future')
    amended = list(times)
    amended[index] = value
    if any(aware(a) > aware(b) for a, b in zip(amended, amended[1:])):
        raise ValueError('Correction would break chronological order')
    return amended
