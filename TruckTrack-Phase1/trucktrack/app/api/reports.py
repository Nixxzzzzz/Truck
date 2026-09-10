import csv
import io
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.dependencies import management
from app.services.analytics import date_range,views,summarize

router=APIRouter(prefix='/api/reports',tags=['Reports'])


def safe_csv(value):
    value='' if value is None else str(value)
    return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r')) else value

@router.get('/{period}')
def report(period:str,start:date|None=None,end:date|None=None,format:str='json',truck_id:int|None=None,driver_id:int|None=None,
           user=Depends(management),db:Session=Depends(get_db, scope='function')):
    aliases={'daily':'today','weekly':'week','monthly':'month','custom':'custom'}
    if period not in aliases or format not in ('json','csv'):
        raise HTTPException(422,'Choose daily, weekly, monthly or custom and json/csv')
    if (start is None) != (end is None):
        raise HTTPException(422, 'Supply both start and end dates')
    start,end=date_range('custom' if start and end else aliases[period],start,end)
    items=views(db,start,end,truck_id,driver_id)
    summary=summarize(items)
    previous_end=start-timedelta(days=1)
    previous_start=previous_end-(end-start)
    previous=summarize(views(db,previous_start,previous_end,truck_id,driver_id))
    rows=[]
    for t in items:
        for s in t['segments']:
            rows.append({'date':t['trip_date'],'trip':t['trip_number'],'truck':t['truck']['registration_number'],
                         'driver':t['driver']['name'],'direction':s['name'],'departure':s['departure'],'arrival':s['arrival'],
                         'travel_minutes':s['actual_minutes'],'expected_minutes':s['expected_minutes'],'tolerance_minutes':s['tolerance_minutes'],
                         'delay_minutes':s['delay_minutes'],'reason':s['reason'],'remarks':s['remarks'],
                         'status':s['status'],'trip_status':t['status'],'corrections':t['correction_count']})
    if format=='json':
        return {'start':start,'end':end,'summary':summary,'previous':{'start':previous_start,'end':previous_end,**previous},'rows':rows}
    stream=io.StringIO(newline='')
    writer=csv.writer(stream)
    writer.writerow(['TruckTrack report',period,str(start),str(end),'Timestamps UTC with offset'])
    writer.writerow(['Metric','Current','Previous equal-length period'])
    for label,key in [('Trips','total_trips'),('Completed','completed_trips'),('On-time %','on_time_percentage')]:
        writer.writerow([label,summary[key],previous[key]])
    for label,group,key in [('Average travel min','travel','average'),('Average delay min','delay','average'),('Total delay min','delay','total_minutes')]:
        writer.writerow([label,summary[group][key],previous[group][key]])
    writer.writerow([])
    writer.writerow(['Delay reason','Segments','Percent'])
    for row in summary['reasons']:
        writer.writerow([safe_csv(row['name']),row['count'],row['percent']])
    writer.writerow([])
    fields=['date','trip','truck','driver','direction','departure','arrival','travel_minutes','expected_minutes','tolerance_minutes','delay_minutes','reason','remarks','status','trip_status','corrections']
    writer.writerow(fields)
    for row in rows:
        writer.writerow([safe_csv(row[k]) for k in fields])
    return Response('\ufeff'+stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="trucktrack-{period}-{start}-{end}.csv"'})
