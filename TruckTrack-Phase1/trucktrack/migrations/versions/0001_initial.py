"""Frozen initial schema, independent of future model edits."""
from alembic import op
revision="0001"
down_revision=None
branch_labels=None
depends_on=None
from datetime import datetime, date
from sqlalchemy import String, Text, ForeignKey, CheckConstraint, UniqueConstraint, Index, text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase):
    pass
from datetime import timezone
def utcnow():
    return datetime.now(timezone.utc)

class Record:
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class User(Record, Base):
    __tablename__ = 'users'
    name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (CheckConstraint("role IN ('ADMIN','DIRECTOR','DRIVER')"),)

class Driver(Record, Base):
    __tablename__ = 'drivers'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True)
    employee_id: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(30), default='')
    status: Mapped[str] = mapped_column(String(16), default='ACTIVE')
    __table_args__ = (CheckConstraint("status IN ('ACTIVE','INACTIVE')"),)

class Truck(Record, Base):
    __tablename__ = 'trucks'
    registration_number: Mapped[str] = mapped_column(String(30), unique=True)
    truck_code: Mapped[str] = mapped_column(String(60), unique=True)
    truck_type: Mapped[str] = mapped_column(String(80), default='')
    capacity: Mapped[float] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(16), default='ACTIVE')
    assigned_driver_id: Mapped[int | None] = mapped_column(ForeignKey('drivers.id'))
    __table_args__ = (CheckConstraint('capacity >= 0'), CheckConstraint("status IN ('ACTIVE','INACTIVE')"))

class Route(Record, Base):
    __tablename__ = 'routes'
    origin: Mapped[str] = mapped_column(String(100))
    destination: Mapped[str] = mapped_column(String(100))
    expected_duration_minutes: Mapped[int]
    allowed_delay_minutes: Mapped[int] = mapped_column(default=10)
    is_active: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (CheckConstraint('expected_duration_minutes > 0'), CheckConstraint('allowed_delay_minutes >= 0'), CheckConstraint('origin <> destination'))

class DelayReason(Record, Base):
    __tablename__ = 'delay_reasons'
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(String(500), default='')
    is_active: Mapped[bool] = mapped_column(default=True)

class Trip(Record, Base):
    __tablename__ = 'trips'
    trip_number: Mapped[str] = mapped_column(String(40), unique=True)
    truck_id: Mapped[int] = mapped_column(ForeignKey('trucks.id'), index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey('drivers.id'), index=True)
    route_id: Mapped[int] = mapped_column(ForeignKey('routes.id'))
    return_route_id: Mapped[int] = mapped_column(ForeignKey('routes.id'))
    trip_date: Mapped[date] = mapped_column(index=True)
    scheduled_departure: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), default='SCHEDULED')
    origin: Mapped[str] = mapped_column(String(100))
    destination: Mapped[str] = mapped_column(String(100))
    outbound_expected: Mapped[int]
    outbound_tolerance: Mapped[int]
    return_expected: Mapped[int]
    return_tolerance: Mapped[int]
    __table_args__ = (
        CheckConstraint("status IN ('SCHEDULED','OUTBOUND','AT_DESTINATION','RETURNING','COMPLETED','CANCELLED')"),
        Index('uq_open_truck', 'truck_id', unique=True, sqlite_where=text("status NOT IN ('COMPLETED','CANCELLED')"), postgresql_where=text("status NOT IN ('COMPLETED','CANCELLED')")),
        Index('uq_open_driver', 'driver_id', unique=True, sqlite_where=text("status NOT IN ('COMPLETED','CANCELLED')"), postgresql_where=text("status NOT IN ('COMPLETED','CANCELLED')")),
    )

class TripEvent(Record, Base):
    __tablename__ = 'trip_events'
    trip_id: Mapped[int] = mapped_column(ForeignKey('trips.id'), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    verification_method: Mapped[str] = mapped_column(String(40))
    correction_reason: Mapped[str] = mapped_column(String(1000), default='')
    device_id: Mapped[str] = mapped_column(String(200), default='')
    device_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    truck_identity: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(32))
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    __table_args__ = (UniqueConstraint('trip_id','event_type'), CheckConstraint('latitude BETWEEN -90 AND 90'), CheckConstraint('longitude BETWEEN -180 AND 180'))

class EventCorrection(Record, Base):
    __tablename__ = 'event_corrections'
    event_id: Mapped[int] = mapped_column(ForeignKey('trip_events.id'), index=True)
    old_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    new_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(String(1000))
    corrected_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    revision: Mapped[int]
    __table_args__ = (UniqueConstraint('event_id','revision'),)

class Delay(Record, Base):
    __tablename__ = 'delays'
    trip_id: Mapped[int] = mapped_column(ForeignKey('trips.id'), index=True)
    route_segment: Mapped[str] = mapped_column(String(16))
    delay_minutes: Mapped[float]
    reason_id: Mapped[int] = mapped_column(ForeignKey('delay_reasons.id'))
    remarks: Mapped[str] = mapped_column(String(1000), default='')
    reported_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    __table_args__ = (UniqueConstraint('trip_id','route_segment'), CheckConstraint("route_segment IN ('OUTBOUND','RETURN')"))

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[int | None] = mapped_column(index=True)
    old_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ip_device: Mapped[str] = mapped_column(String(500), default='')

class SessionToken(Base):
    __tablename__ = 'sessions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf: Mapped[str] = mapped_column(String(80))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class LoginAttempt(Base):
    __tablename__ = 'login_attempts'
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class Setting(Base):
    __tablename__ = 'settings'
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    significant_delay_minutes: Mapped[int] = mapped_column(default=30)
    start_grace_minutes: Mapped[int] = mapped_column(default=30)
    missing_punch_grace_minutes: Mapped[int] = mapped_column(default=30)
    destination_dwell_minutes: Mapped[int] = mapped_column(default=120)
    max_open_minutes: Mapped[int] = mapped_column(default=720)


def upgrade():
    Base.metadata.create_all(op.get_bind())

def downgrade():
    Base.metadata.drop_all(op.get_bind())
