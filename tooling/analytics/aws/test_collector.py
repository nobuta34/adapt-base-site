import unittest
from unittest.mock import patch
import collector

class ReportsTest(unittest.TestCase):
    def test_pagination_and_encoded_site(self):
        calls = []
        def fake(url, body, token=None, form=False):
            calls.append((url, body))
            if 'analyticsdata' in url:
                if body['dimensions'][1]['name'] == 'pagePath':
                    if body['offset'] == '0': return {'rowCount': 2, 'rows': [{'x': 1}]}
                    return {'rowCount': 2, 'rows': [{'x': 2}]}
                return {'rowCount': 0}
            return {'rows': [{'keys': ['2026-10-01','https://adapt-base.com/'], 'clicks': 3}]}
        with patch.object(collector, 'post', fake):
            data = collector.collect('never-log-this', '558518317', 'https://adapt-base.com/', '2026-10-01', '2026-10-02')
        self.assertEqual(len(data['reports']['ga4_pages']['rows']), 2)
        self.assertEqual(data['reports']['ga4_events']['rows'], [])
        self.assertIn('https%3A%2F%2Fadapt-base.com%2F', calls[-1][0])
        self.assertEqual(calls[-1][1]['dataState'], 'final')
        self.assertNotIn('never-log-this', str(data))

    def test_api_failure_is_not_success(self):
        with patch.object(collector, 'post', side_effect=RuntimeError('API unavailable')):
            with self.assertRaises(RuntimeError):
                collector.collect('token', '558518317', 'https://adapt-base.com/', '2026-10-01', '2026-10-02')

if __name__ == '__main__': unittest.main()
