import unittest
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

from browser_use_runner_lib import parse_agent_logs

class TestParseAgentLogs(unittest.TestCase):
    def test_success_detection(self):
        logs = [
            "INFO     [agent] ✅ Task completed successfully",
            "INFO     [agent] 📄 Result: All good"
        ]
        results, final_result, success = parse_agent_logs(logs, "scenario")
        self.assertTrue(success)
        self.assertEqual(final_result, "All good")

    def test_failure_detection(self):
        logs = [
            "INFO     [agent] ❌ Task completed without success",
            "INFO     [agent] 📄 Result: Failed to do thing"
        ]
        results, final_result, success = parse_agent_logs(logs, "scenario")
        self.assertFalse(success)
        self.assertEqual(final_result, "Failed to do thing")

if __name__ == '__main__':
    unittest.main()
