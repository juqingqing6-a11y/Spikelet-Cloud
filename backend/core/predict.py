import cv2
import os

from processor.AIDetector_pytorch import Detector
from processor.AIDetector_pytorch5 import Detector5
from spike.models import Detection,Batches

from processor.AIDetector_pytorch_v7 import Detector7
from processor.AIDetector_pytorch_v77 import Detector77


def predict(dataset, model, ext):
    global img_y
    x = dataset[0].replace('\\', '/')
    file_name = dataset[1]
    print(file_name)

    print(ext)
    x = cv2.imread(x)  # 读取图片文件

    model = Detector()
    # print(threshold)

    # img_y, image_info = model.detect(x)
    # return image_info
    img_y, image_info, image_number = model.detect(x, file_name)
    # img_y, image_info = model.detect(x)
    # print(img_y)
    draw_path = '{}'.format(file_name[:-1])

    if os.path.exists('./static/images/'.format(draw_path)):

        pass
    else:
        os.makedirs('./static/images/'.format(draw_path))

    cv2.imwrite('./static/images/{}.{}'.format(file_name, ext), img_y)
    # 假设file_name是文件名，img_y是图片数据
    target_pic = './media/{}.{}'.format(file_name, ext)
    result_pic = './static/images/{}.{}'.format(file_name, ext)
    # Detection.objects.create(pic=file_name, target_pic=target_pic, result_pic=result_pic)

    return image_info, image_number

def predict5(dataset, model, ext):
    global img_y
    x = dataset[0].replace('\\', '/')
    file_name = dataset[1]

    x = cv2.imread(x)  # 读取图片文件

    model = Detector5()

    img_y, image_info, image_number = model.detect(x, file_name)
    print(file_name)

    draw_path = '{}'.format(file_name[:-1])

    if os.path.exists('./static/images_v5/'.format(draw_path)):

        pass
    else:
        os.makedirs('./static/images_v5/'.format(draw_path))

    cv2.imwrite('./static/images_v5/{}.{}'.format(file_name, ext), img_y)
    # 假设file_name是文件名，img_y是图片数据
    # target_pic = './batch/{}.{}'.format(file_name, ext)
    # result_pic = './static/images_v5/{}.{}'.format(file_name, ext)
    # folder_path = './static/complete_yolov5_batch/{}'.format(file_name)
    #
    # Batches.objects.create(pic=file_name, target_pic=target_pic, result_pic=result_pic, spike_pic=folder_path)

    return image_info, image_number
def predict7(dataset, model, ext):
    global img_y
    x = dataset[0].replace('\\', '/')
    file_name = dataset[1]
    print(file_name)

    print(ext)
    x = cv2.imread(x)  # 读取图片文件

    model = Detector7()
    # print(threshold)

    # img_y, image_info = model.detect(x)
    # return image_info
    img_y, image_info, image_number = model.detect(x, file_name)
    # print(img_y)
    draw_path = '{}'.format(file_name[:-1])

    if os.path.exists('./static/images/'.format(draw_path)):

        pass
    else:
        os.makedirs('./static/images/'.format(draw_path))

    cv2.imwrite('./static/images/{}.{}'.format(file_name, ext), img_y)
    # 假设file_name是文件名，img_y是图片数据
    target_pic = './media/{}.{}'.format(file_name, ext)
    result_pic = './static/images/{}.{}'.format(file_name, ext)
    # Detection.objects.create(pic=file_name, target_pic=target_pic, result_pic=result_pic)
    return image_info, image_number


def predict77(dataset, model, ext):
    global img_y
    x = dataset[0].replace('\\', '/')
    file_name = dataset[1]
    x = cv2.imread(x)  # 读取图片文件

    model = Detector77()
    # print(threshold)

    # img_y, image_info = model.detect(x)
    # return image_info
    img_y, image_info, image_number = model.detect(x, file_name)
    # print(img_y)
    draw_path = '{}'.format(file_name[:-1])

    if os.path.exists('./static/images_batch/'.format(draw_path)):

        pass
    else:
        os.makedirs('./static/images_batch/'.format(draw_path))

    cv2.imwrite('./static/images_batch/{}.{}'.format(file_name, ext), img_y)
    # 假设file_name是文件名，img_y是图片数据
    target_pic = './batch/{}.{}'.format(file_name, ext)
    result_pic = './static/images_batch/{}.{}'.format(file_name, ext)
    folder_path = './static/images_yolov7_batch/{}'.format(file_name)

    # Batches.objects.create(pic=file_name, target_pic=target_pic, result_pic=result_pic, spike_pic=folder_path)
    return image_info, image_number
