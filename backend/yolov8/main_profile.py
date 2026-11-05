from yolov8.ultralytics import YOLO

if __name__ == '__main__':
    # choose your yaml file
    model = YOLO('yolov8/ultralytics/cfg/models/v8/yolov8n.yaml')
    model.info(detailed=True)
    model.profile(imgsz=[640, 640])
    model.fuse()