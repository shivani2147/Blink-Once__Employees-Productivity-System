import unittest
from datetime import date

from routers.employee import _validate_gps, _build_trend_series


class DummyQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


class DummyDB:
    def query(self, model):
        return DummyQuery()


class EmployeeGpsValidationTests(unittest.TestCase):
    def test_missing_location_is_rejected(self):
        valid, err_msg = _validate_gps(DummyDB(), None, None)
        self.assertFalse(valid)
        self.assertIn("location", err_msg.lower())

    def test_month_filter_builds_daily_trend(self):
        class DummyRecord:
            def __init__(self, record_date, status):
                self.date = record_date
                self.status = status

        class DummyAttendance:
            def __init__(self, att_date, status):
                self.date = att_date
                self.status = status

        records = [
            DummyRecord(date(2026, 7, 1), "Done"),
            DummyRecord(date(2026, 7, 2), "Ongoing"),
        ]
        attendance = [
            DummyAttendance(date(2026, 7, 1), "Present"),
            DummyAttendance(date(2026, 7, 2), "Absent"),
        ]

        trend = _build_trend_series(records, attendance, date(2026, 7, 15), year=2026, month=7)

        self.assertEqual(trend["labels"][:3], ["1", "2", "3"])
        self.assertEqual(len(trend["labels"]), 31)
        self.assertEqual(trend["data"][0], 0.0)
        self.assertEqual(trend["data"][1], 35.0)


if __name__ == "__main__":
    unittest.main()
