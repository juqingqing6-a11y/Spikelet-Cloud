"""Local UI handoff: existing sibling frontend + an isolated SQLite database."""
from .settings_dev import *

REPOSITORY_ROOT = BASE_DIR.parent
HANDOFF_RUNTIME = BASE_DIR / "runtime" / "handoff"

TEMPLATES = [dict(TEMPLATES[0], DIRS=[REPOSITORY_ROOT / "frontend" / "templates"])]
STATICFILES_DIRS = [
    REPOSITORY_ROOT / "frontend" / "static",
    BASE_DIR / "static",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": HANDOFF_RUNTIME / "db.sqlite3",
    }
}
MEDIA_ROOT = HANDOFF_RUNTIME / "media"
BATCH_ROOT = HANDOFF_RUNTIME / "batch"

# Analysis code uses backend/static for generated result paths. Source UI assets
# remain in frontend/static; staticfiles can serve both during local development.
for directory in (HANDOFF_RUNTIME, BASE_DIR / "static", MEDIA_ROOT, BATCH_ROOT):
    directory.mkdir(parents=True, exist_ok=True)
