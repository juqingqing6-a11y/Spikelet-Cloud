"""Single-image jobs: isolated paths, bounded workers and short HTTP requests.

The existing detector, classifier, transforms and trait functions are reused.
Run under the project's current single-process threaded Django service.
"""
import json
import logging
import math
import os
import re
import shutil
import threading
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

from django.db import close_old_connections
from django.http import JsonResponse
from django.shortcuts import render

from .batch_runtime import batch_slot, static_file_url, log_cuda_memory

logger = logging.getLogger('django.rgpas.single')
MODELS = {
    'spike-yolo': ('single_yolo', 'single_yolo_result', 'v10', 'yolov10_current.detect', 'testYolov10'),
    'yolov8': ('single_yolov8', 'single_yolov8_result', 'v8legacy', 'yolov8.detect', 'testYolov8'),
    'yolov10': ('single_yolov10', 'single_yolov10_result', 'v10', 'yolov10_current.detect', 'testYolov10m'),
}


class JobError(Exception):
    def __init__(self, message, status=400):
        self.status = status
        super().__init__(message)


class JobStore:
    """One active job per session; globally bounded queued and running jobs."""
    def __init__(self, limit=4, ttl=3600):
        self.lock = threading.RLock()
        self.jobs = {}
        self.limit = limit
        self.ttl = ttl

    def _purge(self):
        now = time.monotonic()
        for key, job in list(self.jobs.items()):
            if job['done'] and now - job['updated'] > self.ttl:
                self.jobs.pop(key, None)

    def get(self, owner, task_id, kind=None):
        with self.lock:
            self._purge()
            job = self.jobs.get(task_id)
            if not job or job['owner'] != owner or (kind and kind != job['kind']):
                raise JobError('任务不存在或已过期，请重新选择图片并计数。', 404)
            return job

    def begin(self, owner, task_id, kind, signature):
        with self.lock:
            self._purge()
            existing = self.jobs.get(task_id)
            if existing:
                if existing['owner'] != owner or existing['kind'] != kind or existing['signature'] != signature:
                    raise JobError('任务编号冲突，请重新选择图片。', 409)
                return existing, False
            if any(j['owner'] == owner and not j['done'] for j in self.jobs.values()):
                raise JobError('当前会话已有单图任务执行中，请等待或恢复查询，勿重复提交。', 409)
            if sum(not j['done'] for j in self.jobs.values()) >= self.limit:
                raise JobError('单图任务队列已满，请稍后重试。', 429)
            job = dict(task_id=task_id, owner=owner, kind=kind, signature=signature,
                       status='queued', phase='queued', done=False, updated=time.monotonic(),
                       result={}, context={}, error='', progress=0)
            self.jobs[task_id] = job
            return job, True

    def update(self, job, **values):
        with self.lock:
            job.update(values)
            job['updated'] = time.monotonic()

    def payload(self, job):
        with self.lock:
            data = {k: job[k] for k in ('task_id', 'kind', 'status', 'phase', 'done', 'error', 'progress')}
            data.update(job['result'])
            return data


JOBS = JobStore()


def _views():
    # Import after views has finished loading; no model imports are duplicated.
    from . import views
    return views


def _owner(request):
    info = request.session.get('user_info')
    if not isinstance(info, dict) or not info.get('user'):
        raise JobError('登录已过期，请重新登录。', 401)
    if not request.session.session_key:
        request.session.save()
    return (request.session.session_key, str(info['user']), str(info.get('role', ''))), dict(info)


def _task_id(value):
    value = value or uuid.uuid4().hex
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,64}', value):
        raise JobError('任务编号无效。')
    return value


def _response(job):
    response = JsonResponse(JOBS.payload(job), status=200 if job['done'] else 202)
    response['Cache-Control'] = 'no-store'
    return response


def _fail_response(exc):
    return JsonResponse({'status': 'failed', 'done': True, 'error': str(exc)}, status=exc.status)


def _run(job, action):
    close_old_connections()
    try:
        # Share the existing batch lock: single and batch GPU work cannot overlap.
        with batch_slot():
            JOBS.update(job, status='running', phase='initializing')
            logger.info('[SINGLE %s] start %s', job['task_id'], job['kind'])
            result = action()
            JOBS.update(job, result=result, status='finished', phase='done', progress=100, done=True)
            logger.info('[SINGLE %s] finished', job['task_id'])
    except Exception as exc:
        logger.exception('[SINGLE %s] failed', job['task_id'])
        message = '处理失败，请查看服务器日志（任务 ' + job['task_id'] + '）。'
        if 'out of memory' in str(exc).lower():
            message = 'GPU显存不足，请等待其他任务结束后重试（任务 ' + job['task_id'] + '）。'
        JOBS.update(job, status='failed', phase='failed', error=message, done=True)
    finally:
        close_old_connections()


def _launch(job, action):
    try:
        thread = threading.Thread(target=_run, args=(job, action), daemon=True,
                                  name='rgpas-single-' + job['task_id'][:12])
        thread.start()
    except Exception:
        JOBS.update(job, status='failed', done=True, error='无法启动后台任务，请稍后重试。')
        raise


