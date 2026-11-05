import torch
import numpy as np
import os
import sys
sys.path.append('D:/Program Files/spike_test/yolov5')
from yolov5.models.experimental import attempt_load
# from utils.general import non_max_suppression, scale_coords
from yolov5.utils.general import scale_boxes
from yolov5.utils.general import non_max_suppression
from yolov5.utils.torch_utils import select_device
import cv2
from random import randint
from yolov5.utils.augmentations import letterbox


class Detector(object):

    def __init__(self, save_folder=None):
        self.img_size = 640
        self.max_frame = 160
        self.init_model()
        if save_folder is None:
            self.save_folder = './static/images_yolov5/'  # 设置默认保存路径
        else:
            self.save_folder = save_folder

    # def init_model(self):
    #     self.weights = 'weights/yolov5.pt'
    #     self.device = '0' if torch.cuda.is_available() else 'cpu'
    #     self.device = select_device(self.device)
    #     model = attempt_load(self.weights, map_location=None)  # 设置 map_location 参数为 None
    #     model.to(self.device).eval()
    #     model.float()
    #     self.m = model
    #     self.names = model.module.names if hasattr(model, 'module') else model.names
    #     print(self.names)
    #     self.colors = [(randint(0, 255), randint(0, 255), randint(0, 255)) for _ in self.names]
    def init_model(self):
        self.weights = './weights/yolov5.pt'
        self.device = '0' if torch.cuda.is_available() else 'cpu'
        self.device = select_device(self.device)

        # model = attempt_load(self.weights, device=torch.device(self.device))

        model = attempt_load(self.weights, map_location=torch.device(self.device),
                             fuse=False)  # 设置 map_location 参数为设备
        # print(model)
        model.eval()
        self.m = model
        self.names = list(model.names.values())  # 将字典的值转换为列表
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

    # def plot_bboxes(self, image, bboxes, line_thickness=None):
    #     tl = line_thickness or round(
    #         0.002 * (image.shape[0] + image.shape[1]) / 2) + 1  # line/font thickness
    #     for (x1, y1, x2, y2, cls_id, conf) in bboxes:
    #         # 这串代码是设置边界框的颜色是随机的
    #         # color = self.colors[self.names.index(cls_id)]
    #         color = (0, 0, 255)  # 固定颜色是红色
    #         c1, c2 = (x1, y1), (x2, y2)
    #         cv2.rectangle(image, c1, c2, color,
    #                       thickness=tl, lineType=cv2.LINE_AA)
    #         tf = max(tl - 1, 1)  # font thickness
    #         t_size = cv2.getTextSize(
    #             cls_id, 0, fontScale=tl / 3, thickness=tf)[0]
    #         c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
    #         # 以下两串代码是在最后的测试图片上展示出置信度和类别名称
    #         cv2.rectangle(image, c1, c2, color, -1, cv2.LINE_AA)  # filled
    #         cv2.putText(image, '{}-{:.2f}'.format(cls_id, conf), (c1[0], c1[1] - 2), 0, tl / 3,
    #                     [225, 255, 255], thickness=tf, lineType=cv2.LINE_AA)
    #     return image
    # def plot_bboxes(self, image, bboxes, line_thickness=None):
    #     tl = line_thickness or round(0.002 * (image.shape[0] + image.shape[1]) / 2) + 1
    #     for idx, (x1, y1, x2, y2, cls_id, conf) in enumerate(bboxes, start=1):
    #         print(idx)
    #         color = (0, 0, 255)  # Fixed color is red
    #         c1, c2 = (x1, y1), (x2, y2)
    #         cv2.rectangle(image, c1, c2, color, thickness=tl, lineType=cv2.LINE_AA)
    #         tf = max(tl - 1, 1)  # Font thickness
    #         t_size = cv2.getTextSize(str(idx), 0, fontScale=tl / 3, thickness=tf)[0]
    #         c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
    #         # cv2.rectangle(image, c1, c2, color, -1, cv2.LINE_AA)  # Filled
    #         cv2.rectangle(image, c1, c2, (-1, -1, -1), -1, cv2.LINE_AA)  # 透明背景
    #         cv2.putText(image, str(idx), (c1[0], c1[1] - 2), cv2.FONT_HERSHEY_SIMPLEX, tl / 3, [0,255,0],
    #                     thickness=tf, lineType=cv2.LINE_AA)
    #     return image
    def plot_bboxes(self, image, bboxes, line_thickness=None):
        tl = line_thickness or round(0.002 * (image.shape[0] + image.shape[1]) / 2) + 1
        for idx, (x1, y1, x2, y2, cls_id, conf) in enumerate(bboxes, start=1):
            color = (0, 0, 255)  # 固定颜色是红色
            c1, c2 = (x1, y1), (x2, y2)
            cv2.rectangle(image, c1, c2, color, thickness=tl, lineType=cv2.LINE_AA)
            tf = max(tl - 1, 1)  # 字体粗细
            t_size = cv2.getTextSize(str(idx), 0, fontScale=tl / 5, thickness=tf)[0]
            text_position = (c1[0], c1[1] - t_size[1] - 3)
            cv2.rectangle(image, (text_position[0] - 2, text_position[1] - t_size[1] - 3),
                          (text_position[0] + t_size[0] + 2, text_position[1]), (-1, -1, -1), -1, cv2.LINE_AA)  # 透明背景
            # cv2.putText(image, str(idx), text_position, cv2.FONT_HERSHEY_SIMPLEX, tl / 5, [155, 205, 155],
            #             thickness=tf, lineType=cv2.LINE_AA)
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
        image_number = 0
        zm1 = 0
        zm2 = 0
        # sum = 0
        lst = []
        for det in pred:

            if det is not None and len(det):
                det[:, :4] = scale_boxes(img.shape[2:], det[:, :4], im0.shape).round()

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

        return im, image_info, image_number
