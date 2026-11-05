"""Bounded model reuse and filesystem helpers for image analysis."""
import gc
import logging
import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger("django.rgpas.batch")
BATCH_LOCK = threading.Lock()
PREDICTION_LOCK = threading.RLock()
_model_key = None
_model = None

@dataclass(frozen=True)
class DetectionOutput:
    number: int
    save_dir: str
    image_path: str

def clear_detector_cache():
    """Drop all references before releasing unused CUDA cache."""
    global _model, _model_key
    with PREDICTION_LOCK:
        _model = None
        _model_key = None
        gc.collect()
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def log_cuda_memory(stage):
    import torch
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        logger.info(
            "[GPU] %s allocated=%.1fMiB reserved=%.1fMiB free=%.1fMiB total=%.1fMiB",
            stage, torch.cuda.memory_allocated() / 2**20,
            torch.cuda.memory_reserved() / 2**20, free / 2**20, total / 2**20,
        )

def predict_cached(factory, weights, source, project, name, *, return_details=False):
    """Keep only the selected detector; preserve the legacy integer response."""
    global _model, _model_key
    import torch
    device = os.environ.get("RGPAS_DETECTION_DEVICE")
    if device is None:
        device = "0" if torch.cuda.is_available() else "cpu"
    key = (str(Path(weights).resolve()), device, factory)
    with PREDICTION_LOCK:
        if _model_key != key or _model is None:
            clear_detector_cache()
            _model = factory(str(weights))
            _model_key = key
        log_cuda_memory("before detection")
        results = _model.predict(
            source=str(source), imgsz=640, project=str(project), name=name,
            device=device, save=True, show_labels=False, show_conf=False,
            line_width=2, save_crop=True, verbose=False,
            exist_ok=return_details,
        )
        if not results:
            raise RuntimeError("检测器未返回结果")
        result = results[0]
        number = int(result.number)
        if not return_details:
            return number
        save_dir = Path(result.save_dir)
        image_path = save_dir / Path(source).name
        if not image_path.is_file():
            image_path = image_path.with_suffix(".jpg")
        if not image_path.is_file():
            raise FileNotFoundError("检测结果图片未生成: " + str(image_path))
        log_cuda_memory("after detection")
        return DetectionOutput(number, str(save_dir), str(image_path))

@contextmanager
def batch_slot():
    """Serialize batch jobs without blocking status requests."""
    with BATCH_LOCK:
        yield

def static_file_url(path, static_root, base_url="/static/"):
    relative = Path(path).resolve().relative_to(Path(static_root).resolve())
    return base_url.rstrip("/") + "/" + quote(relative.as_posix(), safe="/")

def result_payload(rows, task_id, status, **extra):
    """Keep old response arrays aligned with completed rows only."""
    return {
        "task_id": task_id, "status": status, "results": list(rows),
        "filenames_list": [row["filename"] for row in rows],
        "number": [str(row["number"]) for row in rows],
        "sum_list": [str(row["complete_count"]) for row in rows],
        **extra,
    }
