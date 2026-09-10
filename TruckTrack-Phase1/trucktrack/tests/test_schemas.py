"""Request schema tests runnable with unittest and Pydantic only."""
import unittest
from datetime import datetime,timezone
from pydantic import ValidationError
from app.schemas.requests import UserInput,RouteInput,TruckInput,TripInput,EventInput,CorrectionInput,SettingsInput,Login,DriverInput

class SchemaValidation(unittest.TestCase):
    def invalid(self,model,**data):
        with self.assertRaises(ValidationError):
            model(**data)
    def test_route_same_place(self):
        self.invalid(RouteInput,origin='Delhi',destination='delhi',expected_duration_minutes=60)
    def test_route_zero_expected(self):
        self.invalid(RouteInput,origin='A',destination='B',expected_duration_minutes=0)
    def test_negative_tolerance(self):
        self.invalid(RouteInput,origin='A',destination='B',expected_duration_minutes=60,allowed_delay_minutes=-1)
    def test_empty_names(self):
        self.invalid(RouteInput,origin='  ',destination='B',expected_duration_minutes=60)
    def test_truck_nan_capacity(self):
        self.invalid(TruckInput,registration_number='ABC123',truck_code='T01',capacity=float('nan'))
    def test_truck_negative_capacity(self):
        self.invalid(TruckInput,registration_number='ABC123',truck_code='T01',capacity=-1)
    def test_invalid_phone(self):
        self.invalid(DriverInput,user_id=1,employee_id='A',name='Driver',phone='abc')
    def test_trip_requires_timezone(self):
        self.invalid(TripInput,truck_id=1,driver_id=1,route_id=1,return_route_id=2,scheduled_departure='2026-01-01T09:00:00')
    def test_no_arbitrary_event_time(self):
        self.invalid(EventInput,event_type='ORIGIN_DEPARTURE',truck_code='T01',event_time='2026-01-01T09:00:00Z')
    def test_event_coordinates_pair(self):
        self.invalid(EventInput,event_type='ORIGIN_DEPARTURE',truck_code='T01',latitude=28.0)
    def test_event_coordinate_bounds(self):
        self.invalid(EventInput,event_type='ORIGIN_DEPARTURE',truck_code='T01',latitude=91,longitude=70)
    def test_device_time_requires_timezone(self):
        self.invalid(EventInput,event_type='ORIGIN_DEPARTURE',truck_code='T01',device_time='2026-01-01T09:00:00')
    def test_event_invalid_type(self):
        self.invalid(EventInput,event_type='UNKNOWN',truck_code='T01')
    def test_correction_reason_required(self):
        self.invalid(CorrectionInput,event_time='2026-01-01T09:00:00Z',reason='')
    def test_short_password(self):
        self.invalid(UserInput,name='A',username='admin',role='ADMIN',password='weak')
    def test_password_spaces_preserved(self):
        password='  correct horse battery staple  '
        self.assertEqual(UserInput(name=' A ',username='admin',role='ADMIN',password=password).password,password)
        self.assertEqual(Login(username='admin',password=password).password,password)
    def test_invalid_role(self):
        self.invalid(UserInput,name='A',username='admin',role='SUPERADMIN')
    def test_valid_payloads(self):
        route=RouteInput(origin=' Noida ',destination='Delhi',expected_duration_minutes=60)
        self.assertEqual(route.origin,'Noida')
        event=EventInput(event_type='ORIGIN_DEPARTURE',truck_code='T01',latitude=28,longitude=77,device_time=datetime.now(timezone.utc))
        self.assertEqual(event.longitude,77)

if __name__=='__main__':
    unittest.main()
