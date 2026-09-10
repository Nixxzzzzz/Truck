from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.dependencies import current_user, admin, roles
from app.database.session import get_db
from app.models.entities import Trip
from app.schemas.requests import TripInput, EventInput, CorrectionInput, MissingInput, DelayInput, CancelInput, IdentifyInput
from app.repositories.records import own_driver, public
from app.services import trips as service
from app.services.audit import audit

router=APIRouter(prefix='/api/trips',tags=['Trips'])

@router.get('')
def listing(start: date | None=None,end: date | None=None,truck_id: int | None=None,driver_id: int | None=None,
            status: str | None=None,offset: int=Query(0,ge=0),limit: int=Query(100,ge=1,le=500),
            user=Depends(current_user),db: Session=Depends(get_db, scope='function')):
    if start and end and start>end:
        raise HTTPException(422,'Start date must precede end date')
    statement=select(Trip).order_by(Trip.trip_date.desc(),Trip.id.desc())
    if user.role=='DRIVER':
        driver=own_driver(db,user)
        statement=statement.where(Trip.driver_id==(driver.id if driver else -1))
    for field,value in [(Trip.truck_id,truck_id),(Trip.driver_id,driver_id),(Trip.status,status)]:
        if value is not None:
            statement=statement.where(field==value)
    if start:
        statement=statement.where(Trip.trip_date>=start)
    if end:
        statement=statement.where(Trip.trip_date<=end)
    return [service.describe(db,t) for t in db.scalars(statement.offset(offset).limit(limit))]

@router.post('',status_code=201)
def create(data: TripInput,request: Request,user=Depends(admin),db: Session=Depends(get_db, scope='function')):
    return service.create_trip(db,data,user,request)

@router.get('/{ident}')
def detail(ident:int,user=Depends(current_user),db: Session=Depends(get_db, scope='function')):
    return service.describe(db,service.accessible(db,ident,user))

@router.post('/{ident}/identify')
def identify(ident:int,data:IdentifyInput,user=Depends(roles('DRIVER','ADMIN')),db:Session=Depends(get_db, scope='function')):
    trip=service.accessible(db,ident,user)
    truck,driver=service.verify_assignment(db,trip,data.truck_code)
    return {'truck':public(truck),'driver':public(driver),'assignment':f'{trip.origin} → {trip.destination}',
            'verification_method':'TRUCK_CODE','notice':'Code and assignment verified; physical presence is not verified.'}

@router.post('/{ident}/events',status_code=201)
def event(ident:int,data:EventInput,request:Request,user=Depends(roles('DRIVER')),db:Session=Depends(get_db, scope='function')):
    return service.punch(db,service.accessible(db,ident,user,True),data,user,request)

@router.post('/{ident}/events/missing',status_code=201)
def missing(ident:int,data:MissingInput,request:Request,user=Depends(admin),db:Session=Depends(get_db, scope='function')):
    return service.punch(db,service.accessible(db,ident,user,True),data,user,request,correction=True)

@router.post('/{ident}/events/{event_id}/corrections',status_code=201)
def correction(ident:int,event_id:int,data:CorrectionInput,request:Request,user=Depends(admin),db:Session=Depends(get_db, scope='function')):
    return service.correct(db,service.accessible(db,ident,user,True),event_id,data,user,request)

@router.post('/{ident}/delay')
def delay(ident:int,data:DelayInput,request:Request,user=Depends(roles('DRIVER','ADMIN')),db:Session=Depends(get_db, scope='function')):
    return service.report_delay(db,service.accessible(db,ident,user,True),data,user,request)

@router.post('/{ident}/cancel')
def cancel(ident:int,data:CancelInput,request:Request,user=Depends(admin),db:Session=Depends(get_db, scope='function')):
    trip=service.accessible(db,ident,user,True)
    if trip.status!='SCHEDULED':
        raise HTTPException(409,'Only an unstarted scheduled trip may be cancelled')
    old=public(trip)
    trip.status='CANCELLED'
    audit(db,user,'CANCEL','trips',trip.id,old,{'status':'CANCELLED','reason':data.reason},request)
    return service.describe(db,trip)
