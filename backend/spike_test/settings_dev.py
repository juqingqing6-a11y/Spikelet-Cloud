from .settings_base import *

DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

SECRET_KEY = "django-insecure-local-development-only"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "runtime" / "dev" / "db.sqlite3",
    }
}

MEDIA_ROOT = BASE_DIR / "media"
BATCH_ROOT = BASE_DIR / "batch"