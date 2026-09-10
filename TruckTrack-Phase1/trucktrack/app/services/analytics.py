from collections import Counter, defaultdict
from datetime import date, timedelta
from statistics import mean
from zoneinfo import ZoneInfo
from sqlalchemy import select, or_
from fastapi import HTTPException
from app.models.entities import Trip
from app.services.time_engine import utcnow
from app.services.trips import describe
from app.core.config import TIMEZONE


def date_range(period='month',start=None,end=None):
    today=utcnow().astimezone(ZoneInfo(TIMEZONE)).date()
    if period=='today':
        start=end=today
    elif period=='week':
        start,end=today-timedelta(days=today.weekday()),today
    elif period=='month':
        start,end=today.replace(day=1),today
    elif period=='custom':
        if not start or not end:
            raise HTTPException(422,'Custom range requires start and end')
    else:
        raise HTTPException(422,'Unknown date period')
    if start>end or (end-start).days>3660:
        raise HTTPException(422,'Choose an ordered range of at most 10 years')
    return start,end


def views(db,start,end,truck_id=None,driver_id=None):
    statement=select(Trip).where(Trip.trip_date>=start,Trip.trip_date<=end).order_by(Trip.trip_date,Trip.id)
    if truck_id:
        statement=statement.where(Trip.truck_id==truck_id)
    if driver_id:
        statement=statement.where(Trip.driver_id==driver_id)
    now=utcnow()
    return [describe(db,t,now) for t in db.scalars(statement)]


def stats(values):
    return {'average':round(mean(values),2) if values else None,'minimum':min(values) if values else None,'maximum':max(values) if values else None,'count':len(values)}


def summarize(items):
    active=[t for t in items if t['status']!='CANCELLED']
    completed=[t for t in active if t['status']=='COMPLETED']
    segments=[s for t in active for s in t['segments'] if s['complete']]
    delayed=[s for s in segments if s['status']=='DELAYED']
    reasons=Counter(s['reason'] or 'Unreported' for s in delayed)
    directions=Counter(s['name'] for s in delayed)
    by_day=defaultdict(list)
    for t in completed:
        by_day[t['trip_date']].append(t)
    trend=[{'date':day,'trips':len(ts),'average_travel':round(mean(t['travel_minutes'] for t in ts),2),
            'delay_minutes':round(sum(t['delay_minutes'] for t in ts),2)} for day,ts in sorted(by_day.items())]
    def breakdown(counter):
        total=sum(counter.values())
        return [{'name':name,'count':n,'percent':round(n*100/total,1)} for name,n in counter.most_common()]
    drivers=[]
    for ident in sorted({t['driver_id'] for t in active}):
        own=[t for t in active if t['driver_id']==ident]
        done=[t for t in own if t['status']=='COMPLETED']
        drivers.append({'driver_id':ident,'name':own[0]['driver']['name'],'total_trips':len(own),'completed_trips':len(done),
                        'on_time_percentage':round(sum(t['timing_status']=='ON_TIME' for t in done)*100/len(done),1) if done else None,
                        'missing_punches':sum(sum(e['code']=='MISSING_PUNCH' for e in t['exceptions']) for t in own),
                        'delay_reports':sum(t['delay_report_count'] for t in own),
                        'delay_frequency':round(sum(t['timing_status']=='DELAYED' for t in done)*100/len(done),1) if done else None,
                        'manually_corrected_events':sum(sum(bool(e['corrections']) or e['source']=='ADMIN_CORRECTION' for e in t['events']) for t in own),
                        'completion_percentage':round(len(done)*100/len(own),1)})
    return {'total_trips':len(active),'completed_trips':len(completed),'cancelled_trips':len(items)-len(active),
            'on_time_percentage':round(sum(t['timing_status']=='ON_TIME' for t in completed)*100/len(completed),1) if completed else None,
            'outbound':stats([s['actual_minutes'] for s in segments if s['key']=='OUTBOUND']),
            'return':stats([s['actual_minutes'] for s in segments if s['key']=='RETURN']),
            'travel':stats([t['travel_minutes'] for t in completed]),
            'delay':{**stats([s['delay_minutes'] for s in delayed]),'total_minutes':round(sum(s['delay_minutes'] for s in delayed),2),
                     'most_common_reason':reasons.most_common(1)[0][0] if reasons else None},
            'reasons':breakdown(reasons),'directions':breakdown(directions),'trend':trend,'drivers':drivers}


def today(db):
    day=utcnow().astimezone(ZoneInfo(TIMEZONE)).date()
    statement=select(Trip).where(or_(Trip.trip_date==day,Trip.status.not_in(['COMPLETED','CANCELLED']))).order_by(Trip.scheduled_departure)
    items=[describe(db,t) for t in db.scalars(statement)]
    alerts=[e for t in items for e in t['exceptions']]
    alerts.sort(key=lambda e:{'critical':0,'warning':1,'info':2}[e['severity']])
    return {'date':day.isoformat(),'trips':items,'exceptions':alerts,'summary':summarize([t for t in items if t['trip_date']==day.isoformat()])}
