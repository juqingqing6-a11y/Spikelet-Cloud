import os
import warnings

import cv2

warnings.filterwarnings('ignore')
from yolov8.ultralytics import YOLO
import os

current_directory = os.path.dirname(os.path.abspath(__file__))
# 使用__file__获取当前脚本的绝对路径

# 获取项目根目录的绝对路径（上一级目录）
project_root = os.path.dirname(current_directory)
weights_folder = os.path.join(project_root, 'weights')

from spike.batch_runtime import predict_cached
from spike.ulx_router import bind_ultralytics

def testYolov8(result_path, result_path_result, image, *, return_details=False):
    with bind_ultralytics('v8legacy'):
        return predict_cached(
            YOLO, os.path.join(weights_folder, 'yolov8m_raw.pt'),
            result_path, result_path_result, image, return_details=return_details,
        )

