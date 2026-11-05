import warnings
warnings.filterwarnings('ignore')

import sys
# sys.path.append(r'C:\Users\zzzj1\OneDrive\穗粒分析及云平台\云平台中的yolo模型\yolov8')  # ultralytics上级目录

sys.modules.pop('ultralytics', None)

# 把你的 yolov10 目录插到 sys.path 最前面
sys.path.insert(0, '/root/NAU/RiceGrain_Cloud/yolov8_current')

from ultralytics import YOLO

import os

current_directory = os.path.dirname(os.path.abspath(__file__))
# 使用__file__获取当前脚本的绝对路径

# 获取项目根目录的绝对路径（上一级目录）
project_root = os.path.dirname(current_directory)
weights_folder = os.path.join(project_root, 'weights')

def testYolov8(result_path, result_path_result, image):
    model = YOLO(os.path.join(weights_folder, 'Yolov8m-raw.pt')) 
    results_list = model.predict(source=result_path,
                                 imgsz=640,
                                 project=result_path_result,
                                 name=image,
                                 save=True,
                                 show_labels=False,
                                 show_conf=False,
                                 line_width=2,
                                 save_crop=True,
                                 verbose=False)
    # 获取计数结果

    number = results_list[0].number
    return number