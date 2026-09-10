import hmac
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import SessionToken, User
from app.core.security import digest
from app.services.time_engine import aware, utcnow


def current_user(request: Request, db: Session = Depends(get_db, scope='function')):
    auth = request.headers.get('authorization', '')
    bearer = auth.startswith('Bearer ')
    token = auth[7:] if bearer else request.cookies.get('trucktrack_session')
    if not token:
        raise HTTPException(401, 'Please sign in')
    session = db.scalar(select(SessionToken).where(SessionToken.token_hash == digest(token)))
    if not session or aware(session.expires_at) <= utcnow():
        raise HTTPException(401, 'Session expired; sign in again')
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        raise HTTPException(401, 'Account is inactive')
    if not bearer and request.method not in ('GET','HEAD','OPTIONS'):
        if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), session.csrf):
            raise HTTPException(403, 'Invalid CSRF token; refresh and try again')
    request.state.session = session
    return user


def roles(*allowed):
    def permission(user=Depends(current_user)):
        if user.role not in allowed:
            raise HTTPException(403, 'You do not have permission for this action')
        return user
    return permission

admin = roles('ADMIN')
management = roles('ADMIN','DIRECTOR')
