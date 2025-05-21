import unittest
from unittest.mock import patch, mock_open, MagicMock

from browser_use_runner import run_browser_use_test


class TestRunBrowserUseTest(unittest.TestCase):
    @patch("browser_use_runner.subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_parses_clean_json(self, m_open, m_run):
        m_run.return_value = MagicMock(
            stdout='[{"status":"passed","error":null,"screenshot_filename":"img.png"}]'
        )
        results = run_browser_use_test([{"action": "go"}], scenario_name="Test")
        self.assertEqual(results[0].status, "passed")
        self.assertIsNone(results[0].error)
        self.assertFalse(hasattr(results[0], "screenshot"))

    @patch("browser_use_runner.subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_parses_json_with_logs(self, m_open, m_run):
        output = 'LOG line\n[{"status":"passed","error":null,"screenshot_filename":"img.png"}]\nDone'
        m_run.return_value = MagicMock(stdout=output)
        results = run_browser_use_test([{"action": "go"}], scenario_name="Test")
        self.assertEqual(results[0].status, "passed")
        self.assertIsNone(results[0].error)
        self.assertFalse(hasattr(results[0], "screenshot"))

    @patch("browser_use_runner.subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_parse_failure(self, m_open, m_run):
        m_run.return_value = MagicMock(stdout="Error: could not run")
        results = run_browser_use_test(
            [{"action": "go"}, {"action": "click"}], scenario_name="Test"
        )
        self.assertEqual(len(results), 2)
        for res in results:
            self.assertEqual(res.status, "failed")
            self.assertTrue(res.error.startswith("Error"))
            self.assertFalse(hasattr(res, "screenshot"))


if __name__ == "__main__":
    unittest.main()
