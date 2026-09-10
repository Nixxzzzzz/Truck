from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import secrets
from fastapi import HTTPException
from sqlalchemy import select, or_
from app.models.entities import Trip, Truck, Driver, User, Route, TripEvent, EventCorrection, Delay, DelayReason, Setting
from app.repositories.records import get, public, effective_events, own_driver
from app.services.time_engine import EVENTS, STATES, utcnow, aware, iso, travel, validate_sequence, validate_correction
from app.services.audit import audit
from app.core.config import TIMEZONE


def accessible(db, ident, user, lock=False):
    trip = db.scalar(select(Trip).where(Trip.id == ident).with_for_update()) if lock else db.get(Trip, ident)
    if trip is None:
        raise HTTPException(404,'Trip not found')
    if user.role == 'DRIVER':
        driver = own_driver(db,user)
        if not driver or driver.id != trip.driver_id:
            raise HTTPException(404,'Trip not found')
    return trip


def verify_assignment(db, trip, code=None):
    truck, driver = get(db,Truck,trip.truck_id), get(db,Driver,trip.driver_id)
    user = get(db,User,driver.user_id)
    if truck.status != 'ACTIVE' or driver.status != 'ACTIVE' or not user.is_active:
        raise HTTPException(409,'Truck or driver is inactive')
    if truck.assigned_driver_id != driver.id:
        raise HTTPException(409,'Truck and driver assignment is inconsistent')
    if code is not None and code.strip().upper() != truck.truck_code:
        raise HTTPException(422,'Truck code does not match the assigned truck')
    return truck,driver


def create_trip(db, data, user, request=None):
    truck = get(db,Truck,data.truck_id)
    driver = get(db,Driver,data.driver_id)
    # Lock resources in a consistent order; unique partial indexes protect SQLite too.
    db.scalar(select(Truck).where(Truck.id == truck.id).with_for_update())
    db.scalar(select(Driver).where(Driver.id == driver.id).with_for_update())
    out, back = get(db,Route,data.route_id), get(db,Route,data.return_route_id)
    if not out.is_active or not back.is_active:
        raise HTTPException(422,'Routes must be active')
    if out.origin.casefold() != back.destination.casefold() or out.destination.casefold() != back.origin.casefold():
        raise HTTPException(422,'Return route must reverse the outbound route')
    if db.scalar(select(Trip).where(Trip.status.not_in(['COMPLETED','CANCELLED']), or_(Trip.truck_id==truck.id,Trip.driver_id==driver.id))):
        raise HTTPException(409,'Truck or driver already has an open trip')
    trip = Trip(trip_number='TT-'+utcnow().strftime('%Y%m%d')+'-'+secrets.token_hex(3).upper(),
                truck_id=truck.id,driver_id=driver.id,route_id=out.id,return_route_id=back.id,
                trip_date=data.scheduled_departure.astimezone(ZoneInfo(TIMEZONE)).date(),
                scheduled_departure=aware(data.scheduled_departure),status='SCHEDULED',origin=out.origin,destination=out.destination,
                outbound_expected=out.expected_duration_minutes,outbound_tolerance=out.allowed_delay_minutes,
                return_expected=back.expected_duration_minutes,return_tolerance=back.allowed_delay_minutes)
    verify_assignment(db,trip)
    db.add(trip)
    db.flush()
    audit(db,user,'CREATE','trips',trip.id,new=public(trip),request=request)
    return describe(db,trip)


def punch(db, trip, data, user, request=None, correction=False):
    if trip.status in ('COMPLETED','CANCELLED'):
        raise HTTPException(409,'This trip is closed')
    if user.role != 'DRIVER' and not correction:
        raise HTTPException(403,'Normal punches must be confirmed by the assigned driver')
    truck,_ = verify_assignment(db,trip,None if correction else data.truck_code)
    items = effective_events(db,trip.id)
    times = [datetime.fromisoformat(e['event_time']) for e in items]
    timestamp = aware(data.event_time) if correction else utcnow()
    try:
        validate_sequence(times,data.event_type,timestamp)
        if timestamp > utcnow():
            raise ValueError('Event time cannot be in the future')
    except ValueError as exc:
        raise HTTPException(409,str(exc))
    event = TripEvent(trip_id=trip.id,event_type=data.event_type,event_time=timestamp,
                      created_by=user.id,verification_method='ADMIN_CORRECTION' if correction else 'TRUCK_CODE',
                      truck_identity=f'{truck.registration_number} / {truck.truck_code}',
                      source='ADMIN_CORRECTION' if correction else 'DRIVER_CONFIRMED',
                      latitude=None if correction else data.latitude,longitude=None if correction else data.longitude,
                      device_id='admin' if correction else data.device_id,
                      correction_reason=data.reason if correction else '',
                      device_time=None if correction else data.device_time)
    db.add(event)
    trip.status = STATES[len(items)+1]
    db.flush()
    payload = public(event)
    if correction:
        payload['reason'] = data.reason
    audit(db,user,'MISSING_EVENT_CORRECTION' if correction else 'PUNCH','trip_events',event.id,new=payload,request=request)
    return describe(db,trip)


