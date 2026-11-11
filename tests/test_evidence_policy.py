"""CP5: validation dùng URL quan sát được và giữ nguyên giới hạn model calls."""
import unittest

from agent import run_agent
from status_tools import StatusTools
from test_lab import FakeProvider, final, tool_call


class EvidencePolicyTests(unittest.TestCase):
    def test_fabricated_url_does_not_pass_gate(self):
        url = 'https://stspg.io/pjgptg3cfc6n'
        provider = FakeProvider([
            tool_call('a', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'),
            final('Nguồn: https://example.invalid/fabricated'),
            final('Nguồn: ' + url),
        ])
        result = run_agent('x', provider, StatusTools(), max_steps=3)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(provider.histories), 3)
        self.assertIn(url, provider.histories[2][-1]['content'])
        self.assertEqual(sum(t['event']=='validation_missing_source' for t in result['trace']), 1)

    def test_repeated_missing_source_stops_at_budget(self):
        provider = FakeProvider([
            tool_call('a', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'),
            final('Thiếu URL'), final('Vẫn thiếu URL'),
        ])
        result = run_agent('x', provider, StatusTools(), max_steps=3)
        self.assertEqual(result['status'], 'max_steps')
        self.assertEqual(len(provider.histories), 3)
        self.assertEqual(sum(t['event']=='validation_missing_source' for t in result['trace']), 2)

    def test_status_only_does_not_require_incident_url(self):
        provider = FakeProvider([
            tool_call('a', 'get_status', '{"provider":"github"}'), final('Snapshot operational.'),
        ])
        self.assertEqual(run_agent('x', provider, StatusTools())['status'], 'completed')
