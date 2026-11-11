"""CP3: lỗi trở thành observation hoặc kết thúc run có kiểm soát."""
import json
import unittest
from unittest.mock import Mock

from agent import run_agent
from status_tools import StatusTools
from test_lab import FakeProvider, final, tool_call


class RobustnessTests(unittest.TestCase):
    def test_provider_exception_is_recorded_without_sensitive_text(self):
        provider = Mock()
        provider.complete.side_effect = RuntimeError('SECRET_REQUEST_DATA')
        result = run_agent('x', provider, StatusTools())
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['trace'][0]['event'], 'error')
        self.assertNotIn('SECRET_REQUEST_DATA', json.dumps(result))

    def test_tool_exception_does_not_lose_remaining_calls(self):
        response = tool_call('a', 'get_status', '{"provider":"cloudflare"}')
        second = tool_call('b', 'get_status', '{"provider":"github"}')
        response['calls'] += second['calls']
        response['message']['tool_calls'] += second['message']['tool_calls']
        tools = Mock()
        tools.execute.side_effect = [TimeoutError('SECRET_TOOL_DATA'), {'provider': 'github'}]
        provider = FakeProvider([response, final('Cloudflare chưa xác nhận; GitHub lấy được.')])
        result = run_agent('x', provider, tools)
        self.assertEqual(result['status'], 'completed')
        observations = provider.histories[1][-2:]
        self.assertEqual([m['tool_call_id'] for m in observations], ['a', 'b'])
        self.assertEqual(json.loads(observations[0]['content'])['error'], 'TimeoutError')
        self.assertEqual(json.loads(observations[1]['content'])['provider'], 'github')
        self.assertNotIn('SECRET_TOOL_DATA', json.dumps(result))

    def test_non_object_arguments_are_observations(self):
        for raw in ('[]', 'null', '42'):
            with self.subTest(raw=raw):
                provider = FakeProvider([tool_call('a', 'get_status', raw), final()])
                tools = Mock()
                result = run_agent('x', provider, tools)
                self.assertEqual(result['status'], 'completed')
                self.assertEqual(json.loads(provider.histories[1][-1]['content'])['error'], 'INVALID_ARGUMENTS')
                tools.execute.assert_not_called()

    def test_abnormal_finish_with_calls_does_not_execute_tools(self):
        response = tool_call('a', 'get_status', '{}')
        response['finish'] = 'content_filter'
        tools = Mock()
        result = run_agent('x', FakeProvider([response]), tools)
        self.assertEqual(result['status'], 'error')
        tools.execute.assert_not_called()

    def test_missing_provider_fields_returns_error(self):
        result = run_agent('x', FakeProvider([{}]), StatusTools())
        self.assertEqual(result['status'], 'error')

    def test_invalid_budget_does_not_call_provider(self):
        for budget in (0, -1, True, 1.5):
            with self.subTest(budget=budget):
                provider = Mock()
                self.assertEqual(run_agent('x', provider, StatusTools(), budget)['status'], 'error')
                provider.complete.assert_not_called()

    def test_unknown_tool_and_invalid_provider_are_returned_to_model(self):
        provider = FakeProvider([
            tool_call('a', 'missing', '{}'),
            tool_call('b', 'get_status', '{"provider":"invalid"}'),
            final('Không thể xác nhận.'),
        ])
        result = run_agent('x', provider, StatusTools())
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(json.loads(provider.histories[1][-1]['content'])['error'], 'UNKNOWN_TOOL')
        self.assertFalse(json.loads(provider.histories[2][-1]['content'])['ok'])
