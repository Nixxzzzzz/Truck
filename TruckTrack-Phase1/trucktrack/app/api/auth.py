import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import User, SessionToken, LoginAttempt
from app.schemas.requests import Login
from app.core.security import digest, verify_password, hash_password
from app.core.config import COOKIE_SECURE, SESSION_HOURS, TIMEZONE
from app.api.dependencies import current_user
from app.repositories.records import public
from app.services.time_engine import utcnow
from app.services.audit import audit

router = APIRouter(prefix='/api/auth', tags=['Authentication'])
DUMMY_HASH = hash_password(secrets.token_urlsafe(32))

@router.post('/login')
def login(data: Login, request: Request, response: Response, db: Session = Depends(get_db, scope='function')):
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, 'Cross-site login rejected')
    key = digest(request.client.host if request.client else 'local')
    cutoff = utcnow() - timedelta(minutes=15)
    db.execute(delete(LoginAttempt).where(LoginAttempt.timestamp < cutoff))
    count = db.scalar(select(func.count()).select_from(LoginAttempt).where(LoginAttempt.key == key))
    if count >= 20:
        raise HTTPException(429, 'Too many attempts. Try again in 15 minutes.')
    user = db.scalar(select(User).where(User.username == data.username.lower()))
    valid = verify_password(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.is_active:
        db.add(LoginAttempt(key=key))
        audit(db, None, 'LOGIN_FAILED', 'auth', None, new={'username':data.username}, request=request)
        db.commit()  # Failed-attempt tracking must survive the HTTP error rollback.
        raise HTTPException(401, 'Invalid username or password')
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    db.execute(delete(SessionToken).where(SessionToken.expires_at < utcnow()))
    db.add(SessionToken(user_id=user.id, token_hash=digest(token), csrf=csrf, expires_at=utcnow()+timedelta(hours=SESSION_HOURS)))
    audit(db, user, 'LOGIN', 'users', user.id, request=request)
    response.set_cookie('trucktrack_session', token, httponly=True, secure=COOKIE_SECURE, samesite='strict', max_age=SESSION_HOURS*3600)
    return {'user':public(user), 'csrf':csrf, 'access_token':token, 'token_type':'bearer', 'timezone':TIMEZONE}

@router.get('/me')
def me(request: Request, user=Depends(current_user)):
    return {'user':public(user), 'csrf':request.state.session.csrf, 'timezone':TIMEZONE}

@router.post('/logout')
def logout(request: Request, response: Response, user=Depends(current_user), db: Session=Depends(get_db, scope='function')):
    db.delete(request.state.session)
    audit(db, user, 'LOGOUT', 'users', user.id, request=request)
    response.delete_cookie('trucktrack_session')
    return {'message':'Signed out'}
