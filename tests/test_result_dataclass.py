import unittest
from reporter import TestStepResult


class TestTestStepResult(unittest.TestCase):
    def test_to_dict(self):
        ts = TestStepResult(step={"action": "go"}, status="passed", screenshot="img.png")
        d = ts.to_dict()
        self.assertEqual(d["step"]["action"], "go")
        self.assertEqual(d["status"], "passed")
        self.assertEqual(d["screenshot"], "img.png")
        self.assertIsNone(d.get("error"))


if __name__ == "__main__":
    unittest.main()
