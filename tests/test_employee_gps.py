import unittest

from routers.employee import _validate_gps


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


if __name__ == "__main__":
    unittest.main()
