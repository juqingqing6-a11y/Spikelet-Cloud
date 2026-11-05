import io
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

import cv2
import numpy as np
from PIL import Image
from django.test import SimpleTestCase

from spike import single_runtime
from spike.batch_runtime import DetectionOutput


class SingleImageInputTests(SimpleTestCase):
    """Single-image detection must see the same upload bytes as batch detection."""

    def encoded_image(self, image_format, orientation=None):
        # Nonuniform pixels make an unintended lossy JPEG round trip observable.
        pixels = np.arange(67 * 91 * 3, dtype=np.uint8).reshape(67, 91, 3)
        image = Image.fromarray(pixels, mode='RGB')
        output = io.BytesIO()
        options = {'quality': 83} if image_format == 'JPEG' else {}
        if orientation is not None:
            exif = Image.Exif()
            exif[274] = orientation
            options['exif'] = exif
        image.save(output, format=image_format, **options)
        return output.getvalue()

    def run_count(self, root, filename, content, model):
        static = root / 'static'
        directory = static / 'single-input'
        directory.mkdir(parents=True)
        uploaded = directory / 'upload.bin'
        uploaded.write_bytes(content)
        task_id = 'test-input-preservation'
        detector_inputs = []

        def detect(source, output, name, *, return_details):
            source = Path(source)
            detector_inputs.append(source)
            result = Path(output) / name
            result.mkdir(parents=True)
            result_image = result / source.name
            shutil.copyfile(source, result_image)
            return DetectionOutput(188, str(result), str(result_image))

        views = SimpleNamespace(
            cv2=cv2,
            torch=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: True)),
            get_detect_func=Mock(return_value=detect),
            User=SimpleNamespace(objects=SimpleNamespace(get=Mock(return_value=object()))),
            Detection=SimpleNamespace(objects=SimpleNamespace(create=Mock(return_value=SimpleNamespace(id=1)))),
        )
        job = {'task_id': task_id, 'context': {
            'static': str(static), 'uploaded': str(uploaded), 'filename': filename,
            'model': model, 'user_info': {'user': 'test', 'role': '1'},
        }}
        with patch.object(single_runtime, '_views', return_value=views), \
                patch.dict('os.environ', {'RGPAS_DETECTION_DEVICE': '0'}):
            result = single_runtime._count(job)
        return result, job, views, detector_inputs, uploaded

    def test_all_models_preserve_jpeg_bytes_pixels_and_detector_arguments(self):
        content = self.encoded_image('JPEG')
        for model in single_runtime.MODELS:
            with self.subTest(model=model), tempfile.TemporaryDirectory() as temporary:
                result, job, views, inputs, uploaded = self.run_count(
                    Path(temporary), 'P_1.jpg', content, model,
                )
                self.assertEqual(inputs[0].read_bytes(), content)
                np.testing.assert_array_equal(cv2.imread(str(inputs[0])), cv2.imread(str(uploaded)))
                self.assertEqual(inputs[0].name, 'image.jpg')
                self.assertEqual(result['filename'], 'P_1.jpg')
                self.assertEqual(result['image_number'], '188')
                self.assertEqual(job['context']['total'], 188)
                self.assertTrue(result['original_url'].endswith('/image.jpg'))
                views.get_detect_func.assert_called_once_with(*single_runtime.MODELS[model][2:])

    def test_preserves_jpeg_exif_orientation_and_decoded_pixels(self):
        content = self.encoded_image('JPEG', orientation=8)
        with tempfile.TemporaryDirectory() as temporary:
            result, _, _, inputs, uploaded = self.run_count(
                Path(temporary), 'GP003_0.JPEG', content, 'spike-yolo',
            )
            self.assertEqual(inputs[0].read_bytes(), content)
            with Image.open(inputs[0]) as image:
                self.assertEqual(image.getexif()[274], 8)
            np.testing.assert_array_equal(cv2.imread(str(inputs[0])), cv2.imread(str(uploaded)))
            self.assertTrue(result['original_url'].endswith('/image.jpeg'))

    def test_png_remains_lossless_png_instead_of_becoming_jpeg(self):
        content = self.encoded_image('PNG')
        with tempfile.TemporaryDirectory() as temporary:
            result, _, _, inputs, _ = self.run_count(
                Path(temporary), 'grains.png', content, 'yolov8',
            )
            self.assertEqual(inputs[0].read_bytes(), content)
            self.assertEqual(inputs[0].suffix, '.png')
            with Image.open(inputs[0]) as image:
                self.assertEqual(image.format, 'PNG')
            self.assertTrue(result['original_url'].endswith('/image.png'))

    def test_invalid_image_is_rejected_before_detection(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, '无法解码'):
                self.run_count(Path(temporary), 'broken.jpg', b'not an image', 'spike-yolo')
