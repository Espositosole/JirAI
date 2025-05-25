import unittest
from unittest.mock import MagicMock, patch
from jira_test_selector import get_test_selection


class TestGetTestSelection(unittest.TestCase):
    @patch("jira_test_selector.connect_to_jira")
    def test_get_test_selection(self, mock_connect):
        mock_jira = MagicMock()
        mock_connect.return_value = mock_jira
        mock_comment = MagicMock()
        mock_comment.created = "2024-01-01T00:00:10.000+0000"
        mock_comment.body = "run 1,2"
        mock_jira.comments.return_value = [mock_comment]

        selection = get_test_selection("ABC-1", since_time="2024-01-01T00:00:00.000+0000")
        self.assertEqual(selection, [0, 1])


if __name__ == "__main__":
    unittest.main()