def correct(db, trip, event_id, data, user, request=None):
    items = effective_events(db,trip.id)
    index = next((i for i,e in enumerate(items) if e['id']==event_id),None)
    if index is None:
        raise HTTPException(404,'Event not found in this trip')
    times = [datetime.fromisoformat(e['event_time']) for e in items]
    try:
        validate_correction(times,index,data.event_time)
    except ValueError as exc:
        raise HTTPException(422,str(exc))
    change = EventCorrection(event_id=event_id,old_time=times[index],new_time=aware(data.event_time),reason=data.reason,corrected_by=user.id,revision=len(items[index]['corrections'])+1)
    db.add(change)
    db.flush()
    audit(db,user,'TIME_CORRECTION','trip_events',event_id,{'event_time':iso(times[index])},public(change),request)
    return describe(db,trip)


def report_delay(db, trip, data, user, request=None):
    if trip.status == 'CANCELLED':
        raise HTTPException(409,'Cancelled trip')
    reason = get(db,DelayReason,data.reason_id)
    if not reason.is_active:
        raise HTTPException(422,'Delay reason is inactive')
    view = describe(db,trip)
    segment = view['segments'][0 if data.route_segment == 'OUTBOUND' else 1]
    if segment['status'] != 'DELAYED':
        raise HTTPException(409,'This segment is not beyond its delay tolerance')
    delay = db.scalar(select(Delay).where(Delay.trip_id==trip.id,Delay.route_segment==data.route_segment))
    old = public(delay) if delay else None
    if not delay:
        delay = Delay(trip_id=trip.id,route_segment=data.route_segment,reason_id=reason.id,remarks=data.remarks,
                      reported_by=user.id,delay_minutes=segment['delay_minutes'])
        db.add(delay)
    else:
        delay.reason_id,delay.remarks,delay.reported_by,delay.delay_minutes = reason.id,data.remarks,user.id,segment['delay_minutes']
    db.flush()
    audit(db,user,'DELAY_REPORT','delays',delay.id,old,public(delay),request)
    return describe(db,trip)


