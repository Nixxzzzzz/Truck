"""Run from the project root: python -m app.cli init-admin | seed-demo."""
import argparse
import getpass
import os
import secrets
from datetime import datetime,timedelta,time
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.entities import User,Driver,Truck,Route,Trip,TripEvent,DelayReason,Delay,Setting,AuditLog
from app.core.security import hash_password
from app.core.config import TIMEZONE
from app.schemas.requests import UserInput
from app.services.time_engine import utcnow,EVENTS

REASONS=['Traffic','Vehicle Breakdown','Loading Delay','Unloading Delay','Road Closure','Accident','Weather','Driver Issue','Fuel Issue','Other']

def base_data(db):
    if not db.get(Setting,1):
        db.add(Setting(id=1))
    for name in REASONS:
        if not db.scalar(select(DelayReason).where(DelayReason.name==name)):
            db.add(DelayReason(name=name,description=name,is_active=True))
    db.flush()


def init_admin():
    with SessionLocal.begin() as db:
        if db.scalar(select(User).where(User.role=='ADMIN')):
            print('An admin already exists. Manage additional users in the application.')
            return
        username=os.getenv('ADMIN_USERNAME') or input('Admin username: ')
        name=os.getenv('ADMIN_NAME') or input('Admin name: ')
        password=os.getenv('ADMIN_PASSWORD') or getpass.getpass('Admin password (12–128 characters): ')
        data=UserInput(username=username,name=name,password=password,role='ADMIN')
        user=User(username=data.username.lower(),name=data.name,password_hash=hash_password(data.password),role='ADMIN',is_active=True)
        db.add(user)
        base_data(db)
        db.flush()
        db.add(AuditLog(user_id=user.id,action='INITIAL_ADMIN',entity_type='users',entity_id=user.id,new_value={'username':user.username}))
    print('Admin created. Start the server and sign in.')


def seed_demo():
    credentials=[]
    with SessionLocal.begin() as db:
        if db.scalar(select(Trip).where(Trip.trip_number.like('DEMO-%'))):
            print('Demo trips already exist; nothing changed.')
            return
        admin=db.scalar(select(User).where(User.role=='ADMIN',User.is_active.is_(True)))
        if not admin:
            raise SystemExit('Run init-admin first.')
        if db.scalar(select(User).where(User.username.in_(['demo.driver','demo.director']))):
            raise SystemExit('Demo usernames already exist. No records changed.')
        if db.scalar(select(Truck).where(Truck.registration_number=='UP16AB1234')):
            raise SystemExit('Demo registration already exists. No records changed.')
        base_data(db)
        users={}
        for role,name in [('DRIVER','Arjun Kumar'),('DIRECTOR','Operations Director')]:
            password=secrets.token_urlsafe(15)
            username='demo.'+role.lower()
            obj=User(username=username,name=name,password_hash=hash_password(password),role=role,is_active=True)
            db.add(obj)
            db.flush()
            users[role]=obj
            credentials.append((username,password))
        driver=Driver(user_id=users['DRIVER'].id,employee_id='DEMO-EMP-001',name='Arjun Kumar',phone='',status='ACTIVE')
        db.add(driver)
        db.flush()
        truck=Truck(registration_number='UP16AB1234',truck_code='TT-001',truck_type='Light commercial vehicle',capacity=3500,status='ACTIVE',assigned_driver_id=driver.id)
        out=Route(origin='Noida HQ',destination='Delhi',expected_duration_minutes=60,allowed_delay_minutes=10,is_active=True)
        back=Route(origin='Delhi',destination='Noida HQ',expected_duration_minutes=70,allowed_delay_minutes=10,is_active=True)
        db.add_all([truck,out,back])
        db.flush()
        zone=ZoneInfo(TIMEZONE)
        today=utcnow().astimezone(zone).date()
        reasons=list(db.scalars(select(DelayReason).order_by(DelayReason.id)))
        for days_ago in range(35,0,-1):
            day=today-timedelta(days=days_ago)
            departure=datetime.combine(day,time(9),tzinfo=zone)
            out_minutes=[58,65,78,62,96,60,69][days_ago%7]
            return_minutes=[70,76,94,68,110,72][days_ago%6]
            times=[departure,departure+timedelta(minutes=out_minutes)]
            times += [times[1]+timedelta(minutes=45),times[1]+timedelta(minutes=45+return_minutes)]
            trip=Trip(trip_number=f'DEMO-{day:%Y%m%d}',truck_id=truck.id,driver_id=driver.id,route_id=out.id,return_route_id=back.id,
                      trip_date=day,scheduled_departure=departure,status='COMPLETED',origin=out.origin,destination=out.destination,
                      outbound_expected=60,outbound_tolerance=10,return_expected=70,return_tolerance=10)
            db.add(trip)
            db.flush()
            for kind,stamp in zip(EVENTS,times):
                db.add(TripEvent(trip_id=trip.id,event_type=kind,event_time=stamp,verification_method='DEMO_SEED',
                                 source='DEMO_SEED',device_id='demo-generator',truck_identity='UP16AB1234 / TT-001',created_by=users['DRIVER'].id))
            for key,minutes,expected in [('OUTBOUND',out_minutes,60),('RETURN',return_minutes,70)]:
                if minutes>expected+10:
                    reason=reasons[days_ago%len(reasons)]
                    db.add(Delay(trip_id=trip.id,route_segment=key,delay_minutes=minutes-expected,reason_id=reason.id,
                                 remarks='Synthetic demonstration record',reported_by=users['DRIVER'].id))
        departure=datetime.combine(today,time(9),tzinfo=zone)
        db.add(Trip(trip_number=f'DEMO-{today:%Y%m%d}',truck_id=truck.id,driver_id=driver.id,route_id=out.id,return_route_id=back.id,
                    trip_date=today,scheduled_departure=departure,status='SCHEDULED',origin=out.origin,destination=out.destination,
                    outbound_expected=60,outbound_tolerance=10,return_expected=70,return_tolerance=10))
        db.add(AuditLog(user_id=admin.id,action='SEED_DEMO',entity_type='system',new_value={'historical_trips':35,'scheduled_trips':1,'synthetic':True}))
    print('Created 35 historical trips and one scheduled trip. Truck code: TT-001')
    print('Save these generated credentials; passwords are not stored in plaintext:')
    for username,password in credentials:
        print(f'{username}: {password}')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['init-admin','seed-demo'])
    args=parser.parse_args()
    init_admin() if args.command=='init-admin' else seed_demo()
