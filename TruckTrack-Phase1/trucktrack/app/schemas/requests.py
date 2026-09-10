from datetime import datetime
from typing import Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, StringConstraints

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)

class Login(Input):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=False)
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)

class UserInput(Input):
    name: str = Field(min_length=1,max_length=100)
    username: str = Field(min_length=3,max_length=100,pattern=r'^[A-Za-z0-9@._+-]+$')
    password: Annotated[str, StringConstraints(strip_whitespace=False, min_length=12, max_length=128)] | None = None
    role: Literal['ADMIN','DIRECTOR','DRIVER']
    is_active: bool = True

class DriverInput(Input):
    user_id: int = Field(gt=0)
    employee_id: str = Field(min_length=1,max_length=40)
    name: str = Field(min_length=1,max_length=100)
    phone: str = Field(default='',max_length=30,pattern=r'^[0-9+() -]*$')
    status: Literal['ACTIVE','INACTIVE'] = 'ACTIVE'

class TruckInput(Input):
    registration_number: str = Field(min_length=3,max_length=30,pattern=r'^[A-Za-z0-9 -]+$')
    truck_code: str = Field(min_length=3,max_length=60,pattern=r'^[A-Za-z0-9_-]+$')
    truck_type: str = Field(default='',max_length=80)
    capacity: float = Field(default=0,ge=0,le=1000000)
    status: Literal['ACTIVE','INACTIVE'] = 'ACTIVE'
    assigned_driver_id: int | None = Field(default=None,gt=0)

class RouteInput(Input):
    origin: str = Field(min_length=1,max_length=100)
    destination: str = Field(min_length=1,max_length=100)
    expected_duration_minutes: int = Field(gt=0,le=10080)
    allowed_delay_minutes: int = Field(default=10,ge=0,le=10080)
    is_active: bool = True
    @model_validator(mode='after')
    def distinct(self):
        if self.origin.casefold() == self.destination.casefold():
            raise ValueError('Origin and destination must differ')
        return self

class ReasonInput(Input):
    name: str = Field(min_length=1,max_length=80)
    description: str = Field(default='',max_length=500)
    is_active: bool = True

class TripInput(Input):
    truck_id: int = Field(gt=0)
    driver_id: int = Field(gt=0)
    route_id: int = Field(gt=0)
    return_route_id: int = Field(gt=0)
    scheduled_departure: datetime
    @field_validator('scheduled_departure')
    @classmethod
    def zoned(cls, value):
        if value.tzinfo is None:
            raise ValueError('Timestamp must include timezone')
        return value

class EventInput(Input):
    event_type: Literal['ORIGIN_DEPARTURE','DESTINATION_ARRIVAL','DESTINATION_DEPARTURE','ORIGIN_ARRIVAL']
    truck_code: str = Field(min_length=3,max_length=60)
    latitude: float | None = Field(default=None,ge=-90,le=90)
    longitude: float | None = Field(default=None,ge=-180,le=180)
    device_id: str = Field(default='',max_length=200)
    device_time: datetime | None = None
    @field_validator('device_time')
    @classmethod
    def zoned_device(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError('Device timestamp must include timezone')
        return value
    @model_validator(mode='after')
    def coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('Supply both coordinates or neither')
        return self

class CorrectionInput(Input):
    event_time: datetime
    reason: str = Field(min_length=5,max_length=1000)
    @field_validator('event_time')
    @classmethod
    def zoned(cls, value):
        return TripInput.zoned(value)

class MissingInput(CorrectionInput):
    event_type: Literal['ORIGIN_DEPARTURE','DESTINATION_ARRIVAL','DESTINATION_DEPARTURE','ORIGIN_ARRIVAL']

class DelayInput(Input):
    route_segment: Literal['OUTBOUND','RETURN']
    reason_id: int = Field(gt=0)
    remarks: str = Field(default='',max_length=1000)

class CancelInput(Input):
    reason: str = Field(min_length=5,max_length=1000)

class IdentifyInput(Input):
    truck_code: str = Field(min_length=3,max_length=60)

class SettingsInput(Input):
    significant_delay_minutes: int = Field(ge=1,le=10080)
    start_grace_minutes: int = Field(ge=1,le=10080)
    missing_punch_grace_minutes: int = Field(ge=1,le=10080)
    destination_dwell_minutes: int = Field(ge=1,le=10080)
    max_open_minutes: int = Field(ge=1,le=43200)
