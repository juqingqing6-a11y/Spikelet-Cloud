"""Bind bundled Ultralytics versions without rebuilding modules per image."""
import importlib
import importlib.util
import os
import sys
import threading
from contextlib import contextmanager
from typing import Callable

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VERS = {
    "v8": os.path.join(_BASE, "yolov8_current"),
    "v8legacy": os.path.join(_BASE, "yolov8"),
    "v10": os.path.join(_BASE, "yolov10_current"),
}
_CACHE = {}
_BIND_LOCK = threading.RLock()
_BIND_STATE = threading.local()

def _modules():
    return {key: value for key, value in sys.modules.items()
            if key == "ultralytics" or key.startswith("ultralytics.")}

def _purge_ulx_submodules():
    for key in list(_modules()):
        sys.modules.pop(key, None)

def _load_ulx(root_dir):
    package_dir = os.path.join(root_dir, "ultralytics")
    init_py = os.path.join(package_dir, "__init__.py")
    if not os.path.isfile(init_py):
        raise RuntimeError("missing __init__.py: " + init_py)
    spec = importlib.util.spec_from_file_location(
        "ultralytics", init_py, submodule_search_locations=[package_dir],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["ultralytics"] = module
    spec.loader.exec_module(module)
    return module

@contextmanager
def bind_ultralytics(version):
    """Serialize process-wide module switching and cache complete module graphs."""
    with _BIND_LOCK:
        previous = getattr(_BIND_STATE, 'version', None)
        if previous == version:
            yield
            return
        saved = _modules()
        loaded = False
        try:
            _purge_ulx_submodules()
            if version in _CACHE:
                sys.modules.update(_CACHE[version])
            else:
                _load_ulx(_VERS[version])
            loaded = True
            _BIND_STATE.version = version
            yield
        finally:
            if loaded:
                _CACHE[version] = _modules()
            _BIND_STATE.version = previous
            _purge_ulx_submodules()
            sys.modules.update(saved)

def get_ulx(version):
    with bind_ultralytics(version):
        return sys.modules["ultralytics"]

def get_detect_func(version: str, import_path: str, func_name: str) -> Callable:
    with bind_ultralytics(version):
        raw = getattr(importlib.import_module(import_path), func_name)
    def wrapper(*args, **kwargs):
        with bind_ultralytics(version):
            return raw(*args, **kwargs)
    return wrapper
