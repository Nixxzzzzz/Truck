from fastapi.encoders import jsonable_encoder
from app.models.entities import AuditLog


def audit(db, user, action, entity, ident, old=None, new=None, request=None):
    device = ''
    if request:
        device = f'{request.client.host if request.client else ""} | {request.headers.get("user-agent", "")}'[:500]
    db.add(AuditLog(user_id=user.id if user else None, action=action, entity_type=entity,
                    entity_id=ident, old_value=jsonable_encoder(old), new_value=jsonable_encoder(new), ip_device=device))
