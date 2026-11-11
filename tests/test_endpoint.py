"""Kiểm tra URL cấu hình, không gửi API request hoặc dùng key thật."""
import os
import unittest
from unittest.mock import patch

from providers import CONFIG, Provider


class EndpointTests(unittest.TestCase):
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'dummy'}, clear=True)
    def test_default_endpoint_is_unchanged(self):
        self.assertEqual(Provider('openai', 'test').url, CONFIG['openai'][1])

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'dummy'}, clear=True)
    def test_base_and_full_endpoint(self):
        base = 'https://example.invalid/openai/v1'
        for endpoint in (base, base + '/', base + '/chat/completions'):
            with self.subTest(endpoint=endpoint), patch.dict(os.environ, {'API_ENDPOINT': endpoint}):
                self.assertEqual(Provider('openai', 'test').url, base + '/chat/completions')

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'dummy', 'API_ENDPOINT': 'https://example.invalid'}, clear=True)
    def test_override_does_not_affect_other_providers(self):
        self.assertEqual(Provider('gemini', 'test').url, CONFIG['gemini'][1])

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'dummy', 'API_ENDPOINT': 'https://opencode.ai/inference/go/openai/v1'}, clear=True)
    @patch('providers.post_json')
    def test_opencode_session_is_stable_across_calls(self, post):
        post.return_value = {'choices': [{'message': {'role': 'assistant', 'content': 'ok'}, 'finish_reason': 'stop'}]}
        client = Provider('openai', 'test')
        client.complete([{'role': 'user', 'content': 'first'}], [])
        client.complete([{'role': 'user', 'content': 'second'}], [])
        sessions = [call.args[1]['x-opencode-session'] for call in post.call_args_list]
        self.assertTrue(sessions[0])
        self.assertEqual(sessions[0], sessions[1])
        self.assertEqual(post.call_args.args[1]['User-Agent'], 'StatusAgentLab/1.0')