def describe(db, trip, now=None):
    now = now or utcnow()
    result = public(trip)
    truck,driver = get(db,Truck,trip.truck_id),get(db,Driver,trip.driver_id)
    result.update(truck=public(truck),driver=public(driver))
    events = effective_events(db,trip.id)
    labels = [f'{trip.origin} departure',f'{trip.destination} arrival',f'{trip.destination} departure',f'{trip.origin} arrival']
    times = [datetime.fromisoformat(e['event_time']) for e in events]
    for i,e in enumerate(events):
        e['label'],e['location'] = labels[i],trip.origin if i in (0,3) else trip.destination
    result['events'] = events
    result['next_event'] = EVENTS[len(events)] if len(events)<4 and trip.status!='CANCELLED' else None
    result['next_label'] = labels[len(events)] if result['next_event'] else None
    reports = list(db.scalars(select(Delay).where(Delay.trip_id==trip.id)))
    segments=[]
    for index,(key,name,expected,tolerance) in enumerate([
        ('OUTBOUND',f'{trip.origin} → {trip.destination}',trip.outbound_expected,trip.outbound_tolerance),
        ('RETURN',f'{trip.destination} → {trip.origin}',trip.return_expected,trip.return_tolerance)]):
        pos = index*2
        start = times[pos] if len(times)>pos else None
        end = times[pos+1] if len(times)>pos+1 else None
        metric = travel(start,end or now,expected,tolerance)
        report = next((r for r in reports if r.route_segment==key),None)
        metric.update(key=key,name=name,departure=iso(start),arrival=iso(end),complete=end is not None,
                      expected_arrival=iso(start+timedelta(minutes=expected)) if start else None,
                      reason=get(db,DelayReason,report.reason_id).name if report else None,
                      remarks=report.remarks if report else '',reported_delay_minutes=report.delay_minutes if report else None,
                      reported_by=report.reported_by if report else None,reported_at=iso(report.updated_at) if report else None)
        segments.append(metric)
    result['segments']=segments
    result['travel_minutes']=round(sum(s['actual_minutes'] or 0 for s in segments),2)
    result['delay_minutes']=round(sum(s['delay_minutes'] for s in segments),2)
    result['timing_status']='DELAYED' if any(s['status']=='DELAYED' for s in segments) else 'ON_TIME' if times else 'NOT_STARTED'
    result['current_stage']={'SCHEDULED':'Awaiting departure','OUTBOUND':segments[0]['name'],'AT_DESTINATION':f'At {trip.destination}',
                             'RETURNING':segments[1]['name'],'COMPLETED':'Trip completed','CANCELLED':'Cancelled'}[trip.status]
    active = segments[1] if len(events)>=3 else segments[0]
    result['started_at']=active['departure']
    result['expected_arrival']=active['expected_arrival'] if trip.status in ('OUTBOUND','RETURNING') else None
    result['current_delay_minutes']=active['delay_minutes'] if trip.status in ('OUTBOUND','RETURNING') else 0
    result['correction_count']=sum(len(e['corrections']) + (e['source']=='ADMIN_CORRECTION') for e in events)
    result['delay_report_count']=len(reports)
    result['exceptions']=exceptions(db,trip,result,now)
    return result


def exceptions(db,trip,view,now):
    if trip.status=='CANCELLED':
        return []
    config = db.get(Setting,1)
    thresholds = {'significant_delay_minutes':30,'start_grace_minutes':30,'missing_punch_grace_minutes':30,'destination_dwell_minutes':120,'max_open_minutes':720}
    if config:
        thresholds.update({k:getattr(config,k) for k in thresholds})
    items=[]
    def add(code,message,severity='warning'):
        items.append({'code':code,'message':message,'severity':severity,'trip_id':trip.id,'trip_number':trip.trip_number})
    if trip.status=='SCHEDULED' and now>aware(trip.scheduled_departure)+timedelta(minutes=thresholds['start_grace_minutes']):
        add('LATE_START','Scheduled departure has not been recorded')
    if trip.status in ('OUTBOUND','RETURNING'):
        segment=view['segments'][trip.status=='RETURNING']
        if segment['delay_minutes']>=thresholds['significant_delay_minutes']:
            add('SIGNIFICANT_DELAY',f"Truck is {segment['delay_minutes']:.0f} minutes beyond expected arrival",'critical')
        if segment['delay_minutes']>=thresholds['missing_punch_grace_minutes']:
            add('MISSING_PUNCH',f"{view['next_label']} punch is overdue; confirm arrival or travel delay")
    events=view['events']
    if trip.status=='AT_DESTINATION' and now>datetime.fromisoformat(events[1]['event_time'])+timedelta(minutes=thresholds['destination_dwell_minutes']):
        add('RETURN_NOT_STARTED','Return journey has not started within the configured dwell window')
    if trip.status not in ('COMPLETED','CANCELLED') and events and now>datetime.fromisoformat(events[0]['event_time'])+timedelta(minutes=thresholds['max_open_minutes']):
        add('LONG_OPEN','Trip has remained open unusually long','critical')
    for segment in view['segments']:
        if segment['status']=='DELAYED' and not segment['reason']:
            add('MISSING_REASON',f"Delay reason needed for {segment['name']}")
        elif segment['reason']:
            add('DELAY_REPORTED',f"{segment['name']}: {segment['reason']}",'info')
    if view['correction_count']:
        add('CORRECTED',f"{view['correction_count']} manual correction(s); review timeline",'info')
    if trip.status not in ('COMPLETED','CANCELLED'):
        try:
            verify_assignment(db,trip)
        except HTTPException:
            add('ASSIGNMENT','Truck or driver assignment is inconsistent or inactive','critical')
    for e in events:
        if e['device_time'] and abs((datetime.fromisoformat(e['device_time'])-datetime.fromisoformat(e['original_time'])).total_seconds())>300:
            add('CLOCK_DIFFERENCE','Device time differs from server time by over five minutes')
            break
    return items
