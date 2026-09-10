from fastapi import HTTPException
from sqlalchemy import select, or_, delete, func
from app.models.entities import User, Driver, Truck, Route, DelayReason, Trip, SessionToken
from app.repositories.records import get, public
from app.core.security import hash_password
from app.services.audit import audit

MODELS = {'users':User, 'drivers':Driver, 'trucks':Truck, 'routes':Route, 'delay-reasons':DelayReason}


def save(db, resource, data, actor, request, ident=None):
    model = MODELS[resource]
    obj = get(db, model, ident) if ident else None
    old = public(obj) if obj else None
    values = data.model_dump()
    open_trips = select(Trip).where(Trip.status.not_in(['COMPLETED','CANCELLED']))
    if obj:
        relation = {'trucks':Trip.truck_id == ident, 'drivers':Trip.driver_id == ident,
                    'routes':or_(Trip.route_id == ident, Trip.return_route_id == ident)}
        if resource in relation and db.scalar(open_trips.where(relation[resource])):
            raise HTTPException(409, 'Complete or cancel the open trip before editing this record')
    if resource == 'users':
        values['username'] = values['username'].lower()
        password = values.pop('password')
        if not obj and not password:
            raise HTTPException(422, 'Password is required for a new user')
        if password:
            values['password_hash'] = hash_password(password)
        if obj:
            driver = db.scalar(select(Driver).where(Driver.user_id == obj.id))
            if driver and values['role'] != 'DRIVER':
                raise HTTPException(409, 'A linked driver account must retain the DRIVER role')
            if driver and not values['is_active'] and db.scalar(open_trips.where(Trip.driver_id == driver.id)):
                raise HTTPException(409, 'Account has an open trip')
            if obj.id == actor.id and (not values['is_active'] or values['role'] != 'ADMIN'):
                raise HTTPException(409, 'You cannot deactivate or demote your own admin account')
            if password or obj.role != values['role'] or not values['is_active']:
                db.execute(delete(SessionToken).where(SessionToken.user_id == obj.id))
    if resource == 'drivers':
        user = get(db, User, values['user_id'])
        if user.role != 'DRIVER' or (values['status'] == 'ACTIVE' and not user.is_active):
            raise HTTPException(422, 'Choose an active DRIVER account')
        if obj and obj.user_id != values['user_id']:
            raise HTTPException(409, 'A driver account association is immutable; create a new driver instead')
    if resource == 'trucks':
        values['registration_number'] = values['registration_number'].upper().replace(' ', '')
        values['truck_code'] = values['truck_code'].upper()
        if values['assigned_driver_id']:
            driver = get(db, Driver, values['assigned_driver_id'])
            user = get(db, User, driver.user_id)
            if driver.status != 'ACTIVE' or not user.is_active:
                raise HTTPException(422, 'Assigned driver must be active')
    if obj is None:
        obj = model(**values)
        db.add(obj)
    else:
        for key, value in values.items():
            setattr(obj, key, value)
    db.flush()
    audit(db, actor, 'UPDATE' if ident else 'CREATE', resource, obj.id, old, public(obj), request)
    return public(obj)
