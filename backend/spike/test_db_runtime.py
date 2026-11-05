from concurrent.futures import ThreadPoolExecutor
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from django.db.utils import ConnectionHandler

from spike.db_runtime import run_db_worker


@unittest.skipUnless(importlib.util.find_spec("_sqlite3"), "SQLite-backed unit tests require _sqlite3; validate MySQL workers separately on the server.")
class WorkerConnectionTests(unittest.TestCase):
    def setUp(self):
        from django.conf import settings
        if not settings.configured:
            settings.configure(SECRET_KEY="worker-connection-test", USE_TZ=True,
                               DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}})
        self.directory = tempfile.TemporaryDirectory()
        self.handler = ConnectionHandler({alias: {
            "ENGINE": "django.db.backends.sqlite3", "NAME": str(Path(self.directory.name) / (alias + ".sqlite3")),
            "CONN_MAX_AGE": None,
        } for alias in ("default", "reporting")})
        self.patch_connections = patch("spike.db_runtime.connections", self.handler)
        self.patch_connections.start()
        self.patch_old = patch("spike.db_runtime.close_old_connections")
        self.patch_old.start()
        # A live caller connection must survive cleanup in the pool thread.
        with self.handler["default"].cursor() as cursor:
            cursor.execute("SELECT 7")
        self.caller_connection = self.handler["default"].connection

    def tearDown(self):
        self.patch_old.stop()
        self.patch_connections.stop()
        self.handler.close_all()
        self.directory.cleanup()

    def query_both(self):
        values = []
        for alias in ("default", "reporting"):
            with self.handler[alias].cursor() as cursor:
                cursor.execute("SELECT 42")
                values.append(cursor.fetchone()[0])
        return values

    def check_closed(self):
        for alias in ("default", "reporting"):
            self.assertIsNone(self.handler[alias].connection)

    def test_reused_worker_releases_all_aliases_without_closing_caller(self):
        def task():
            result = run_db_worker(self.query_both)
            self.check_closed()
            return result
        with ThreadPoolExecutor(max_workers=1) as pool:
            for _ in range(3):
                self.assertEqual(pool.submit(task).result(), [42, 42])
        self.assertIs(self.handler["default"].connection, self.caller_connection)
        with self.handler["default"].cursor() as cursor:
            cursor.execute("SELECT 7")
            self.assertEqual(cursor.fetchone()[0], 7)

    def test_exception_closes_connections_and_propagates_original_error(self):
        error = RuntimeError("trait task failed")
        def fail():
            self.query_both()
            raise error
        def task():
            try:
                run_db_worker(fail)
            finally:
                self.check_closed()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(RuntimeError) as caught:
                pool.submit(task).result()
        self.assertIs(caught.exception, error)

    def test_returned_failure_status_also_releases_connections(self):
        def failure_status():
            self.query_both()
            return {"status": "failed"}
        def task():
            result = run_db_worker(failure_status)
            self.check_closed()
            return result
        with ThreadPoolExecutor(max_workers=1) as pool:
            self.assertEqual(pool.submit(task).result(), {"status": "failed"})


if __name__ == "__main__":
    unittest.main()
