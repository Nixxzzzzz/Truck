"""Full integration suite. Uses an isolated temporary SQLite DB, never user data."""
import importlib.util
import os
import tempfile
from datetime import timedelta
from pathlib import Path
import pytest

for dependency in ['fastapi','sqlalchemy','httpx','dotenv']:
    if importlib.util.find_spec(dependency) is None:
        pytest.skip('Install requirements.txt to run API integration tests',allow_module_level=True)

TMP=tempfile.TemporaryDirectory()
os.environ['DATABASE_URL']='sqlite:///'+str(Path(TMP.name)/'tests.db')
os.environ['ALLOWED_HOSTS']='testserver,localhost,127.0.0.1'
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from app.main import app
from app.database.session import Base,engine,SessionLocal
from app.models.entities import User,Driver,Truck,Route,Trip,TripEvent,EventCorrection,DelayReason,Setting,AuditLog
from app.core.security import hash_password
from app.services.time_engine import utcnow,EVENTS
from app.services.trips import describe

PASSWORD='Test-only-password-934!'

@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        for name,role in [('admin','ADMIN'),('director','DIRECTOR'),('driver','DRIVER'),('other','DRIVER')]:
            db.add(User(username=name,name=name,password_hash=hash_password(PASSWORD),role=role,is_active=True))
        db.flush()
        db.add_all([Driver(user_id=3,employee_id='D1',name='Driver',status='ACTIVE'),Driver(user_id=4,employee_id='D2',name='Other',status='ACTIVE')])
        db.flush()
        db.add_all([Truck(registration_number='TEST123',truck_code='TEST-001',assigned_driver_id=1,status='ACTIVE'),
                    Truck(registration_number='TEST456',truck_code='TEST-002',assigned_driver_id=2,status='ACTIVE'),
                    Route(origin='Origin',destination='Destination',expected_duration_minutes=60,allowed_delay_minutes=10),
                    Route(origin='Destination',destination='Origin',expected_duration_minutes=70,allowed_delay_minutes=10),
                    DelayReason(name='Traffic',is_active=True),Setting(id=1)])
    yield

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def login(client,username='admin'):
    response=client.post('/api/auth/login',json={'username':username,'password':PASSWORD})
    assert response.status_code==200,response.text
    client.headers['X-CSRF-Token']=response.json()['csrf']
    return response.json()


def create(client):
    login(client)
    r=client.post('/api/trips',json={'truck_id':1,'driver_id':1,'route_id':1,'return_route_id':2,
                                   'scheduled_departure':(utcnow()-timedelta(hours=5)).isoformat()})
    assert r.status_code==201,r.text
    return r.json()['id']


def event_payload(kind,code='TEST-001'):
    return {'event_type':kind,'truck_code':code,'device_id':'pytest','device_time':utcnow().isoformat()}


def test_login_health_logout(client):
    assert client.get('/health').status_code==200
    assert client.get('/api/trips').status_code==401
    assert client.post('/api/auth/login',json={'username':'admin','password':'bad'}).status_code==401
    data=login(client)
    assert 'password_hash' not in data['user']
    assert client.get('/api/auth/me').status_code==200
    assert client.post('/api/auth/logout').status_code==200
    assert client.get('/api/auth/me').status_code==401


def test_csrf_and_bearer(client):
    data=login(client)
    client.headers.pop('X-CSRF-Token')
    assert client.post('/api/auth/logout').status_code==403
    client.headers['Authorization']='Bearer '+data['access_token']
    assert client.post('/api/auth/logout').status_code==200
    assert client.get('/api/auth/me').status_code==401

@pytest.mark.parametrize('role',['director','driver'])
def test_admin_permissions(client,role):
    login(client,role)
    assert client.post('/api/routes',json={'origin':'A','destination':'B','expected_duration_minutes':50}).status_code==403
    assert client.get('/api/users').status_code==403
    assert client.get('/api/audit').status_code==403
    assert client.get('/api/dashboard/today').status_code==(403 if role=='driver' else 200)


