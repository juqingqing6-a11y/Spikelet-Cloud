import os
import torch
import numpy as np

from yolov7.models.experimental import attempt_load
# from utils.general import non_max_suppression, scale_coords
from yolov7.utils.general import scale_coords, non_max_suppression
from yolov7.utils.torch_utils import select_device
import cv2
from random import randint
from yolov7.utils.datasets import letterbox
from yolov7.models.common import MP


class Detector7(object):

    def __init__(self, save_folder=None):

        self.img_size = 640
        self.max_frame = 160
        self.init_model()
        if save_folder is None:
            self.save_folder = './static/images_yolov7/'  # 设置默认保存路径
        else:
            self.save_folder = save_folder


    def init_model(self):

        self.weights = 'D:/AAAAzhangmin/spike_test/weights/yolov7.pt'
        self.device = '0' if torch.cuda.is_available() else 'cpu'
        self.device = select_device(self.device)
        print(0)
        model = attempt_load(self.weights, map_location=torch.device(self.device))  # 设置 map_location 参数为设备
        print(model)
        model.eval()
        self.m = model
        print(2)
        self.names = model.module.names if hasattr(model, 'module') else model.names  # 将字典的值转换为列表
        print(self.names)
        self.colors = [(randint(0, 255), randint(0, 255), randint(0, 255)) for _ in self.names]

    def preprocess(self, img):

        img0 = img.copy()
        img = letterbox(img, new_shape=self.img_size)[0]
        img = img[:, :, ::-1].transpose(2, 0, 1)
        img = np.ascontiguousarray(img)
        img = torch.from_numpy(img).to(self.device)
        # img = img.float()
        img = img.float()  # 半精度
        img /= 255.0  # 图像归一化
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        return img0, img

    def plot_bboxes(self, image, bboxes, line_thickness=None):
        tl = line_thickness or round(
            0.002 * (image.shape[0] + image.shape[1]) / 2) + 1  # line/font thickness
        for (x1, y1, x2, y2, cls_id, conf) in bboxes:
            # 颜色是随机的
            # color = self.colors[self.names.index(cls_id)]
            color = (0, 0, 255)  # 设置为红色 (BGR格式)
            c1, c2 = (x1, y1), (x2, y2)
            cv2.rectangle(image, c1, c2, color,
                          thickness=tl, lineType=cv2.LINE_AA)
            tf = max(tl - 1, 1)  # font thickness
            t_size = cv2.getTextSize(
                cls_id, 0, fontScale=tl / 3, thickness=tf)[0]
            c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
            # 以下两串代码是在最后的测试图片上展示出置信度和类别名称
            # cv2.rectangle(image, c1, c2, color, -1, cv2.LINE_AA)  # filled
            # cv2.putText(image, '{}-{:.2f}'.format(cls_id, conf), (c1[0], c1[1] - 2), 0, tl / 3,
            #             [225, 255, 255], thickness=tf, lineType=cv2.LINE_AA)
        return image

    def detect(self, im, image_filename):

        im0, img = self.preprocess(im)

        pred = self.m(img, augment=False)[0]
        pred = pred.float()
        pred = non_max_suppression(pred, 0.3)

        pred_boxes = []
        image_info = {}

        count = 0
        index = 0
        zm1 = 0
        zm2 = 0
        # sum = 0
        image_number = 0
        lst = []
        for det in pred:

            if det is not None and len(det):
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                for *x, conf, cls_id in det:
                    lbl = self.names[int(cls_id)]
                    x1, y1 = int(x[0]), int(x[1])
                    x2, y2 = int(x[2]), int(x[3])
                    pred_boxes.append((x1, y1, x2, y2, lbl, conf))
                    count += 1
                    index += 1
                    key = '{}-{:02}'.format(lbl, count)
                    # key = lbl
                    # print("key是：",count)

                    image_info[key] = ['{}×{}'.format(x2 - x1, y2 - y1), np.round(float(conf), 3)]
                    # 获取当前处理图片的文件名
                    filename = os.path.splitext(os.path.basename(image_filename))[0]
                    folder_path = os.path.join(self.save_folder, filename)
                    os.makedirs(folder_path, exist_ok=True)  # 创建以文件名命名的文件夹
                    os.listdir(folder_path)
                    # 保存边界框到文件夹中
                    x1, y1 = int(x[0]), int(x[1])
                    x2, y2 = int(x[2]), int(x[3])
                    cropped_bbox = im[y1:y2, x1:x2]  # 裁剪边界框
                    image_number = image_number + 1
                    save_path = os.path.join(folder_path, f"{image_number}.jpg")
                    cv2.imwrite(save_path, cropped_bbox)  # 保存裁剪后的边界框
                    print(image_number)

        im = self.plot_bboxes(im, pred_boxes)
        print(im, image_info, image_number)
        return im, image_info, image_number
