"""Dependency-free rules/security tests: python -m unittest tests.test_rules -v."""
import unittest
from datetime import datetime,timedelta,timezone
from app.services.time_engine import travel,validate_sequence,validate_correction,EVENTS,aware
from app.core.security import hash_password,verify_password,digest

class TimeRules(unittest.TestCase):
    def setUp(self):
        self.start=datetime(2026,1,1,9,tzinfo=timezone.utc)
    def metric(self,minutes):
        return travel(self.start,self.start+timedelta(minutes=minutes),60,10)
    def test_exact_expected(self):
        self.assertEqual(self.metric(60)['status'],'ON_TIME')
        self.assertEqual(self.metric(60)['delay_minutes'],0)
    def test_within_tolerance(self):
        self.assertEqual(self.metric(65)['status'],'ON_TIME')
        self.assertEqual(self.metric(65)['delay_minutes'],5)
    def test_tolerance_boundary(self):
        self.assertEqual(self.metric(70)['status'],'ON_TIME')
    def test_just_beyond_tolerance(self):
        self.assertEqual(self.metric(70.01)['status'],'DELAYED')
    def test_delayed_uses_expected_not_tolerance(self):
        self.assertEqual(self.metric(78)['delay_minutes'],18)
    def test_not_started(self):
        self.assertEqual(travel(None,None,60,10)['status'],'NOT_STARTED')
    def test_early(self):
        self.assertEqual(self.metric(40)['delay_minutes'],0)
    def test_cross_midnight(self):
        start=datetime(2026,1,1,23,30,tzinfo=timezone.utc)
        self.assertEqual(travel(start,start+timedelta(minutes=90),60,10)['actual_minutes'],90)
    def test_timezone_equivalence(self):
        end=self.start.astimezone(timezone(timedelta(hours=5,minutes=30)))+timedelta(minutes=60)
        self.assertEqual(travel(self.start,end,60,10)['actual_minutes'],60)
    def test_correct_sequence(self):
        times=[]
        for i,event in enumerate(EVENTS):
            stamp=self.start+timedelta(minutes=i*60)
            validate_sequence(times,event,stamp)
            times.append(stamp)
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            validate_sequence([self.start],EVENTS[0],self.start)
    def test_missing_predecessor(self):
        with self.assertRaises(ValueError):
            validate_sequence([],EVENTS[3],self.start)
    def test_reverse_time(self):
        with self.assertRaises(ValueError):
            validate_sequence([self.start],EVENTS[1],self.start-timedelta(seconds=1))
    def test_fifth_event(self):
        with self.assertRaises(ValueError):
            validate_sequence([self.start]*4,EVENTS[0],self.start)
    def test_correction_preserves_input(self):
        original=[self.start,self.start+timedelta(minutes=60)]
        adjusted=validate_correction(original,1,self.start+timedelta(minutes=75))
        self.assertNotEqual(adjusted,original)
        self.assertEqual(original[1],self.start+timedelta(minutes=60))
    def test_correction_cannot_break_order(self):
        with self.assertRaises(ValueError):
            validate_correction([self.start,self.start+timedelta(minutes=60)],1,self.start-timedelta(minutes=1))
    def test_future_correction(self):
        with self.assertRaises(ValueError):
            validate_correction([self.start],0,self.start+timedelta(minutes=1),now=self.start)

class SecurityRules(unittest.TestCase):
    def test_salted_password_roundtrip(self):
        password='A sufficiently long password'
        a,b=hash_password(password),hash_password(password)
        self.assertNotEqual(a,b)
        self.assertTrue(verify_password(password,a))
        self.assertFalse(verify_password('wrong',a))
    def test_invalid_hash(self):
        self.assertFalse(verify_password('abc','malformed'))
    def test_token_digest(self):
        self.assertEqual(len(digest('abc')),64)
        self.assertNotEqual(digest('abc'),digest('xyz'))

if __name__=='__main__':
    unittest.main()