def test_complete_driver_workflow(client):
    ident=create(client)
    login(client,'driver')
    assert client.post(f'/api/trips/{ident}/identify',json={'truck_code':'WRONG'}).status_code==422
    assert client.post(f'/api/trips/{ident}/identify',json={'truck_code':'TEST-001'}).status_code==200
    assert client.post(f'/api/trips/{ident}/events',json=event_payload(EVENTS[2])).status_code==409
    for kind in EVENTS:
        r=client.post(f'/api/trips/{ident}/events',json=event_payload(kind))
        assert r.status_code==201,r.text
    trip=r.json()
    assert trip['status']=='COMPLETED'
    assert len(trip['events'])==4
    assert all(e['truck_identity']=='TEST123 / TEST-001' for e in trip['events'])
    assert client.post(f'/api/trips/{ident}/events',json=event_payload(EVENTS[-1])).status_code==409


def test_driver_scope(client):
    ident=create(client)
    login(client,'other')
    assert client.get('/api/trips').json()==[]
    assert client.get(f'/api/trips/{ident}').status_code==404
    assert client.post(f'/api/trips/{ident}/events',json=event_payload(EVENTS[0])).status_code==404
    assert client.get('/api/drivers/1').status_code==404
    assert client.get('/api/trucks/1').status_code==404


def test_no_driver_time_override(client):
    ident=create(client)
    login(client,'driver')
    payload=event_payload(EVENTS[0]);payload['event_time']=utcnow().isoformat()
    assert client.post(f'/api/trips/{ident}/events',json=payload).status_code==422
    assert client.post(f'/api/trips/{ident}/events/missing',json={'event_type':EVENTS[0],'event_time':utcnow().isoformat(),'reason':'forgot punch'}).status_code==403


def test_snapshots_and_resource_conflicts(client):
    ident=create(client)
    assert client.post('/api/trips',json={'truck_id':1,'driver_id':1,'route_id':1,'return_route_id':2,'scheduled_departure':utcnow().isoformat()}).status_code==409
    assert client.delete('/api/trucks/1').status_code==409
    login(client,'driver')
    for kind in EVENTS:
        assert client.post(f'/api/trips/{ident}/events',json=event_payload(kind)).status_code==201
    login(client)
    assert client.put('/api/routes/1',json={'origin':'Origin','destination':'Destination','expected_duration_minutes':100,'allowed_delay_minutes':20,'is_active':True}).status_code==200
    assert client.get(f'/api/trips/{ident}').json()['outbound_expected']==60


def test_delay_correction_and_reports(client):
    ident=create(client)
    start=utcnow()-timedelta(hours=4)
    for kind,minutes in zip(EVENTS,[0,78,120,190]):
        r=client.post(f'/api/trips/{ident}/events/missing',json={'event_type':kind,'event_time':(start+timedelta(minutes=minutes)).isoformat(),'reason':'Verified historical punch from dispatch log'})
        assert r.status_code==201,r.text
    trip=r.json();event_id=trip['events'][1]['id'];old=trip['events'][1]['event_time']
    assert trip['segments'][0]['delay_minutes']==78-60
    login(client,'driver')
    r=client.post(f'/api/trips/{ident}/delay',json={'route_segment':'OUTBOUND','reason_id':1,'remarks':'Heavy traffic'})
    assert r.status_code==200,r.text
    assert client.post(f'/api/trips/{ident}/delay',json={'route_segment':'RETURN','reason_id':1}).status_code==409
    login(client)
    r=client.post(f'/api/trips/{ident}/events/{event_id}/corrections',json={'event_time':(start+timedelta(minutes=80)).isoformat(),'reason':'Dispatch record checked'})
    assert r.status_code==201,r.text
    assert r.json()['events'][1]['original_time']==old
    assert len(r.json()['events'][1]['corrections'])==1
    assert r.json()['segments'][0]['delay_minutes']==20
    invalid=client.post(f'/api/trips/{ident}/events/{event_id}/corrections',json={'event_time':(start-timedelta(minutes=1)).isoformat(),'reason':'Invalid test correction'})
    assert invalid.status_code==422
    login(client,'director')
    assert client.get('/api/reports/daily').status_code==200
    assert 'text/csv' in client.get('/api/reports/monthly?format=csv').headers['content-type']
    data=client.get('/api/dashboard/analytics?period=today').json()
    assert data['delay']['count']==1
    assert data['delay']['total_minutes']==20


