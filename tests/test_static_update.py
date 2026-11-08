from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from scripts.update_schedule import update
from scripts.update_schedule import fetch_sources
from scripts.seznam_backup import convert


class StaticUpdateTests(unittest.TestCase):
    def test_automatic_backup_when_nova_rejects_runner(self):
        with patch('scripts.update_schedule.fetch_nova',side_effect=OSError('403')):
            with patch('scripts.update_schedule.fetch_seznam',return_value=[]) as backup:
                with self.assertLogs(level='WARNING'):
                    rows,source=fetch_sources()
                backup.assert_called_once()
                self.assertEqual(source,'https://tv.seznam.cz/')
                self.assertEqual(rows,[])

    def test_backup_uses_live_flag_and_prague_time(self):
        row={'name':'Formule 1 - Velká cena Test 2026 (sprint)', 'live':True,
             'time_from':1795307100, 'time_to':1795310100, 'short_description':'Přímý přenos'}
        converted=convert(row)
        self.assertEqual(converted['kind'],'sprint')
        self.assertTrue(converted['start'].endswith('+01:00'))
        self.assertIsNone(convert(dict(row,live=False)))
        self.assertIsNone(convert(dict(row,name='F1 Academy - závod')))

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