def count_view(request):
    try:
        owner, info = _owner(request)
        if request.method == 'GET':
            if request.GET.get('task_id'):
                return _response(JOBS.get(owner, request.GET['task_id'], 'count'))
            return render(request, 'index.html', {'username': info['user']})
        if request.method != 'POST':
            raise JobError('仅支持POST提交或GET查询。', 405)
        model = request.POST.get('model')
        image = request.FILES.get('file')
        if model not in MODELS or not image:
            raise JobError('请选择有效的图片和检测模型。')
        filename = str(image.name).replace('\\', '/').rsplit('/', 1)[-1]
        task_id = _task_id(request.POST.get('task_id'))
        job, fresh = JOBS.begin(owner, task_id, 'count', (model, filename))
        if not fresh:
            return _response(job)
        try:
            v = _views()
            project, static = v.get_base_paths()
            directory = Path(static) / MODELS[model][0] / task_id
            directory.mkdir(parents=True, exist_ok=False)
            uploaded = directory / 'upload.bin'
            with uploaded.open('wb') as stream:
                for chunk in image.chunks():
                    stream.write(chunk)
            JOBS.update(job, context={'project': str(project), 'static': str(static), 'uploaded': str(uploaded),
                                     'filename': filename, 'model': model, 'user_info': info, 'analysis_id': task_id})
            request.session['single_analysis_id'] = task_id
            _launch(job, lambda: _count(job))
        except Exception:
            JOBS.update(job, status='failed', done=True, error='图片保存或任务启动失败，请查看服务器日志。')
            logger.exception('[SINGLE %s] could not accept upload', task_id)
        return _response(job)
    except JobError as exc:
        return _fail_response(exc)


def _count(job):
    v = _views()
    if not v.torch.cuda.is_available() or os.environ.get('RGPAS_DETECTION_DEVICE', '').lower() == 'cpu':
        raise RuntimeError('GPU不可用；单图修复流程不会自动切换为CPU，请检查CUDA环境。')
    ctx = job['context']
    static = Path(ctx['static'])
    img = v.cv2.imread(ctx['uploaded'])
    if img is None:
        raise ValueError('无法解码上传图片')
    # Match batch uploads: preserve the encoded image and its metadata. A JPEG
    # decode/encode round trip changes pixels and can change detection counts.
    source = Path(ctx['uploaded']).with_name('image' + Path(ctx['filename']).suffix.lower())
    shutil.copyfile(ctx['uploaded'], source)
    model = ctx['model']
    spec = MODELS[model]
    detect = v.get_detect_func(spec[2], spec[3], spec[4])
    JOBS.update(job, phase='detecting', progress=10)
    detection = detect(str(source), str(static / spec[1]), job['task_id'], return_details=True)
    # Keep the detector's actual directory. Never reconstruct it from a filename.
    image_url = static_file_url(detection.image_path, static)
    original_url = static_file_url(source, static)
    current_user = v.User.objects.get(user=ctx['user_info']['user'], role__role=ctx['user_info']['role'])
    record = v.Detection.objects.create(pic=ctx['filename'], target_pic=original_url,
                                        result_pic=image_url, user=current_user)
    ctx.update(save_dir=str(detection.save_dir), detection_id=record.id, total=int(detection.number))
    return {'analysis_id': job['task_id'], 'filename': ctx['filename'], 'model': model,
            'model_name': str(detection.number), 'image_number': str(detection.number),
            'result_pic': job['task_id'], 'result_url': image_url, 'original_url': original_url}


def extract_view(request):
    try:
        owner, _ = _owner(request)
        if request.method == 'GET':
            try:
                job = JOBS.get(owner, request.GET.get('task_id', ''), 'extract')
            except JobError:
                # A lost start response may have reused an already-finished job.
                count = JOBS.get(owner, request.GET.get('analysis_id', ''), 'count')
                job = JOBS.get(owner, count['context'].get('extraction_task_id', ''), 'extract')
            return _response(job)
        if request.method != 'POST':
            raise JobError('仅支持POST提交或GET查询。', 405)
        analysis_id = request.POST.get('analysis_id') or request.session.get('single_analysis_id')
        count = JOBS.get(owner, analysis_id, 'count')
        if count['status'] != 'finished':
            raise JobError('请先完成当前图片的计数。', 409)
        ctx = count['context']
        if request.POST.get('model') != ctx['model'] or request.POST.get('file') != ctx['filename']:
            raise JobError('图片或模型已改变，请重新计数。', 409)
        task_id = _task_id(request.POST.get('task_id'))
        with JOBS.lock:
            previous = JOBS.jobs.get(ctx.get('extraction_task_id'))
            if previous and (not previous['done'] or previous['status'] == 'finished'):
                return _response(previous)
            job, fresh = JOBS.begin(owner, task_id, 'extract', (analysis_id, ctx['model']))
            if fresh:
                ctx['extraction_task_id'] = task_id
        if fresh:
            JOBS.update(job, context=dict(ctx))
            _launch(job, lambda: _extract(job))
        return _response(job)
    except JobError as exc:
        return _fail_response(exc)


