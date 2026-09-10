from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.dependencies import management
from app.services.analytics import today, date_range, views, summarize

router=APIRouter(prefix='/api/dashboard',tags=['Dashboard'])

@router.get('/today')
def current(user=Depends(management),db:Session=Depends(get_db, scope='function')):
    return today(db)

@router.get('/analytics')
def analytics(period:str='month',start:date|None=None,end:date|None=None,truck_id:int|None=None,driver_id:int|None=None,
              user=Depends(management),db:Session=Depends(get_db, scope='function')):
    start,end=date_range(period,start,end)
    previous_end=start-timedelta(days=1)
    previous_start=previous_end-(end-start)
    return {'start':start,'end':end,**summarize(views(db,start,end,truck_id,driver_id)),
            'previous':{'start':previous_start,'end':previous_end,**summarize(views(db,previous_start,previous_end,truck_id,driver_id))}}
