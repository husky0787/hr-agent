"""Streaming state must merge repeated sources without dropping tool history."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from agent.multi_agent import _merge_state


class AgentStateTests(unittest.TestCase):
    def test_research_and_workflow_share_citations_but_keep_both_tool_calls(self):
        state = {"citations": [], "tool_calls_log": []}
        tool = {"name": "search_handbook_tool", "args": {"query": "first week"}}
        _merge_state(state, {"citations": ["onboarding-checklist.md", "it-setup.md"], "tool_calls_log": [tool]})
        _merge_state(state, {"citations": ["onboarding-checklist.md", "benefits-guide.md"], "tool_calls_log": [tool]})
        self.assertEqual(state["citations"], ["onboarding-checklist.md", "it-setup.md", "benefits-guide.md"])
        self.assertEqual(len(state["tool_calls_log"]), 2)


if __name__ == "__main__":
    unittest.main()
