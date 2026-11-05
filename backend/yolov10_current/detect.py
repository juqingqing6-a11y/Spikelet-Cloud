import warnings
warnings.filterwarnings('ignore')

import sys
# sys.path.append(r'C:\Users\zzzj1\OneDrive\穗粒分析及云平台\云平台中的yolo模型\yolov8')  # ultralytics上级目录

# sys.modules.pop('ultralytics', None)

# 把你的 yolov10 目录插到 sys.path 最前面
# sys.path.insert(0, '/root/NAU/RiceGrain_Cloud/yolov10_current')

from .ultralytics import YOLO

import os

current_directory = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_directory)
weights_folder = os.path.join(project_root, 'weights')

from spike.batch_runtime import predict_cached
from spike.ulx_router import bind_ultralytics

def testYolov10m(result_path, result_path_result, image, *, return_details=False):
    with bind_ultralytics('v10'):
        return predict_cached(
            YOLO, os.path.join(weights_folder, 'Yolov10m-raw.pt'),
            result_path, result_path_result, image, return_details=return_details,
        )

def testYolov10(result_path, result_path_result, image, *, return_details=False):
    with bind_ultralytics('v10'):
        return predict_cached(
            YOLO, os.path.join(weights_folder, 'RGD-YOLO.pt'),
            result_path, result_path_result, image, return_details=return_details,
        )

