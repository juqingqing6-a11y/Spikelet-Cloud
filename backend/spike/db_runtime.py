"""Database lifecycle for dedicated ORM worker threads outside HTTP requests."""
from django.db import close_old_connections, connections


def run_db_worker(function, *args, **kwargs):
    """Run one pool task and release only this worker thread's connections."""
    try:
        close_old_connections()
        return function(*args, **kwargs)
    finally:
        # Request cleanup runs in the request thread, not in these pool threads.
        # Close explicitly even when CONN_MAX_AGE permits persistent connections.
        connections.close_all()
