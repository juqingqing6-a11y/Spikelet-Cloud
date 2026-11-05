import warnings
warnings.filterwarnings('ignore')
from yolov8.ultralytics import YOLO

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

if __name__ == '__main__':

    # model = YOLO('ultralytics/cfg/models/v8/yolov8s-bifpn.yaml')
    # model = YOLO('ultralytics/cfg/models/v8/yolov8s.yaml')
    model = YOLO('yolov8/ultralytics/cfg/models/v8/yolov8s-bifpn-attention.yaml')
    model.load('yolov8s.pt') # loading pretrain weights
    model.train(data='dataset/data_spike.yaml',
                cache=False,
                imgsz=640,
                epochs=100,
                batch=8,
                close_mosaic=10,
                workers=0,
                device='0',
                optimizer='SGD', # using SGD
                # resume='', # last.pt path
                amp=False, # close amp
                # fraction=0.2,
                project='runs/train',
                name='exp',
                )