def test_missing_punch_exception(client):
    ident=create(client)
    start=utcnow()-timedelta(hours=2)
    assert client.post(f'/api/trips/{ident}/events/missing',json={'event_type':EVENTS[0],'event_time':start.isoformat(),'reason':'Dispatch evidence checked'}).status_code==201
    codes={x['code'] for x in client.get('/api/dashboard/today').json()['exceptions']}
    assert {'MISSING_PUNCH','SIGNIFICANT_DELAY','CORRECTED'}<=codes


def test_inactive_entities_and_bad_references(client):
    login(client)
    base={'truck_id':1,'driver_id':1,'route_id':1,'return_route_id':2,'scheduled_departure':utcnow().isoformat()}
    assert client.post('/api/trips',json={**base,'truck_id':999}).status_code==404
    assert client.post('/api/trips',json={**base,'driver_id':2}).status_code==409
    assert client.post('/api/trips',json={**base,'return_route_id':1}).status_code==422
    assert client.delete('/api/trucks/1').status_code==200
    assert client.post('/api/trips',json=base).status_code==409


def test_cancel_preserves_history(client):
    ident=create(client)
    r=client.post(f'/api/trips/{ident}/cancel',json={'reason':'Customer cancelled dispatch'})
    assert r.status_code==200
    assert r.json()['status']=='CANCELLED'
    assert client.get(f'/api/trips/{ident}').status_code==200
    assert any(a['action']=='CANCEL' for a in client.get('/api/audit').json())


def test_validation_unique_and_injection(client):
    login(client)
    assert client.post('/api/routes',json={'origin':'same','destination':'same','expected_duration_minutes':60}).status_code==422
    assert client.post('/api/routes',json={'origin':'A','destination':'B','expected_duration_minutes':0}).status_code==422
    assert client.post('/api/auth/login',json={'username':"' OR 1=1 --",'password':'arbitrary'}).status_code==401
    assert client.get('/api/dashboard/analytics?period=custom&start=2026-09-09&end=2026-01-01').status_code==422
    assert client.get('/api/trips?limit=9999').status_code==422


def test_all_admin_resources(client):
    login(client)
    for path in ['users','drivers','trucks','routes','delay-reasons']:
        r=client.get('/api/'+path)
        assert r.status_code==200,r.text
        assert isinstance(r.json(),list)
        assert client.get('/api/'+path+'/1').status_code==200
    settings=client.get('/api/settings').json();settings.pop('id')
    settings['significant_delay_minutes']=40
    assert client.put('/api/settings',json=settings).status_code==200
    assert client.get('/api/settings').json()['significant_delay_minutes']==40


def test_disabled_user_session_revoked(client):
    data=login(client,'director')
    token=data['access_token']
    login(client)
    assert client.put('/api/users/2',json={'name':'director','username':'director','role':'DIRECTOR','is_active':False}).status_code==200
    client.headers['Authorization']='Bearer '+token
    assert client.get('/api/auth/me').status_code==401


def test_schema_has_constraints():
    with SessionLocal.begin() as db:
        assert db.scalar(select(func.count()).select_from(User))==4
        assert db.connection().exec_driver_sql('PRAGMA foreign_keys').scalar()==1
        assert db.connection().exec_driver_sql('PRAGMA foreign_key_check').all()==[]
