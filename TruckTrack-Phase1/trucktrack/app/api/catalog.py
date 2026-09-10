from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import User, Driver, Truck, Route, DelayReason, AuditLog, Setting
from app.schemas.requests import UserInput, DriverInput, TruckInput, RouteInput, ReasonInput, SettingsInput
from app.api.dependencies import admin, management, current_user
from app.repositories.records import public, get, own_driver
from app.services.catalog import save, MODELS
from app.services.audit import audit

router = APIRouter(prefix='/api', tags=['Administration'])

# Each factory closure gives FastAPI the actual Pydantic schema (including OpenAPI).
def register(resource, schema):
    model = MODELS[resource]
    permission = admin if resource == 'users' else current_user
    def listing(user=Depends(permission), db: Session=Depends(get_db, scope='function')):
        statement = select(model).order_by(model.id)
        if user.role == 'DRIVER':
            driver = own_driver(db, user)
            if resource == 'drivers':
                statement = statement.where(model.id == (driver.id if driver else -1))
            elif resource == 'trucks':
                statement = statement.where(model.assigned_driver_id == (driver.id if driver else -1))
            elif resource in ('routes','delay-reasons'):
                statement = statement.where(model.is_active.is_(True))
        return [public(x) for x in db.scalars(statement)]
    def detail(ident: int, user=Depends(permission), db: Session=Depends(get_db, scope='function')):
        items = listing(user, db)
        from fastapi import HTTPException
        found = next((x for x in items if x['id'] == ident), None)
        if found is None:
            raise HTTPException(404, 'Record not found')
        return found
    def create(data: schema, request: Request, user=Depends(admin), db: Session=Depends(get_db, scope='function')):
        return save(db, resource, data, user, request)
    def update(ident: int, data: schema, request: Request, user=Depends(admin), db: Session=Depends(get_db, scope='function')):
        return save(db, resource, data, user, request, ident)
    def deactivate(ident: int, request: Request, user=Depends(admin), db: Session=Depends(get_db, scope='function')):
        obj = get(db, model, ident)
        values = {k:getattr(obj,k) for k in schema.model_fields if hasattr(obj,k)}
        if 'status' in values:
            values['status'] = 'INACTIVE'
        else:
            values['is_active'] = False
        return save(db, resource, schema(**values), user, request, ident)
    for path, endpoint, methods in [(f'/{resource}',listing,['GET']), (f'/{resource}/{{ident}}',detail,['GET']),
                                   (f'/{resource}',create,['POST']), (f'/{resource}/{{ident}}',update,['PUT']),
                                   (f'/{resource}/{{ident}}',deactivate,['DELETE'])]:
        endpoint.__name__ = resource.replace('-','_') + '_' + endpoint.__name__
        router.add_api_route(path, endpoint, methods=methods)

for resource, schema in [('users',UserInput),('drivers',DriverInput),('trucks',TruckInput),('routes',RouteInput),('delay-reasons',ReasonInput)]:
    register(resource,schema)

@router.get('/settings')
def settings(user=Depends(management), db: Session=Depends(get_db, scope='function')):
    return public(get(db, Setting, 1))

@router.put('/settings')
def update_settings(data: SettingsInput, request: Request, user=Depends(admin), db: Session=Depends(get_db, scope='function')):
    obj = get(db, Setting, 1)
    old = public(obj)
    for key,value in data.model_dump().items():
        setattr(obj,key,value)
    audit(db,user,'UPDATE','settings',1,old,public(obj),request)
    return public(obj)

@router.get('/audit')
def audit_history(entity_id: int | None=None, offset: int=0, limit: int=100, user=Depends(admin), db: Session=Depends(get_db, scope='function')):
    from fastapi import HTTPException
    if offset < 0 or not 1 <= limit <= 500:
        raise HTTPException(422,'Invalid pagination')
    statement = select(AuditLog).order_by(AuditLog.id.desc())
    if entity_id is not None:
        statement = statement.where(AuditLog.entity_id == entity_id)
    return [public(a) for a in db.scalars(statement.offset(offset).limit(limit))]