def _extract(job):
    v = _views()
    ctx = job['context']
    static = Path(ctx['static'])
    crops = Path(ctx['save_dir']) / 'panicle'
    if not crops.is_dir():
        alternate = Path(ctx['save_dir']) / 'crops' / 'panicle'
        if alternate.is_dir():
            crops = alternate
        elif ctx['total']:
            raise FileNotFoundError('当前检测任务的穗粒裁剪目录不存在')
    destination = static / ('single_' + ctx['model'] + '_complety') / ctx['analysis_id'] / job['task_id']
    masks = static / ('single_' + ctx['model'] + '_comp_mask') / ctx['analysis_id'] / job['task_id']
    destination.mkdir(parents=True, exist_ok=True)
    masks.mkdir(parents=True, exist_ok=True)
    # No previous success is overwritten; a failed attempt is not automatically rerun.
    image_ids = sorted(int(p.stem) for p in crops.glob('*.jpg') if p.stem.isdigit()) if crops.is_dir() else []
    clf, mapping, transform, device = v.load_eff_classifier()
    if not str(device).startswith('cuda'):
        raise RuntimeError('完整粒分类器必须使用GPU，请检查RGPAS_CLASSIFIER_DEVICE。')
    JOBS.update(job, phase='classifying', progress=5)
    # Reuse the GPU model serially, matching the repaired batch default.
    for index, image_id in enumerate(image_ids):
        item = v.process_single_image(image_id, str(crops), str(destination), str(masks), clf, mapping, transform)
        if item.get('status') == 'error':
            raise RuntimeError(item.get('message', '分类失败'))
        JOBS.update(job, progress=5 + int(65 * (index + 1) / max(len(image_ids), 1)))
    JOBS.update(job, phase='filtering', progress=72)
    images = sorted(p.name for p in destination.glob('*.jpg'))
    features = [v.extract_image_features(name, str(destination)) for name in images]
    selected = select_whole_grains(features, ctx['model'])
    for name in images:
        if name not in selected:
            (destination / name).unlink()
            mask = masks / (Path(name).stem + '.png')
            if mask.exists():
                mask.unlink()
    final = sorted((p.name for p in destination.glob('*.jpg')), key=lambda name: int(Path(name).stem))
    JOBS.update(job, phase='traits', progress=80)
    request = SimpleNamespace(session={'download_id': ctx['detection_id'], 'total_count': str(ctx['total'])})
    from django.db import transaction
    try:
        # One connection and transaction: no partial successful CSV after an error.
        with transaction.atomic():
            for index, name in enumerate(final):
                v.analyze_and_store_traits(name, str(destination), str(masks), request, threading.Lock())
                JOBS.update(job, progress=80 + int(18 * (index + 1) / max(len(final), 1)))
            v.Result.objects.create(select_model=ctx['model'], single_total=str(ctx['total']),
                                    single_completed=str(len(final)), image_id=ctx['detection_id'])
    finally:
        try:
            log_cuda_memory('single extraction completed')
        except Exception:
            logger.warning('Could not sample CUDA memory', exc_info=True)
    return {'analysis_id': ctx['analysis_id'], 'filename': ctx['filename'], 'model': ctx['model'],
            'sum': len(final), 'image_names': final,
            'complete_urls': [static_file_url(destination / name, static) for name in final]}


def select_whole_grains(features, model='spike-yolo'):
    """Preserve area and aspect-ratio thresholds; align each region to its image.

    The old slicing omitted the first file in each feature batch. Every image
    is now examined, including a single-image result and the zero-result case.
    """
    rows = []
    for feature in features:
        sizes, aspects = feature['size_list'], feature['lw_list']
        if len(sizes) != len(aspects):
            raise ValueError('表型特征数量不一致')
        for size, aspect in zip(sizes, aspects):
            if not math.isfinite(size) or not math.isfinite(aspect):
                raise ValueError('表型特征包含无效数值')
            rows.append((feature['name'], float(size), float(aspect)))
    if not rows:
        return set()
    size_mean = round(sum(row[1] for row in rows) / len(rows), 3)
    aspect_mean = round(sum(row[2] for row in rows) / len(rows), 3)
    lower, aspect_upper = (.8, 1.3) if model == 'spike-yolo' else (.85, 1.25)
    return {name for name, size, aspect in rows
            if size_mean * lower <= size <= size_mean * 1.5 and aspect <= aspect_mean * aspect_upper}


def detection_for_download(request):
    """Bind CSV to this session's completed single job, never global latest()."""
    owner, info = _owner(request)
    analysis_id = request.GET.get('analysis_id') or request.session.get('single_analysis_id')
    count = JOBS.get(owner, analysis_id, 'count')
    extraction = JOBS.get(owner, count['context'].get('extraction_task_id', ''), 'extract')
    if count['status'] != 'finished' or extraction['status'] != 'finished':
        raise JobError('请等待当前图片的完整粒提取完成。', 409)
    return _views().Detection.objects.get(pk=count['context']['detection_id'],
                                         user__user=info['user'], user__role__role=info['role'])
