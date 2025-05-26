import unittest
from unittest.mock import MagicMock, patch
import sys
import types

# Provide a dummy nest_asyncio module for imports
sys.modules.setdefault('nest_asyncio', types.SimpleNamespace(apply=lambda: None))
class _DummyBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

sys.modules.setdefault('pydantic', types.SimpleNamespace(BaseModel=_DummyBaseModel))
sys.modules.setdefault('browser_use', types.SimpleNamespace(Agent=object, Controller=object))
sys.modules.setdefault('langchain_openai', types.SimpleNamespace(ChatOpenAI=object))
sys.modules.setdefault('openai', types.SimpleNamespace(RateLimitError=Exception))

import jira_writer


class TestSubtaskHelpers(unittest.TestCase):
    @patch("jira_writer.connect_to_jira")
    def test_read_scenarios_from_subtask(self, mock_connect):
        mock_jira = MagicMock()
        mock_connect.return_value = mock_jira
        mock_issue = MagicMock()
        mock_issue.fields.description = (
            'test\n```json\n[{"scenario": "A", "steps": []}]\n```'
        )
        mock_jira.issue.return_value = mock_issue

        scenarios = jira_writer.read_scenarios_from_subtask("ABC-1")
        self.assertEqual(len(scenarios), 1)
        self.assertEqual(scenarios[0]["scenario"], "A")

    @patch("jira_writer.connect_to_jira")
    def test_create_subtask_with_scenarios(self, mock_connect):
        mock_jira = MagicMock()
        mock_connect.return_value = mock_jira
        mock_parent = MagicMock()
        mock_parent.fields.project.key = "PROJ"
        mock_jira.issue.return_value = mock_parent
        mock_created = MagicMock()
        mock_created.key = "PROJ-2"
        mock_jira.create_issue.return_value = mock_created

        key = jira_writer.create_subtask_with_scenarios(
            "PROJ-1", [{"scenario": "A", "steps": []}]
        )
        self.assertEqual(key, "PROJ-2")
        mock_jira.create_issue.assert_called_once()


if __name__ == "__main__":
    unittest.main()
