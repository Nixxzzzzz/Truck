import logging
from fastapi import FastAPI, Request, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from app.core.config import ROOT, ALLOWED_HOSTS
from app.database.session import get_db
from app.api import auth, catalog, trips, dashboard, reports

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger('trucktrack')
app=FastAPI(title='TruckTrack API',version='1.0.0',description='Desktop transport operations. Cookie + CSRF or opaque Bearer authentication. All application endpoints under /api.')
app.add_middleware(TrustedHostMiddleware,allowed_hosts=ALLOWED_HOSTS)
for router in [auth.router,catalog.router,trips.router,dashboard.router,reports.router]:
    app.include_router(router)
app.mount('/static',StaticFiles(directory=ROOT/'app/static'),name='static')

@app.middleware('http')
async def security_headers(request:Request,call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['Cache-Control']='no-store'
    if request.url.path not in ('/docs','/redoc'):
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    return response

@app.exception_handler(IntegrityError)
async def integrity_error(request,exc):
    logger.warning('Integrity conflict on %s',request.url.path)
    return JSONResponse(status_code=409,content={'detail':'Record conflicts with existing data or references. Check unique fields, assignments and event order.'})

@app.exception_handler(OperationalError)
async def operational_error(request,exc):
    logger.error('Database operation failed on %s',request.url.path)
    return JSONResponse(status_code=503,content={'detail':'Database unavailable or busy. Check migration/setup, then retry.'})

@app.exception_handler(Exception)
async def unexpected_error(request,exc):
    logger.exception('Unexpected request failure')
    return JSONResponse(status_code=500,content={'detail':'Unexpected server error. Check server logs.'})

@app.get('/health',tags=['Health'])
def health(db:Session=Depends(get_db, scope='function')):
    db.execute(text('SELECT 1'))
    db.execute(text('SELECT id FROM settings LIMIT 1'))
    return {'status':'ok','database':'connected','version':'1.0.0'}

@app.get('/',include_in_schema=False)
def home():
    return FileResponse(ROOT/'app/templates/index.html')
