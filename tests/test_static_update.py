from pathlib import Path
import json
import tempfile
import unittest

from scripts.update_schedule import update


class StaticUpdateTests(unittest.TestCase):
    def test_outage_preserves_last_successful_timestamp_and_programmes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'schedule.json'
            original = update(path, fetcher=lambda: [])
            def fail():
                raise OSError('Simulated Nova outage')
            with self.assertLogs(level='ERROR'):
                saved = update(path, fetcher=fail)
            self.assertEqual(saved['programmes'], original['programmes'])
            self.assertEqual(saved['updated_at'], original['updated_at'])
            self.assertIsNotNone(saved['fetch_failed_at'])
            refreshed = update(path, fetcher=lambda: [])
            self.assertIsNone(refreshed['fetch_failed_at'])

    def test_no_fallback_means_fail_instead_of_fabricating_schedule(self):
        with tempfile.TemporaryDirectory() as directory:
            def fail():
                raise OSError('Simulated Nova outage')
            with self.assertLogs(level='ERROR'), self.assertRaises(FileNotFoundError):
                update(Path(directory)/'missing.json', fetcher=fail)
