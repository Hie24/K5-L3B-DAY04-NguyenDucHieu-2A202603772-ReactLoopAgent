"""Retry của LLM provider độc lập với lỗi tool trong scenario eval."""
import io
import json
import os
import urllib.error
import unittest
from unittest.mock import patch

from providers import Provider, post_json


class TransportTests(unittest.TestCase):
    @patch('providers.time.sleep')
    @patch('providers.urllib.request.urlopen')
    def test_rate_limit_respects_retry_after(self, open_url, sleep):
        limited = urllib.error.HTTPError('https://example.invalid', 429, 'limited', {'Retry-After': '2'}, io.BytesIO())
        response = open_url.return_value.__enter__.return_value
        response.read.return_value = b'{"ok":true}'
        open_url.side_effect = [limited, open_url.return_value]
        self.assertEqual(post_json('https://example.invalid', {}, {}), {'ok': True})
        sleep.assert_called_once_with(2)

    @patch('providers.time.sleep')
    @patch('providers.urllib.request.urlopen')
    def test_persistent_rate_limit_is_bounded(self, open_url, sleep):
        errors = [urllib.error.HTTPError('https://example.invalid', 429, 'limited', {'Retry-After': '1'}, io.BytesIO()) for _ in range(4)]
        open_url.side_effect = errors
        with self.assertRaises(RuntimeError):
            post_json('https://example.invalid', {}, {})
        self.assertEqual(open_url.call_count, 4)
        self.assertEqual(sleep.call_count, 3)
        errors[-1].close()

    @patch('providers.time.sleep')
    @patch('providers.urllib.request.urlopen')
    def test_authentication_failure_is_not_retried(self, open_url, sleep):
        error = urllib.error.HTTPError('https://example.invalid', 401, 'unauthorized', {}, io.BytesIO())
        open_url.side_effect = error
        with self.assertRaises(RuntimeError):
            post_json('https://example.invalid', {}, {})
        sleep.assert_not_called()
        error.close()

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'dummy', 'MAX_COMPLETION_TOKENS': '2048', 'REASONING_EFFORT': 'low'}, clear=True)
    @patch('providers.post_json')
    def test_budget_settings_are_sent_to_model(self, post):
        post.return_value = {'choices': [{'message': {'role': 'assistant', 'content': 'ok'}, 'finish_reason': 'stop'}]}
        Provider('openai', 'test').complete([{'role': 'user', 'content': 'x'}], [])
        payload = post.call_args.args[2]
        self.assertEqual(payload['max_completion_tokens'], 2048)
        self.assertEqual(payload['reasoning_effort'], 'low')
