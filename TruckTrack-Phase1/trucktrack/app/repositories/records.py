from datetime import date, datetime
from fastapi import HTTPException
from sqlalchemy import select, inspect
from app.models.entities import Driver, TripEvent, EventCorrection
from app.services.time_engine import aware, iso


def get(db, model, ident):
    obj = db.get(model, ident)
    if obj is None:
        raise HTTPException(404, f'{model.__name__} not found')
    return obj


def public(obj):
    result = {}
    for attr in inspect(type(obj)).column_attrs:
        if attr.key in ('password_hash', 'token_hash', 'csrf'):
            continue
        value = getattr(obj, attr.key)
        result[attr.key] = iso(value) if isinstance(value, datetime) else value.isoformat() if isinstance(value, date) else value
    return result


def own_driver(db, user):
    return db.scalar(select(Driver).where(Driver.user_id == user.id))


def effective_events(db, trip_id):
    events = list(db.scalars(select(TripEvent).where(TripEvent.trip_id == trip_id).order_by(TripEvent.id)))
    result = []
    for event in events:
        item = public(event)
        corrections = list(db.scalars(select(EventCorrection).where(EventCorrection.event_id == event.id).order_by(EventCorrection.id)))
        item['original_time'] = iso(event.event_time)
        item['event_time'] = iso(corrections[-1].new_time if corrections else event.event_time)
        item['corrections'] = [public(c) for c in corrections]
        result.append(item)
    return result
