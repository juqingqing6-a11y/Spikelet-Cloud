from __future__ import print_function, division
from PIL import Image, ImageOps

import os
import sys
import zipfile
import tempfile
from datetime import datetime
# sys.path.append('/root/NAU/RiceGrain-cloud20250110/yolov8')   #服务器中的文件位置
# sys.path.append('D:/shanghai_grain/yolo_family/cloud_test/spike20240525/yolov8')

# from yolov8_current.detect import testYolov8
# from yolov10_current.detect import testYolov10m, testYolov10
from .ulx_router import bind_ultralytics, get_detect_func
from yolov8.detect import testYolov8

import csv

import cv2

# 导入相关库
import numpy as np # 数据处理库
from scipy import ndimage # 数据处理库
import pandas as pd
import skimage.io as sk_io # 用于读写图像
from skimage.transform import rescale, rotate, resize # 用于标定图像的宽和高

from skimage.measure import label, regionprops # 用于连通域分析
from skimage.filters import threshold_otsu, threshold_local # 用于阈值分割
# 形态学处理相关库
from skimage.morphology import skeletonize # 用提取于二维骨架
from skimage.morphology import erosion, dilation, opening, closing, remove_small_holes, convex_hull_image, remove_small_objects, binary_erosion
from skimage.morphology import disk
from skimage.segmentation import clear_border
from skimage import feature, filters
from skimage import morphology, measure
from skimage import draw
from scipy.spatial import distance
from skimage import util
from skimage.feature import corner_harris, corner_subpix, corner_peaks
from skimage.segmentation import clear_border, felzenszwalb, quickshift

import math

from skimage import color
from skimage.filters import unsharp_mask
from skimage import exposure
from skimage.exposure import match_histograms
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from tqdm import tqdm
import re
import torch
from django.utils.encoding import smart_str

from torch.autograd import Variable
from torchvision import datasets, transforms
import torchvision
import torch.nn as nn

from spike.models import User
from spike import models
from django.views.decorators.csrf import csrf_exempt
import os
from .models import Batches, Download, Detection, Single, Result, Results, Group, RiceGenotype

# Create your views here.
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.db import transaction
from django.core.paginator import Paginator
from django.views.decorators.http import condition


import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

# views.py 顶部 import 区域附近
import time, threading, json
import logging
import traceback
import uuid
from pathlib import Path
from django.conf import settings
from django.http import FileResponse
from .batch_runtime import (
    batch_slot, clear_detector_cache, log_cuda_memory,
    result_payload, static_file_url,
)
from .db_runtime import run_db_worker
logger = logging.getLogger("django.rgpas.batch")
_ACTIVE_BATCHES = set()
_ACTIVE_BATCHES_LOCK = threading.Lock()
from django.http import StreamingHttpResponse

# 简易线程安全的进度存储（按 session_key 存）
_PROGRESS = {}
_PROGRESS_LOCK = threading.Lock()

def _ensure_session_key(request):
    sk = request.session.session_key
    if not sk:
        request.session.save()
        sk = request.session.session_key
    return sk

def progress_set(session_key, **kwargs):
    with _PROGRESS_LOCK:
        now = time.time()
        d = _PROGRESS.get(session_key, {})
        d.update(kwargs)
        d['ts'] = now
        _PROGRESS[session_key] = d
        for old_key, old_state in list(_PROGRESS.items()):
            if old_state.get('done') and now - old_state.get('ts', now) > 3600:
                _PROGRESS.pop(old_key, None)

def progress_get(session_key):
    with _PROGRESS_LOCK:
        return _PROGRESS.get(session_key, {}).copy()

def progress_clear(session_key):
    with _PROGRESS_LOCK:
        _PROGRESS.pop(session_key, None)


### 原始开始  ###
def logout_view(request):
    logout(request)
    return redirect('/')  # 这里的 'login' 应该是您登录视图的URL名称

@csrf_exempt
def login(request):
    if request.method == 'GET':
        return render(request, "login.html")

    email = request.POST.get('email')

    password = request.POST.get('password')

    login_type = request.POST.get('login_type')
    # 根据登录类型选择角色
    role = '1' if login_type == 'user' else '0'


    try:
        user_record = models.User.objects.get(email=email,role__role=role)
    except models.User.DoesNotExist:
        user_record = None

    if user_record is not None:
        if user_record.password == password:
            # 用户登录成功，生成 JWT token
            refresh = RefreshToken.for_user(user_record)
            # 获取JWT token字符串
            token = str(refresh.access_token)

            # # 存储用户名在会话中
            # request.session['username'] = user_record.user
            # # 存储用户角色
            # request.session['role'] = user_record.role
            # 将用户信息的字典表示保存到 session 中
            request.session['user_info'] = user_record.to_dict()
            return redirect('index')

        else:
            return render(request, "login.html", {"error_msg": "The user has already registered, but the email or password is incorrect. Please re-enter!"})
    else:
        return render(request, "login.html", {"error_msg": "The user is not registered. Please register first!"})


from django.http import JsonResponse


@csrf_exempt
def forget(request):
    if request.method == 'POST':
        user = request.POST.get('username')
        email = request.POST.get('email')

        # 在数据库中查找匹配的用户记录
        try:
            user_record = User.objects.get(user=user, email=email)
            password = user_record.password  # 获取用户密码

            # 如果成功找到用户，可以返回一个成功的状态和密码
            response_data = {
                'success': True,
                'password': password
            }
            return JsonResponse(response_data)
        except User.DoesNotExist:
            # 如果找不到匹配的用户记录，返回一个失败的状态和错误消息
            response_data = {
                'success': False,
                'message': 'The user does not exist or the email address does not match!'
            }
            return JsonResponse(response_data)

    return render(request, "login.html")


@csrf_exempt
def register(request):
    if request.method == 'GET':
        return render(request, "register.html")
    user = request.POST.get('username')
    password = request.POST.get('password')
    email = request.POST.get('email')

     # 邮箱验证：必须包含 .edu 或 .ac
    if not re.search(r'\.(edu|ac)(\.[a-z]+)?$', email, re.IGNORECASE):
        return JsonResponse({'success': False, 'message': 'The email address must be an academic email address (.edu or .ac).'})
    
    if len(password) < 10:
        return JsonResponse({'success': False, 'message': 'The password must be more than 10 characters'})

    # 密码验证：长度 >= 10 且至少包含三类字符
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'[0-9]', password))
    has_special = bool(re.search(r'[^A-Za-z0-9\u4e00-\u9fa5]', password))  # 特殊字符

    if not (has_upper and has_lower and has_digit and has_special):
        return JsonResponse({'success': False, 'message': 'The password must contain the following simultaneously: uppercase letters, lowercase letters, numbers, and special characters.'})

    user_records = models.User.objects.filter(email=email)
    if user_records:

        response_data = {
            'success': True,
            'message': 'The user has already registered. Please log in directly!'
        }
        return JsonResponse(response_data)

    ###获取或创建Group实例，假设role_id为1的group已经存在###
    role_instance = Group.objects.get(role='1')
    User.objects.create(user=user, password=password, email=email, role=role_instance)

    response_data = {
        'success': True,
        'message': 'Congratulations! Your registration is successful. Please return to the login page!'
    }
    return JsonResponse(response_data)


@csrf_exempt
def index(request):
    # 检查用户是否已登录
    if 'user_info' in request.session:
        user_info = request.session.get('user_info')
        username = user_info['user']
        role = user_info['role']
    else:
        # 用户未登录，您可以选择如何处理，例如，重定向到登录页面
        return redirect('/')
    if request.method == 'POST':
        img = request.FILES.get('file')
        option = request.POST.get('model')
        img_path = os.path.join('media', img.name)
        with open(img_path, 'wb') as f:
            for chunk in img.chunks():
                f.write(chunk)
        if option == 'spike-yolo':
            y_rf = 'spike-yolo'
            return JsonResponse({'model_name': y_rf})
        ####新增初始的yolov8s模型####
        elif option == 'yolov8':
            y_rf = 'yolov8'
            return JsonResponse({'model_name': y_rf})
        ####新增初始的yolov8s模型结束####
        ####新增初始的yolov10s模型#####
        elif option == 'yolov10':
            y_rf = 'yolov10'
            return JsonResponse({'model_name': y_rf})
        ####新增初始的yolov10s模型结束#####

    return render(request, 'index.html', {'username': username, 'user_info': user_info})


def user_show(request):
    data_list = User.objects.all()
    # 检查用户是否已登录
    # if 'username' in request.session:
    if 'user_info' in request.session:
        user_info = request.session.get('user_info')
        username = user_info['user']
        role = user_info['role']
        # username = request.session.get('username')
    else:
        # 用户未登录，您可以选择如何处理，例如，重定向到登录页面
        return redirect('/')
    return render(request, "user_show.html", {'username': username, "data_list": data_list,'user_info': user_info})


def user_add(request):
    # username = request.session.get('username')
    user_info = request.session.get('user_info')
    username = user_info['user']
    if request.method == 'GET':
        return render(request, "user_add.html", {'username': username})
    user = request.POST.get('user')
    password = request.POST.get('password')
    email = request.POST.get('email')
    eml = models.User.objects.filter(email=email)
    if email == "" or password == "" or user == "":
        return render(request, "user_add.html", {"error_msg": "以上信息均不可为空，请重新填写"})
    if eml:
        return render(request, "user_add.html", {"error_msg": "邮箱已存在"})
    User.objects.create(user=user, password=password, email=email)
    return redirect("/user_show/")


def user_delete(request):
    nid = request.GET.get('nid')
    models.User.objects.filter(id=nid).delete()
    return redirect("/user_show/")


def user_edit(request, nid):
    if request.method == 'GET':
        user_info = request.session.get('user_info')
        username = user_info['user']
        data_list = models.User.objects.filter(id=nid).first()
        return render(request, "user_edit.html", {'username': username, "data_list": data_list,'user_info': user_info})
    email = request.POST.get('email')
    password = request.POST.get('password')
    models.User.objects.filter(id=nid).update(email=email, password=password)
    return redirect("/user_show/")


def sort(request):
    # username = request.session.get('username')
    user_info = request.session.get('user_info')
    username = user_info['user']
    return render(request, "sort.html", {'username': username})

### 将性状分析封装为函数 ###

def get_base_paths():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_directory)
    static_folder = os.path.join(project_root, 'static')
    # model_folder = os.path.join(project_root, 'models')
    return project_root, static_folder

def clear_folder(folder_path):
    import shutil
    """
    清空指定文件夹中的所有内容
    :param folder_path: 需要清空的文件夹路径
    """
    try:
        # 如果文件夹存在
        if os.path.exists(folder_path):
            # 删除文件夹及其所有内容
            shutil.rmtree(folder_path)
            # 重新创建空文件夹
            os.makedirs(folder_path)
            print(f"成功清空文件夹: {folder_path}")
        else:
            # 如果文件夹不存在，创建它
            os.makedirs(folder_path)
            print(f"文件夹不存在，已创建: {folder_path}")
    except Exception as e:
        print(f"清空文件夹时发生错误: {str(e)}")


# 将单个图像的处理封装为一个函数
@torch.inference_mode()
def process_single_image(i, folder_path, destination_folder, des_mask_folder, model, mapping, data_transforms):
    """
    处理单张图像的完整流程，包括图像分割、特征提取和保存
    Args:
        i: 图像序号
        folder_path: 源图像文件夹路径
        destination_folder: 目标图像保存路径
        des_mask_folder: 掩码图像保存路径
        model: 预训练的分类模型
        mapping: 标签映射
        data_transforms: 图像变换函数
    """

    try:
        image_name = f"{i}.jpg"  # 构建图片文件名
        mask_name = f"{i}.png"

        img_path = os.path.join(folder_path, image_name)  # 构建完整的文件路径
        # 读取图像
        image = sk_io.imread(img_path)
        image_bag_r = image[:, :, 0]

        # 自适应阈值分割
        thre_bag_r = threshold_otsu(image_bag_r)
        grain_mask = image_bag_r > thre_bag_r
        grain_mask = remove_small_objects(grain_mask, min_size=100)
        grain_part = cutout_plant_from_original(image, grain_mask)

        # 其余处理代码（gamma调整、边界扩展等）
        if grain_part.mean() < 55:
            gam = exposure.adjust_gamma(grain_part, 2)  # 调暗
        elif 55 <= grain_part.mean() < 80:
            gam = exposure.adjust_gamma(grain_part, 3)  # 调暗
        elif 80 <= grain_part.mean() < 115:
            gam = exposure.adjust_gamma(grain_part, 4)  # 调暗
        elif grain_part.mean() >= 115:
            gam = exposure.adjust_gamma(grain_part, 5)  # 调暗

        ret = cv2.copyMakeBorder(gam, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        ret_img = cv2.copyMakeBorder(grain_part, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=(0, 0, 0))

        image_bag_r = ret[:, :, 0]
        thre_bag_r = threshold_otsu(image_bag_r)
        grain_mask_ret = image_bag_r > thre_bag_r

        gray_image = ret[:, :, 0] * grain_mask_ret
        color_image = cv2.applyColorMap(gray_image, cv2.COLORMAP_JET)
        color_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)

        ratio_list = range(2, 12, 2)
        processed = False

        for n, ratio in enumerate(ratio_list):
            segments_fz = felzenszwalb(color_image, scale=10, sigma=0.05,
                                       min_size=int(np.sum(grain_mask_ret > 0) / ratio))
            grain_props = measure.regionprops_table(segments_fz, color.rgb2gray(ret),
                                                    properties=['bbox', 'image'], cache=True)
            grain_data = pd.DataFrame(grain_props)

            for idx in grain_data.index:
                # 获取边界框坐标
                min_row = grain_data.loc[idx, 'bbox-0']
                min_col = grain_data.loc[idx, 'bbox-1']
                max_row = grain_data.loc[idx, 'bbox-2']
                max_col = grain_data.loc[idx, 'bbox-3']

                # 调整掩码大小
                mask_b = resize(grain_data.loc[idx, 'image'],
                                (max_row - min_row, max_col - min_col))

                if mask_b.sum() < 650:
                    continue

                # 8. 形态学处理
                mask_b = dilation(mask_b, disk(1))
                big_grain = (color.gray2rgb(mask_b) * ret_img[min_row:max_row, min_col:max_col]).astype('int')

                # 9. 分类预测
                big_grain = Image.fromarray(big_grain.astype('uint8'), mode='RGB')
                inputs = data_transforms(big_grain)
                inputs.unsqueeze_(0)
                inputs = inputs.to(next(model.parameters()).device)
                outputs = model(inputs)
                _, preds = torch.max(outputs, 1)
                class_name = [k for (k, v) in mapping.items() if v == preds.item()]

                if class_name == ['1']:
                    # 10. 后处理
                    mask_b = remove_small_holes(mask_b, area_threshold=5)
                    mask_b = erosion(mask_b, disk(3))
                    mask_b = dilation(mask_b, disk(3))
                    mask_b = remove_small_objects(mask_b, min_size=200)
                    mask_b = mask_b.astype('uint8')
                    mask_b = cv2.GaussianBlur(mask_b, (0, 0), sigmaX=3, sigmaY=3,
                                              borderType=cv2.BORDER_DEFAULT)
                    mask_b = mask_b.astype(bool)

                    # 11. 生成最终图像
                    big_grain = (color.gray2rgb(mask_b) * ret_img[min_row:max_row, min_col:max_col]).astype('int')
                    big_grain = Image.fromarray(big_grain.astype('uint8'), mode='RGB')
                    big_grain = ImageOps.expand(big_grain, border=5, fill=(0, 0, 0))

                    # 12. 保存结果
                    output_path = os.path.join(destination_folder, image_name)
                    mask_output_path = os.path.join(des_mask_folder, mask_name)

                    if not os.path.exists(output_path):
                        big_grain.save(output_path)
                        sk_io.imsave(mask_output_path, mask_b)
                        processed = True
                        break  # 成功处理后跳出内层循环
            if processed:
                break  # 成功处理后跳出外层循环
        return {
            'image_name': image_name,
            'processed': processed,
            'status': 'success',
            'message': f"图像 {image_name} 处理{'成功' if processed else '未找到有效特征'}"
        }

    except torch.cuda.OutOfMemoryError:
        raise
    except Exception as e:
        # 错误处理
        return {
            'image_name': image_name,
            'processed': False,
            'status': 'error',
            'message': f"处理图像 {image_name} 时发生错误: {str(e)}"
        }

def extract_image_features(image_name, destination_folder):
    img_path = os.path.join(destination_folder, image_name)
    image = sk_io.imread(img_path)
    image_bag_lab = color.rgb2lab(image)
    image_bag_l = image_bag_lab[:, :, 0]
    thre_bag_l = threshold_otsu(image_bag_l)
    thre_l_mask = image_bag_l > thre_bag_l
    grain_mask = remove_small_objects(thre_l_mask, min_size=thre_l_mask.sum() / 5)
    label_img = label(grain_mask)
    regions = regionprops(label_img)

    # 局部特征列表
    local_size_list = []
    local_round_list = []
    local_lw_list = []

    for props in regions:
        pi = math.pi
        area = props.area
        local_size_list.append(area)
        perimeter = props.perimeter
        diameter = props.equivalent_diameter
        roundness = round((4 * pi * area) / (perimeter * perimeter), 3)
        local_round_list.append(roundness)
        major_length = props.major_axis_length  # length
        minor_length = props.minor_axis_length  # width
        if minor_length == 0:
            lw = 0
        else:
            lw = round(major_length / minor_length, 3)  # 长宽比
        local_lw_list.append(lw)

    return {
        'name': image_name,
        'size_list': local_size_list,
        'round_list': local_round_list,
        'lw_list': local_lw_list
    }


def analyze_and_store_traits(img_name, destination_folder, des_mask_folder, request, lock):
    analyse_img_path = os.path.join(destination_folder, img_name)
    analyse_img = sk_io.imread(analyse_img_path)

    get_img_name = img_name.split('.')[0]
    analyse_mask_path = os.path.join(des_mask_folder, get_img_name + '.png')
    analyse_mask = sk_io.imread(analyse_mask_path)

    # 特征提取
    grain_label, num = label(analyse_mask, return_num=True)
    regions = regionprops(grain_label)

    result_data = []

    for props in regions:
        area = props.area
        minor_axis_length = props.minor_axis_length
        major_axis_length = props.major_axis_length
        perimeter = props.perimeter
        circularity = (4 * math.pi * area) / (perimeter ** 2)
        compacthness = (perimeter ** 2) / area  # 紧致度
        diameter = 2 * ((area / math.pi) ** (1 / 2))

        if (major_axis_length != 0 and minor_axis_length != 0):
            if major_axis_length > minor_axis_length:
                length = major_axis_length
                width = minor_axis_length
                l_w = length / width
                eccentricity = np.sqrt(1.0 - (width / length) ** 2)
            else:
                length = minor_axis_length
                width = minor_axis_length
                l_w = length / width
                eccentricity = np.sqrt(1.0 - (width / length) ** 2)
        else:
            l_w = 0
            eccentricity = 0

        from skimage import img_as_ubyte  # 标定图像格式
        big_grain = img_as_ubyte(analyse_img)
        red_mean = big_grain[:, :, 0].sum() / area
        green_mean = big_grain[:, :, 1].sum() / area
        blue_mean = big_grain[:, :, 2].sum() / area

        img_hsv = color.rgb2hsv(big_grain)
        hsv_h = img_hsv[:, :, 0].sum() / area
        hsv_s = img_hsv[:, :, 1].sum() / area
        hsv_v = img_hsv[:, :, 2].sum() / area

        img_lab = color.rgb2lab(big_grain)
        lab_l = img_lab[:, :, 0].sum() / area
        lab_a = img_lab[:, :, 1].sum() / area
        lab_b = img_lab[:, :, 2].sum() / area

        ratio = 0.283

        format_area = "{:.3f}".format(area * (ratio ** 2))
        format_length = "{:.3f}".format(length * ratio)
        format_width = "{:.3f}".format(width * ratio)
        format_l_w = "{:.3f}".format(l_w)
        format_diameter = "{:.3f}".format(diameter * ratio)
        format_perimeter = "{:.3f}".format(perimeter * ratio)
        format_circularity = "{:.3f}".format(circularity)
        format_compactness = "{:.3f}".format(compacthness)
        format_eccentricity = "{:.3f}".format(eccentricity)
        format_red_mean = "{:.0f}".format(red_mean)
        format_green_mean = "{:.0f}".format(green_mean)
        format_blue_mean = "{:.0f}".format(blue_mean)
        format_hsv_h = "{:.1f}".format(hsv_h)
        format_hsv_s = "{:.1f}".format(hsv_s)
        format_hsv_v = "{:.1f}".format(hsv_v)
        format_lab_l = "{:.1f}".format(lab_l)
        format_lab_a = "{:.1f}".format(lab_a)
        format_lab_b = "{:.1f}".format(lab_b)

        # 需要返回的数据字典
        trait_data = {
            'area': format_area,
            'length': format_length,
            'width': format_width,
            'l_w': format_l_w,
            'diameter': format_diameter,
            'perimeter': format_perimeter,
            'circularity': format_circularity,
            'compactness': format_compactness,
            'eccentricity': format_eccentricity,
            'red_mean': format_red_mean,
            'green_mean': format_green_mean,
            'blue_mean': format_blue_mean,
            'hsv_h': format_hsv_h,
            'hsv_s': format_hsv_s,
            'hsv_v': format_hsv_v,
            'lab_l': format_lab_l,
            'lab_a': format_lab_a,
            'lab_b': format_lab_b
        }
        result_data.append(trait_data)

    # 使用锁确保数据库操作的线程安全
    with lock:
        # 从会话中获取对象的ID
        download_id = request.session.get('download_id')
        # total_count = request.session.get('total_count', 0)
        # 使用ID获取对象
        download_instance = Detection.objects.get(pk=download_id)

        # 批量创建对象
        for trait_data in result_data:
            Single.objects.create(
                area=trait_data['area'],
                length=trait_data['length'],
                width=trait_data['width'],
                l_w=trait_data['l_w'],
                diameter=trait_data['diameter'],
                perimeter=trait_data['perimeter'],
                circularity=trait_data['circularity'],
                compactness=trait_data['compactness'],
                eccentricity=trait_data['eccentricity'],
                red_mean=trait_data['red_mean'],
                green_mean=trait_data['green_mean'],
                blue_mean=trait_data['blue_mean'],
                hsv_h=trait_data['hsv_h'],
                hsv_s=trait_data['hsv_s'],
                hsv_v=trait_data['hsv_v'],
                lab_l=trait_data['lab_l'],
                lab_a=trait_data['lab_a'],
                lab_b=trait_data['lab_b'],
                image_id=download_instance.id
            )

    return {'img_name': img_name, 'trait_count': len(result_data)}

def batch_analyze_and_store_traits(img_name, destination_folder, des_mask_folder, request, lock):
    try:
        # 初始化性状列表
        area_full_list = []
        length_full_list = []
        width_full_list = []
        lw_full_list = []
        cir_full_list = []
        dia_full_list = []
        per_full_list = []
        ecc_full_list = []
        comp_full_list = []
        red_full_list = []
        green_full_list = []
        blue_full_list = []
        hue_full_list = []
        sat_full_list = []
        val_full_list = []
        l_full_list = []
        a_full_list = []
        b_full_list = []

        # 设置比例系数
        ratio = 0.283
        
        # 读取图像
        analyse_img_path = os.path.join(destination_folder, img_name)
        analyse_img = sk_io.imread(analyse_img_path)

        get_img_name = img_name.split('.')[0]
        analyse_mask_path = os.path.join(des_mask_folder, get_img_name + '.png')
        analyse_mask = sk_io.imread(analyse_mask_path)

        # 特征提取
        grain_label, num = label(analyse_mask, return_num=True)
        regions = regionprops(grain_label)
        
        grain_count = 0  # 计数器
        all_traits = []

        for props in regions:

            grain_count += 1

            area = props.area
            minor_axis_length = props.minor_axis_length
            major_axis_length = props.major_axis_length
            perimeter = props.perimeter
            circularity = (4 * math.pi * area) / (perimeter ** 2)
            compacthness = (perimeter ** 2) / area  # 紧致度

            ###add traits###
            diameter = 2 * ((area / math.pi) ** (1 / 2))

            if (major_axis_length != 0 and minor_axis_length != 0):
                if major_axis_length > minor_axis_length:
                    length = major_axis_length
                    width = minor_axis_length
                    l_w = length / width
                    eccentricity = np.sqrt(1.0 - (width / length) ** 2)
                else:
                    length = minor_axis_length
                    width = major_axis_length
                    l_w = length / width
                    eccentricity = np.sqrt(1.0 - (width / length) ** 2)
            else:
                l_w = 0
                eccentricity = 0

            # 颜色特征提取
            from skimage import img_as_ubyte
            big_grain = img_as_ubyte(analyse_img)
            red_mean = big_grain[:, :, 0].sum() / area
            green_mean = big_grain[:, :, 1].sum() / area
            blue_mean = big_grain[:, :, 2].sum() / area

            img_hsv = color.rgb2hsv(big_grain)
            hsv_h = img_hsv[:, :, 0].sum() / area
            hsv_s = img_hsv[:, :, 1].sum() / area
            hsv_v = img_hsv[:, :, 2].sum() / area

            ### add lab###
            img_lab = color.rgb2lab(big_grain)
            lab_l = img_lab[:, :, 0].sum() / area
            lab_a = img_lab[:, :, 1].sum() / area
            lab_b = img_lab[:, :, 2].sum() / area

            # 计算实际值
            act_area = area * ratio * ratio
            act_length = length * ratio
            act_width = width * ratio
            act_dia = diameter * ratio
            act_per = perimeter * ratio

            # 添加到性状列表
            area_full_list.append(act_area)
            length_full_list.append(act_length)
            width_full_list.append(act_width)
            lw_full_list.append(l_w)
            dia_full_list.append(diameter)
            ecc_full_list.append(eccentricity)
            per_full_list.append(perimeter)
            cir_full_list.append(circularity)
            comp_full_list.append(compacthness)
            red_full_list.append(red_mean)
            green_full_list.append(green_mean)
            blue_full_list.append(blue_mean)
            hue_full_list.append(hsv_h)
            sat_full_list.append(hsv_s)
            val_full_list.append(hsv_v)
            l_full_list.append(lab_l)
            a_full_list.append(lab_a)
            b_full_list.append(lab_b)

            # 格式化单个粒的性状数据并存储到数据库
            format_data = {
                'area': "{:.3f}".format(act_area),
                'length': "{:.3f}".format(act_length),
                'width': "{:.3f}".format(act_width),
                'l_w': "{:.3f}".format(l_w),
                'diameter': "{:.3f}".format(act_dia),
                'perimeter': "{:.3f}".format(act_per),
                'circularity': "{:.3f}".format(circularity),
                'eccentricity': "{:.3f}".format(eccentricity),
                'compactness': "{:.3f}".format(compacthness),
                'red_mean': "{:.0f}".format(red_mean),
                'green_mean': "{:.0f}".format(green_mean),
                'blue_mean': "{:.0f}".format(blue_mean),
                'hsv_h': "{:.1f}".format(hsv_h),
                'hsv_s': "{:.1f}".format(hsv_s),
                'hsv_v': "{:.1f}".format(hsv_v),
                'lab_l': "{:.1f}".format(lab_l),
                'lab_a': "{:.1f}".format(lab_a),
                'lab_b': "{:.1f}".format(lab_b)
            }

            # 使用锁确保数据库操作的线程安全
            with lock:
                try:
                    # 获取download_instance
                    download_id = request.session.get('download_id')
                    download_instance = Batches.objects.get(pk=download_id)

                    # 创建Download记录
                    Download.objects.create(
                        area=format_data['area'],
                        length=format_data['length'],
                        width=format_data['width'],
                        l_w=format_data['l_w'],
                        diameter=format_data['diameter'],
                        perimeter=format_data['perimeter'],
                        circularity=format_data['circularity'],
                        eccentricity=format_data['eccentricity'],
                        compactness=format_data['compactness'],
                        red_mean=format_data['red_mean'],
                        green_mean=format_data['green_mean'],
                        blue_mean=format_data['blue_mean'],
                        hsv_h=format_data['hsv_h'],
                        hsv_s=format_data['hsv_s'],
                        hsv_v=format_data['hsv_v'],
                        lab_l=format_data['lab_l'],
                        lab_a=format_data['lab_a'],
                        lab_b=format_data['lab_b'],
                        image_id=download_instance.id
                    )
                except Exception as e:
                    raise RuntimeError("性状入库失败") from e

        # 计算并返回平均值
        trait_means = {
            'area_mean': np.round(np.mean(area_full_list), 3),
            'length_mean': np.round(np.mean(length_full_list), 3),
            'width_mean': np.round(np.mean(width_full_list), 3),
            'lw_mean': np.round(np.mean(lw_full_list), 3),
            'dia_mean': np.round(np.mean(dia_full_list), 3),
            'cir_mean': np.round(np.mean(cir_full_list), 3),
            'per_mean': np.round(np.mean(per_full_list), 3),
            'ecc_mean': np.round(np.mean(ecc_full_list), 3),
            'comp_mean': np.round(np.mean(comp_full_list), 3),
            'red_mean': np.round(np.mean(red_full_list), 0),
            'green_mean': np.round(np.mean(green_full_list), 0),
            'blue_mean': np.round(np.mean(blue_full_list), 0),
            'hue_mean': np.round(np.mean(hue_full_list), 3),
            'sat_mean': np.round(np.mean(sat_full_list), 3),
            'val_mean': np.round(np.mean(val_full_list), 3),
            'l_mean': np.round(np.mean(l_full_list), 3),
            'a_mean': np.round(np.mean(a_full_list), 3),
            'b_mean': np.round(np.mean(b_full_list), 3),
        }

        return {
            'img_name': img_name,
            'trait_count': grain_count,
            'trait_means': trait_means,
            'all_traits': format_data,
            'status': 'success'
        }

    except Exception as e:
        print(f"处理图片 {img_name} 时发生错误: {str(e)}")
        return {
            'img_name': img_name,
            'trait_count': 0,
            'status': 'failed',
            'error': str(e)
        }

def progress_event(progress, status, current_step):
    """生成SSE事件"""
    data = json.dumps({
        'progress': progress,
        'status': status,
        'current_step': current_step
    })
    return f"data: {data}\n\n"


img_path = []

def clear_folder_contents(folder_path: str, retries: int = 3, delay: float = 0.2):
    """
    更安全的清空：不删根目录，只删内部内容，降低并发风险
    """
    ensure_dir(folder_path)
    for name in os.listdir(folder_path):
        p = os.path.join(folder_path, name)
        last_err = None
        for _ in range(retries):
            try:
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
                break
            except Exception as e:
                last_err = e
                time.sleep(delay)
        else:
            print(f"[warn] 清空失败(可能被占用): {p} -> {last_err}")

def load_eff_classifier():
    """
    统一给 spike-yolo / yolov8 / yolov10 使用的 EfficientNet 分类模型。
    只在首次调用时加载一次并缓存，后续直接复用，避免每张图片重复加载造成速度慢/显存抖动。
    """
    if _classifier_cache["model"] is not None:
        return (_classifier_cache["model"],
                _classifier_cache["mapping"],
                _classifier_cache["transforms"],
                _classifier_cache["device"])

    project_root, _ = get_base_paths()
    # 你的分类数据与权重路径（和原工程一致）
    classify_folder = os.path.join(project_root, 'eff_classify', 'training_datasets')
    classify_image_path = os.path.join(classify_folder, 'for_cloud')
    classify_model_path = os.path.join(classify_folder, 'model')
    net_name = 'classify.pth'

    # 变换与设备
    data_transforms = transforms.Compose([
        transforms.RandomRotation(degrees=(0, 180), expand=True),
        transforms.Resize((64, 64)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(p=0.5),
        transforms.ToTensor()
    ])
    default_device = "cuda:0" if torch.cuda.is_available() else "cpu"
    device = torch.device(os.environ.get("RGPAS_CLASSIFIER_DEVICE", default_device))

    # 类别映射
    data = datasets.ImageFolder(classify_image_path)
    mapping = data.class_to_idx

    # 加载模型（和你原来一致：torch.load再 .eval）
    model_file = os.path.join(classify_model_path, net_name)
    model = torch.load(model_file, map_location=device)
    model = model.to(device)
    model.eval()

    _classifier_cache["model"] = model
    _classifier_cache["mapping"] = mapping
    _classifier_cache["transforms"] = data_transforms
    _classifier_cache["device"] = device
    return model, mapping, data_transforms, device

_classifier_cache = {
    "model": None,
    "mapping": None,
    "transforms": None,
    "device": None,
}

### 将性状分析封装为函数 结束###


from django.views.decorators.http import require_GET

def _progress_key(request, task_id=None):
    task_id = task_id or request.GET.get('task_id', '')
    return _ensure_session_key(request) + ':' + task_id


@require_GET
def analyse_status(request):
    if not request.session.get('user_info'):
        return JsonResponse({'error': '登录已过期，请重新登录。'}, status=401)
    state = progress_get(_progress_key(request))
    return JsonResponse(state or {'status': 'waiting', 'done': False})


@require_GET
def analyse_progress(request):
    if not request.session.get('user_info'):
        return JsonResponse({'error': '登录已过期，请重新登录。'}, status=401)
    key = _progress_key(request)
    def event_stream():
        yield "event: ping\ndata: init\n\n"
        started = time.monotonic()
        last_version = None
        while True:
            state = progress_get(key)
            if state:
                if state.get('ts') != last_version:
                    yield "data: " + json.dumps(state, ensure_ascii=False) + "\n\n"
                    last_version = state.get('ts')
                if state.get('done'):
                    break
            elif time.monotonic() - started > 60:
                # Reconnect without claiming that a job has completed.
                yield "event: ping\ndata: waiting\n\n"
                break
            yield ": heartbeat\n\n"
            time.sleep(1)
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

img_path = []
@csrf_exempt
def new_analyse(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    user_info = request.session.get('user_info')
    if not isinstance(user_info, dict) or not user_info.get('user'):
        return JsonResponse({'error': '登录已过期，请重新登录。'}, status=401)
    images = request.FILES.getlist('file')
    if not images:
        return JsonResponse({'error': '请选择要处理的图片。'}, status=400)
    model = request.POST.get('model')
    if model not in ('yolov8', 'spike-yolo', 'yolov10'):
        return JsonResponse({'error': '请选择有效的检测模型。'}, status=400)
    task_id = request.POST.get('task_id') or uuid.uuid4().hex
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', task_id):
        return JsonResponse({'error': '任务编号无效。'}, status=400)
    session_id = _ensure_session_key(request)
    key = _progress_key(request, task_id)
    with _ACTIVE_BATCHES_LOCK:
        if session_id in _ACTIVE_BATCHES:
            return JsonResponse({'error': '当前会话已有批量任务正在执行，请等待完成。'}, status=409)
        _ACTIVE_BATCHES.add(session_id)
    rows = []
    try:
        progress_set(key, task_id=task_id, status='queued', phase='queued',
                     current_file='', index=0, total=len(images), progress=0,
                     results=[], error='', done=False)
        with batch_slot():
            try:
                progress_set(key, status='running', phase='initializing')
                response = _run_batch_analysis(request, key, images, model, task_id, rows)
                progress_set(key, status='finished', phase='done', progress=100,
                             results=list(rows), done=True)
                return JsonResponse(response)
            except Exception as exc:
                # Finish cleanup before another queued batch can start.
                return _batch_failure(request, key, task_id, rows, exc)
    except Exception as exc:
        return _batch_failure(request, key, task_id, rows, exc)
    finally:
        with _ACTIVE_BATCHES_LOCK:
            _ACTIVE_BATCHES.discard(session_id)


def _batch_failure(request, key, task_id, rows, exc):
    state = progress_get(key)
    is_oom = isinstance(exc, torch.cuda.OutOfMemoryError)
    message = ('显存不足，任务已停止。已完成的结果已保留。'
               if is_oom else '处理失败，已完成的结果已保留，请查看服务器日志。')
    logger.error('Batch %s failed at %s: %s', task_id, state.get('phase'),
                 state.get('current_file'), exc_info=(type(exc), exc, exc.__traceback__))
    if is_oom:
        current = exc
        seen = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            traceback.clear_frames(current.__traceback__)
            current.__traceback__ = None
            current = current.__cause__ or current.__context__
        try:
            clear_detector_cache()
        except Exception:
            logger.exception('Failed to release detector cache after OOM')
    progress_set(key, status='failed', failure_phase=state.get('phase'),
                 phase='failed', error=message, results=list(rows), done=True)
    # Django does not automatically save sessions for HTTP 500 responses.
    try:
        request.session.save()
    except Exception:
        logger.exception('Failed to persist partial batch download metadata')
    return JsonResponse(result_payload(
        rows, task_id, 'failed', error=message,
        failed_file=state.get('current_file', ''),
        failure_phase=state.get('phase', ''),
    ), status=500)


def _run_batch_analysis(request, session_key, images, model, task_id, completed_rows):
    user_info = request.session['user_info']
    username = user_info['user']
    total_files = len(images)
    # 收集返回给前端 updateResults(data) 的字段
    filenames_list = []  # 每个上传文件的文件名（含扩展名）
    num_list = []  # 每张图的总穗粒数（检测阶段返回）
    sum_list = []  # 每张图“完整穗粒数”（你的过滤&分类后保留的数量）

    # 同时也保存 traits 的均值（用于 TraitsOfSpikes.csv）
    filenames = []
    area_mean_list = []
    length_mean_list = []
    width_mean_list = []
    dia_mean_list = []
    lw_mean_list = []
    cir_mean_list = []
    per_mean_list = []
    ecc_mean_list = []
    comp_mean_list = []
    red_mean_list = []
    green_mean_list = []
    blue_mean_list = []
    hue_mean_list = []
    sat_mean_list = []
    val_mean_list = []
    l_mean_list = []
    a_mean_list = []
    b_mean_list = []

    # 路径：整批只计算一次
    project_root, static_folder = get_base_paths()
    task_folder = uuid.uuid4().hex
    image_ids = []
    request.session['batch_image_ids'] = image_ids
    request.session['batch_task_id'] = task_id
    def url_for(file_path):
        return static_file_url(file_path, static_folder, settings.STATIC_URL)

    # traits 输出总目录（按日期&用户名）
    traits_full_output_folder = os.path.join(static_folder, 'batch_traits')
    os.makedirs(traits_full_output_folder, exist_ok=True)
    get_today_date = datetime.today().strftime('%Y-%m-%d')
    user_traits_folder = task_folder
    traits_output_folder = os.path.join(traits_full_output_folder, user_traits_folder)
    os.makedirs(traits_output_folder, exist_ok=True)
    request.session['batch_traits_folder'] = 'batch_traits/' + task_folder


    # 统一加载分类器（3个模型均需要）
    clf_model, clf_mapping, clf_transforms, clf_device = load_eff_classifier()

    # 针对 3 个模型分别配置目录名
    if model == 'spike-yolo':
        batch_dir_name = 'batch_yolo'
        result_dir_name = 'batch_yolo_result'
        complety_dir_name = 'batch_yolo_complety'
        mask_dir_name = 'batch_yolo_comp_mask'
        # with bind_ultralytics("v10"):
        #     from yolov10_current.detect import testYolov10
        #     detect_func = testYolov10  # 你工程里 spike-yolo 的 test 函数是哪个？若不是 yolov10，请换成对应函数
        detect_func = get_detect_func('v10', 'yolov10_current.detect', 'testYolov10')

    elif model == 'yolov8':
        batch_dir_name = 'batch_yolov8'
        result_dir_name = 'batch_yolov8_result'
        complety_dir_name = 'batch_yolov8_complety'
        mask_dir_name = 'batch_yolov8_comp_mask'
        # with bind_ultralytics("v10"):
        #     from yolov10_current.detect import testYolov10
        detect_func = get_detect_func('v8legacy', 'yolov8.detect', 'testYolov8')
            
    else:  # 'yolov10'
        batch_dir_name = 'batch_yolov10'
        result_dir_name = 'batch_yolov10_result'
        complety_dir_name = 'batch_yolov10_complety'
        mask_dir_name = 'batch_yolov10_comp_mask'
        # with bind_ultralytics("v10"):
        #     from yolov10_current.detect import testYolov10m
        #     detect_func = testYolov10m
        detect_func = get_detect_func('v10', 'yolov10_current.detect', 'testYolov10m')

    # 批处理输入/输出根目录（整批只清理一次“输入目录文件”，结果目录不清空，避免首张后把后续结果删掉）
    batch_directory = os.path.join(static_folder, batch_dir_name, task_folder)
    os.makedirs(batch_directory, exist_ok=True)

    result_path_result = os.path.join(static_folder, result_dir_name, task_folder)
    os.makedirs(result_path_result, exist_ok=True)

    # 把所有上传图片先保存到 batch_directory
    from django.core.files.storage import FileSystemStorage
    fs = FileSystemStorage(location=batch_directory)

    # 会话期创建 Batches 记录：一张图对应一个 Batches，用于 traits -> Download 关联
    current_user = User.objects.get(user=user_info['user'], role__role=user_info['role'])

    def write_summary():
        # 生成 TraitsOfSpikes.csv（批量汇总）
        try:
            num_traits_df = pd.DataFrame({
                'Image name': filenames,
                'Number of spike': num_list,
                'Grain size (mm^2)': area_mean_list,
                'Grain length (mm)': length_mean_list,
                'Grain width (mm)': width_mean_list,
                'Grain diameter (mm)': dia_mean_list,
                'Grain length/width ratio': lw_mean_list,
                'Grain roundness': cir_mean_list,
                'Grain perimeter (mm)': per_mean_list,
                'Grain compactness': comp_mean_list,
                'Grain eccentricity': ecc_mean_list,
                'Red value': red_mean_list,
                'Green value': green_mean_list,
                'Blue value': blue_mean_list,
                'Hue value': hue_mean_list,
                'Saturation value': sat_mean_list,
                'Brightness value': val_mean_list,
                'Lightness value': l_mean_list,
                'Green-red value': a_mean_list,
                'Blue-yellow value': b_mean_list
            })
            csv_path = os.path.join(traits_output_folder, "TraitsOfSpikes.csv")
            num_traits_df.to_csv(csv_path, index=False)
        except Exception as exc:
            raise RuntimeError("写入批量汇总 CSV 失败") from exc


    # == 主循环：逐张处理 ==
    for idx, image in enumerate(images, start=1):         ### 新增实时更新分析图像名

        # 告诉前端：开始处理第 idx 张
        progress_set(session_key,
                     status='running',
                     phase='detecting',
                     current_file=image.name,
                     index=idx,
                     total=total_files,
                     progress=int((idx-1) / total_files * 100),
                     done=False)
        # 告诉前端：开始处理第 idx 张  
        
        filename = fs.save(image.name, image, max_length=150)
        original_pic = Path(filename).stem
        filenames.append(Path(image.name).stem)
        filenames_list.append(filename)
        uploaded_file_url = os.path.join(batch_directory, filename)

        # ... 检测前后都可以刷一下阶段 ...
        progress_set(session_key, phase='detecting', current_file=image.name)   ### 新增实时更新分析图像名

        # 创建 Batches 记录 & 放入 session（traits 入库用）
        download_instance = Batches.objects.create(
            pic=image.name,
            target_pic=url_for(uploaded_file_url),
            result_pic='',
            spike_pic='',
            user=current_user
        )
        request.session['download_id'] = download_instance.id

        # 1) 运行检测（把目标图保存/传入 detect 函数）
        detection = detect_func(
            uploaded_file_url, result_path_result, original_pic, return_details=True,
        )
        total_spike = detection.number
        num_list.append(total_spike)
        download_instance.result_pic = url_for(detection.image_path)
        download_instance.save(update_fields=['result_pic'])

        # 检测完成后
        progress_set(session_key, phase='classifying', current_file=image.name)    ### 新增实时更新分析图像名

        # 2) 结果子图所在目录（panicle）
        folder_path = os.path.join(detection.save_dir, 'panicle')

        # 3) 完整粒/掩膜输出（逐图创建/清理其子目录，不影响其它图）
        destination_folder = os.path.join(static_folder, complety_dir_name, task_folder, original_pic)
        des_mask_folder = os.path.join(static_folder, mask_dir_name, task_folder, original_pic)

        # 只清掉本张图的 jpg/png，保留其它图的文件
        os.makedirs(destination_folder, exist_ok=True)
        os.makedirs(des_mask_folder, exist_ok=True)

        download_instance.spike_pic = url_for(destination_folder)
        download_instance.save(update_fields=['spike_pic'])

        # 4) 复制“整图检测结果图”到 traits 文件夹，便于打包
        import shutil
        try:
            output_image_path = detection.image_path
            copy_image_path = os.path.join(traits_output_folder, f"{original_pic}.jpg")
            shutil.copyfile(output_image_path, copy_image_path)
        except Exception as exc:
            raise RuntimeError("复制检测结果到下载目录失败") from exc

        # 5) 统计 panicle 子图个数
        cnt = 1
        while os.path.exists(os.path.join(folder_path, f"{cnt}.jpg")):
            cnt += 1
        # cnt-1 才是实际数量
        print(f"{model} - {original_pic} 检测子图数量：{cnt - 1}")

        # 6) ——分类（EfficientNet）——（并行）
        # 这里按你原逻辑：process_single_image 内部会用 mapping/transforms 进行类别判定并生成 mask
        batch_size = 100
        num_batches = (cnt - 1) // batch_size + (1 if (cnt - 1) % batch_size != 0 else 0)
        for b in range(num_batches):
            start_i = b * batch_size + 1
            end_i = min((b + 1) * batch_size + 1, cnt)
            with ThreadPoolExecutor(max_workers=max(1, int(os.environ.get('RGPAS_CLASSIFIER_WORKERS', '1')))) as executor:
                futures = {
                    executor.submit(
                        process_single_image,
                        i,
                        folder_path,
                        destination_folder,
                        des_mask_folder,
                        clf_model,
                        clf_mapping,
                        clf_transforms
                    ): i
                    for i in range(start_i, end_i)
                }
                for fut in concurrent.futures.as_completed(futures):
                    _ = futures[fut]
                    try:
                        classification = fut.result()
                        if classification.get('status') == 'error':
                            raise RuntimeError(classification.get('message', '分类失败'))
                    except Exception:
                        # Stop the batch instead of reporting incomplete data as success.
                        raise

        # ... 分类完成后
        progress_set(session_key, phase='filtering', current_file=image.name)

        # 7) 第二阶段：特征提取 & 过滤（并行抽取 -> 单线程过滤）
        input_list = os.listdir(destination_folder)
        all_features = {'name': [], 'size_list': [], 'round_list': [], 'lw_list': []}

        feat_batch = 20
        num_feat_batches = (len(input_list) + feat_batch - 1) // feat_batch
        for b in range(num_feat_batches):
            start_i = b * feat_batch
            end_i = min((b + 1) * feat_batch, len(input_list))
            batch_images = input_list[start_i:end_i]

            batch_results = []
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {
                    executor.submit(extract_image_features, img_name, destination_folder): img_name
                    for img_name in batch_images
                }
                for fut in concurrent.futures.as_completed(futures):
                    img_name = futures[fut]
                    try:
                        result = fut.result()
                        batch_results.append(result)
                    except Exception as exc:
                        raise RuntimeError(f"提取特征失败: {img_name}") from exc

            for result in batch_results:
                all_features['name'].append(result['name'])
                all_features['size_list'].extend(result['size_list'])
                all_features['round_list'].extend(result['round_list'])
                all_features['lw_list'].extend(result['lw_list'])

        lw_list = all_features['lw_list']
        size_list = all_features['size_list']
        lw_mean = round(np.mean(lw_list), 3) if lw_list else 0
        size_mean = round(np.mean(size_list), 3) if size_list else 0

        # DataFrame 过滤
        get_df = pd.DataFrame({
            'name': all_features['name'],
            'lw': lw_list[:len(all_features['name'])],
            'round': all_features['round_list'][:len(all_features['name'])],
            'size': size_list[:len(all_features['name'])]
        })
        get_df.sort_values(by='size', inplace=True)

        size_lower_bound = size_mean * 0.85
        size_upper_bound = size_mean * 1.5
        size_filtered_df = get_df[(get_df['size'] >= size_lower_bound) & (get_df['size'] <= size_upper_bound)]
        lw_upper_bound = lw_mean * 1.25
        lw_filtered_df = size_filtered_df[(size_filtered_df['lw'] <= lw_upper_bound)]
        select_img_name_list = lw_filtered_df['name'].tolist()

        # 删除不符合条件的文件（仅本图目录）
        for name in input_list:
            stem = name.split('.')[0]
            if name not in select_img_name_list:
                try:
                    os.remove(os.path.join(destination_folder, name))
                except:
                    pass
                try:
                    os.remove(os.path.join(des_mask_folder, stem + '.png'))
                except:
                    pass
        
        # 第二阶段：特征提取与筛选完成
        progress_set(session_key, phase='analysing', current_file=image.name)

        # 8) 第三阶段：性状分析并入库（并行）
        analyse_traits_list = os.listdir(destination_folder)
        db_lock = threading.Lock()

        full_area_list = []
        full_length_list = []
        full_width_list = []
        full_dia_list = []
        full_lw_list = []
        full_cir_list = []
        full_per_list = []
        full_ecc_list = []
        full_comp_list = []
        full_red_list = []
        full_green_list = []
        full_blue_list = []
        full_hue_list = []
        full_sat_list = []
        full_val_list = []
        full_l_list = []
        full_a_list = []
        full_b_list = []

        images_done = 0
        ana_batch = 20
        num_ana_batches = (len(analyse_traits_list) + ana_batch - 1) // ana_batch

        for b in range(num_ana_batches):
            start_i = b * ana_batch
            end_i = min((b + 1) * ana_batch, len(analyse_traits_list))
            batch_images = analyse_traits_list[start_i:end_i]

            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {
                    executor.submit(
                        run_db_worker,
                        batch_analyze_and_store_traits,
                        img_name,
                        destination_folder,
                        des_mask_folder,
                        request,
                        db_lock
                    ): img_name
                    for img_name in batch_images
                }
                for fut in concurrent.futures.as_completed(futures):
                    img_name = futures[fut]
                    try:
                        result = fut.result()
                        if result['status'] == 'success':
                            images_done += 1
                            means = result['trait_means']
                            full_area_list.append(means['area_mean'])
                            full_length_list.append(means['length_mean'])
                            full_width_list.append(means['width_mean'])
                            full_dia_list.append(means['dia_mean'])
                            full_lw_list.append(means['lw_mean'])
                            full_cir_list.append(means['cir_mean'])
                            full_per_list.append(means['per_mean'])
                            full_ecc_list.append(means['ecc_mean'])
                            full_comp_list.append(means['comp_mean'])
                            full_red_list.append(means['red_mean'])
                            full_green_list.append(means['green_mean'])
                            full_blue_list.append(means['blue_mean'])
                            full_hue_list.append(means['hue_mean'])
                            full_sat_list.append(means['sat_mean'])
                            full_val_list.append(means['val_mean'])
                            full_l_list.append(means['l_mean'])
                            full_a_list.append(means['a_mean'])
                            full_b_list.append(means['b_mean'])
                        else:
                            raise RuntimeError(f"性状分析失败: {img_name}: {result.get('error', 'Unknown error')}")
                    except Exception as exc:
                        raise RuntimeError(f"性状分析失败: {img_name}") from exc

        # 一张图片的“完整穗粒数” = 实际参与性状分析的粒图数
        sum_list.append(images_done)

        # 该图片的总体均值（加入 CSV 行）
        def _safe_mean(x):
            return round(np.mean(x), 3) if x else 0

        area_mean_list.append(_safe_mean(full_area_list))
        length_mean_list.append(_safe_mean(full_length_list))
        width_mean_list.append(_safe_mean(full_width_list))
        dia_mean_list.append(_safe_mean(full_dia_list))
        lw_mean_list.append(_safe_mean(full_lw_list))
        cir_mean_list.append(_safe_mean(full_cir_list))
        per_mean_list.append(_safe_mean(full_per_list))
        ecc_mean_list.append(_safe_mean(full_ecc_list))
        comp_mean_list.append(_safe_mean(full_comp_list))
        # 颜色均值按原来的四舍五入规则
        red_mean_list.append(round(np.mean(full_red_list), 0) if full_red_list else 0)
        green_mean_list.append(round(np.mean(full_green_list), 0) if full_green_list else 0)
        blue_mean_list.append(round(np.mean(full_blue_list), 0) if full_blue_list else 0)
        hue_mean_list.append(_safe_mean(full_hue_list))
        sat_mean_list.append(_safe_mean(full_sat_list))
        val_mean_list.append(_safe_mean(full_val_list))
        l_mean_list.append(_safe_mean(full_l_list))
        a_mean_list.append(_safe_mean(full_a_list))
        b_mean_list.append(_safe_mean(full_b_list))

        # 本图完成，写入 Results（总数/完整数）
        Results.objects.create(
            select_model=model,
            total=total_spike,
            sum=images_done,
            image_id=download_instance.id
        )

        # 把本图完整粒输出拷贝到 traits 打包目录（便于用户下载）
        try:
            copy_complete_folder = os.path.join(traits_output_folder, original_pic)
            if os.path.exists(copy_complete_folder):
                shutil.rmtree(copy_complete_folder)
            shutil.copytree(destination_folder, copy_complete_folder)
        except Exception as exc:
            raise RuntimeError("复制完整粒结果到下载目录失败") from exc

        # == 全部图片处理结束：写 CSV 并一次性返回 JSON ==

        # 第三阶段：性状分析入库完成
        # ... 当前这张完结：用 idx/total 估个整体百分比
        grain_paths = sorted(
            Path(destination_folder).glob('*.jpg'),
            key=lambda entry: (0, int(entry.stem)) if entry.stem.isdigit() else (1, entry.stem),
        )
        completed_rows.append({
            'name': image.name, 'filename': filename, 'number': total_spike,
            'complete_count': images_done, 'original_url': url_for(uploaded_file_url),
            'result_url': url_for(detection.image_path),
            'complete_urls': [url_for(entry) for entry in grain_paths],
        })
        image_ids.append(download_instance.id)
        request.session['batch_image_ids'] = list(image_ids)
        write_summary()
        log_cuda_memory('image completed')
        progress_set(session_key,
                     results=list(completed_rows),
                     phase='done_one',
                     current_file=image.name,
                     progress=int(idx / total_files * 100))

    num_list = [str(n) for n in num_list]
    sum_list = [str(s) for s in sum_list]

    return result_payload(completed_rows, task_id, 'finished')

import codecs
import io
from wsgiref.util import FileWrapper

def create_zip_file(folder_path, zip_name):
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=folder_path)
                zipf.write(file_path, arcname=arcname)
                # zipf.write(os.path.join(root, file),
                #            os.path.relpath(os.path.join(root, file),
                #                            os.path.join(folder_path, '..')))

def create_csv_file(folder_path, file_name, image_ids=None):
    file_path = os.path.join(folder_path, file_name)
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        header = [
            smart_str('ID'), smart_str('Grain size (mm^2)'), smart_str('Grain length (mm)'), smart_str('Grain width (mm)'), smart_str('Grain diameter (mm)'),
            smart_str('grain length/width ratio'), smart_str('Grain roundness'), smart_str('Grain perimeter (mm)'), smart_str('Grain compactness'), smart_str('Grain eccentricity'),
            smart_str('Red value'), smart_str('Green value'), smart_str('Blue value'),
            smart_str('Hue value'), smart_str('Saturation value'), smart_str('Brightness value'),
            smart_str('Lightness value'), smart_str('Green-red value'), smart_str('Blue-yellow value')
        ]

        writer.writerow(header)

        data = Download.objects.all()
        if image_ids is not None:
            data = data.filter(image_id__in=image_ids)
        data = data.order_by('image_id')
        id_counter_dict = {}

        for item in data:
            if item.image_id:
                pic = Batches.objects.get(pk=item.image_id).pic
                pic_name = pic.split('.')[0]
                if pic not in id_counter_dict:
                    id_counter_dict[pic] = 1
                else:
                    id_counter_dict[pic] += 1

                # row_id = f"{pic}_{id_counter_dict[pic]}"
                row_id = f"{pic_name}_{id_counter_dict[pic]}"
                row = [
                    smart_str(row_id),  # 编号递增
                    # smart_str(latest_detection.pic),
                    smart_str(item.area),
                    smart_str(item.length),
                    smart_str(item.width),
                    smart_str(item.diameter),
                    smart_str(item.l_w),
                    smart_str(item.circularity),
                    smart_str(item.perimeter),
                    smart_str(item.compactness),
                    smart_str(item.eccentricity),
                    smart_str(item.red_mean),
                    smart_str(item.green_mean),
                    smart_str(item.blue_mean),
                    smart_str(item.hsv_h),
                    smart_str(item.hsv_s),
                    smart_str(item.hsv_v),
                    smart_str(item.lab_l), 
                    smart_str(item.lab_a), 
                    smart_str(item.lab_b)
                ]

                writer.writerow(row)
    return file_path
                
from django.views.decorators.http import require_http_methods        
@require_http_methods(["GET"])
def download(request):
    ###新的代码（压缩本地文件夹）###

    try:
        get_today_date = datetime.today().strftime('%Y-%m-%d')

        user_info = request.session.get('user_info')
        username = user_info['user']

        current_directory = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_directory)
        static_folder = os.path.join(project_root, 'static')

        traits_full_output_folder = os.path.join(static_folder, 'batch_traits')
        user_traits_folder = f"{username}_{get_today_date}"
        traits_output_folder = os.path.join(traits_full_output_folder, user_traits_folder)
        saved_folder = request.session.get('batch_traits_folder')
        if saved_folder:
            traits_output_folder = str((Path(static_folder) / saved_folder).resolve())
            Path(traits_output_folder).relative_to(Path(traits_full_output_folder).resolve())

        # 获取当前日期和时间
        current_time = datetime.now().strftime("%Y-%m-%d-%H_%M")
        # 创建性状 csv 文件
        csv_file_name = f"{current_time}_TraitsOfCompleteSpikelets.csv"
        image_ids = request.session.get('batch_image_ids')
        if image_ids is None:
            image_ids = list(Batches.objects.filter(user__user=username, user__role__role=user_info['role']).values_list('id', flat=True))
        create_csv_file(traits_output_folder, csv_file_name, image_ids)

        zip_name = f"{current_time}_BatchProcessTraits.zip"
        # Each download gets an independent temporary stream. Closing the
        # response removes the ZIP without deleting any analysis images.
        zip_stream = tempfile.TemporaryFile()
        try:
            create_zip_file(traits_output_folder, zip_stream)
            zip_stream.seek(0)
            return FileResponse(zip_stream, as_attachment=True, filename=zip_name,
                                content_type='application/zip')
        except Exception:
            zip_stream.close()
            raise

    except Exception as e:
        logger.exception('Failed to export batch traits')
        return HttpResponse("Error occurred while creating or sending the zip file.", status=500)

def downloadTestimage(request):

    try:

        zip_name = "TestImages.zip"
        response = HttpResponse(FileWrapper(open(zip_name, 'rb')), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(zip_name)}"'
        response['Content-Length'] = os.path.getsize(zip_name)

        return response

    except Exception as e:
        # 这里可以根据需要记录日志或进行错误处理
        return HttpResponse("Error occurred while creating or sending the zip file.", status=500)

def downloadwhole(request, image_name):

    try:

        current_directory = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_directory)
        static_folder = os.path.join(project_root, 'static')
        whole_folder = os.path.join(static_folder, 'DatabaseDisplay', 'CompleteForDownload')

        folder_name = image_name.split('.')[0]
        whole_download_folder = os.path.join(whole_folder, folder_name)
        zip_name = folder_name + ".zip"
        create_zip_file(whole_download_folder, zip_name)

        response = HttpResponse(FileWrapper(open(zip_name, 'rb')), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(zip_name)}"'
        response['Content-Length'] = os.path.getsize(zip_name)

        return response

    except Exception as e:
        # 这里可以根据需要记录日志或进行错误处理
        return HttpResponse("Error occurred while creating or sending the zip file.", status=500)

def getLatestDetection(request):
    from .single_runtime import detection_for_download, JobError
    try:
        latest_detection = detection_for_download(request)
    except JobError as exc:
        return JsonResponse({'error': str(exc)}, status=exc.status)
    return JsonResponse({'pic': latest_detection.pic})

def downloadSingle(request):
    # 使用 latest 获取 Detection 表中的最后一条数据
    from .single_runtime import detection_for_download, JobError
    try:
        latest_detection = detection_for_download(request)
    except JobError as exc:
        return JsonResponse({'error': str(exc)}, status=exc.status)

    # 提取图像名称中的数字部分作为文件名
    # file_name = latest_detection.pic.split('.')[0] + '_TraitsOfSingleSpikelet.csv'
    # file_name = 'TraitsOfSingleSpikelet.csv'

    file_name = f"{latest_detection.pic.split('.')[0]}_grain_analysis.csv"

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    # response['Content-Disposition'] = 'attachment; filename="' + file_name + '"'     错误的保存方式
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'  # 设置文件名


    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    response.write(codecs.BOM_UTF8)

    header = [
        smart_str('ID'), smart_str('Grain size (mm^2)'), smart_str('Grain length (mm)'), smart_str('Grain width (mm)'), smart_str('Grain diameter (mm)'), 
        smart_str('Grain length/width ratio'), smart_str('Grain roundness'), smart_str('Grain perimeter'), smart_str('Grain compactness'), smart_str('Grain eccentricity'), 
        smart_str('Red value'), smart_str('Green value'), smart_str('Blue value'),
        smart_str('Hue value'), smart_str('Saturation value'), smart_str('Brightness value'),
        smart_str('Lightness value'), smart_str('Green-red value'), smart_str('Blue-yellow value'),
      ]

    writer.writerow(header)

    # 检查是否存在相关联的 Detection 记录
    singles = Single.objects.filter(image_id=latest_detection.id)
    for i, single in enumerate(singles, start=1):
        row = [
            smart_str(i),  # 编号递增
            # smart_str(latest_detection.pic),
            smart_str(single.area),
            smart_str(single.length),
            smart_str(single.width),
            smart_str(single.diameter),
            smart_str(single.l_w),
            smart_str(single.circularity),
            smart_str(single.perimeter),
            smart_str(single.compactness),
            smart_str(single.eccentricity),
            smart_str(single.red_mean),
            smart_str(single.green_mean),
            smart_str(single.blue_mean),
            smart_str(single.hsv_h),
            smart_str(single.hsv_s),
            smart_str(single.hsv_v),
            smart_str(single.lab_l),
            smart_str(single.lab_a),
            smart_str(single.lab_b)
        ]

        writer.writerow(row)

    response.write(csv_buffer.getvalue().encode('utf-8'))

    return response

def upload(request):
    return render(request, "upload.html")


def entity(request):
    return render(request, "entity.html")

# your_app_name/views.py
from django.shortcuts import render
from .models import Detection

@csrf_exempt
def test(request):
    from .single_runtime import count_view
    return count_view(request)


def atest(request):
    # 检查用户是否已登录
    # if 'username' in request.session:
    if 'user_info' in request.session:
        user_info = request.session.get('user_info')
        username = user_info['user']
        role = user_info['role']
        # username = request.session.get('username')
    else:
        # 用户未登录，您可以选择如何处理，例如，重定向到登录页面
        return redirect('/')
    return render(request, 'analyse.html', {'username': username, 'user_info': user_info})

def adatabase(request):

    if 'user_info' in request.session:
        user_info = request.session.get('user_info')
        username = user_info['user']
        role = user_info['role']
        # username = request.session.get('username')
    else:
        # 用户未登录，您可以选择如何处理，例如，重定向到登录页面
        return redirect('/')

    current_directory = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_directory)
    static_folder = os.path.join(project_root, 'static')
    database_file_folder = os.path.join(static_folder, 'DatabaseDisplay')
    image_folder = os.path.join(database_file_folder, 'InputImagePage1')

    image_files = [

        {'url': f'DatabaseDisplay/InputImagePage1/{filename}', 'name': filename, 'gpname': os.path.splitext(filename)[0]}

        for filename in os.listdir(image_folder)
        if filename.endswith(('.png', '.jpg', 'jpeg'))
    ]

    ### 检查是否有搜索查询 ###
    search_query = request.GET.get('search_query')
    if search_query:
        # 过滤出包含搜索查询的图像
        filtered_images = [image for image in image_files if search_query.lower() in image['name'].lower()]
    else:
        filtered_images = image_files
    ### 检查是否有搜索查询结束 ###

    ### 增加每页显示图像代码 ###
    # 假设每页显示50张图片
    pagintor = Paginator(filtered_images, 100)
    # 从请求中获取页码
    page = request.GET.get('page')
    # 从获取分页后的图片列表
    images = pagintor.get_page(page)
    ### 增加每页显示图像代码结束 ###

    return render(request, 'database.html', {'username': username, 'user_info': user_info, 'images_files': image_files,
                                             'page': page, 'paginator': pagintor, 'images': images,
                                             'search_query': search_query})


# def adatabase2(request, image_name):

#     if 'user_info' in request.session:
#         user_info = request.session.get('user_info')
#         username = user_info['user']
#         role = user_info['role']
#         # username = request.session.get('username')
#     else:
#         # 用户未登录，您可以选择如何处理，例如，重定向到登录页面
#         return redirect('/')

#     # 假设image_name从URL中获取
#     current_directory = os.path.dirname(os.path.abspath(__file__))
#     project_root = os.path.dirname(current_directory)
#     static_folder = os.path.join(project_root, 'static')
#     database_file_folder = os.path.join(static_folder, 'DatabaseDisplay')

#     # get_raw_folder = os.path.join(database_file_folder, 'InputImagePage2')
#     # raw_image_path = os.path.join(get_raw_folder, image_name)

#     get_detect_folder = os.path.join(database_file_folder, 'DetectedImage')
#     image_path = os.path.join(get_detect_folder, image_name)

#     get_complete_folder = os.path.join(database_file_folder, 'CompleteForDisplay')
#     gp_folder = os.path.splitext(image_name)[0]
#     gp_complete_folder = os.path.join(get_complete_folder, gp_folder)
#     gp_folder_name = os.path.basename(gp_complete_folder)

#     raw_image = {'url': f'DatabaseDisplay/InputImagePage1/{image_name}'}

#     image = {'url': f'DatabaseDisplay/DetectedImage/{image_name}', 'gpname': os.path.splitext(image_name)[0],
#              'name': image_name}

#     image_files = [
#         {'url': f'DatabaseDisplay/CompleteForDisplay/{gp_folder_name}/{filename}', 'name': filename,
#          'gpname': os.path.splitext(filename)[0]}

#         # {'url': f'{gp_complete_folder}/{filename}', 'name': filename,
#         #  'gpname': os.path.splitext(filename)[0]}

#         #### 读取文件夹中的子文件夹，并获取子文件夹中干的文件

#         for filename in os.listdir(gp_complete_folder)
#         if filename.endswith(('.png', '.jpg', 'jpeg'))
#     ]

#     if not os.path.exists(image_path):
#         return HttpResponse('Image not found', status=404)

#     database_excel_path = os.path.join(static_folder, 'database_used_1105.xlsx')
#     df_database = pd.read_excel(database_excel_path, engine='openpyxl')

#     # 安全转换：RGB -> 整数；其他数值列保持 float 或 None
#     def safe_int(x):
#         if x is None: 
#             return None
#         try:
#             return int(round(float(x)))
#         except Exception:
#             return None

#     def safe_float(x):
#         if x is None: 
#             return None
#         try:
#             return float(x)
#         except Exception:
#             return None

#     # 用 where + notna 把所有 NaN 转为 None（数据库里会写 NULL）
#     df_database = df_database.where(pd.notna(df_database), None)

#     gp_folder = os.path.splitext(image_name)[0]

#     for index, row in df_database.iterrows():
#         RiceGenotype.objects.update_or_create(
#             genotype=row['genotype'],
#             defaults={
#                 'species': row['species'],
#                 'region': row['origin country'],
#                 'raw_classify': row['classify1'],
#                 'current_classify': row['classify2'],
#                 'area': row['area'],
#                 'length': row['length'],
#                 'width': row['width'],
#                 'l_w': row['l/w'],
#                 'perimeter': row['perimeter'],
#                 'diameter': row['diameter'],
#                 'Circularity': row['circu'],
#                 'Compacthness': row['compacthness'],
#                 'Red_mean': row['r'],
#                 'Green_mean': row['g'],
#                 'Blue_mean': row['b'],
#                 'Hue_mean': row['h'],
#                 'Saturation_mean': row['s'],
#                 'Value_mean': row['v']
#             }
#         )

#     # 从数据库中提取数据
#     genotype_data = RiceGenotype.objects.filter(genotype=gp_folder).first()
#     if genotype_data:
#         table_data = {
#             'genotype': genotype_data.genotype,
#             'species': genotype_data.species,
#             'region': genotype_data.region,
#             'raw_classify': genotype_data.raw_classify,
#             'current_classify': genotype_data.current_classify,
#             'area': genotype_data.area,
#             'length': genotype_data.length,
#             'width': genotype_data.width,
#             'l_w': genotype_data.l_w,
#             'perimeter': genotype_data.perimeter,
#             'Circularity': genotype_data.Circularity,
#             'Compacthness': genotype_data.Compacthness,
#             'Red_mean': genotype_data.Red_mean,
#             'Green_mean': genotype_data.Green_mean,
#             'Blue_mean': genotype_data.Blue_mean,
#             'Hue_mean': genotype_data.Hue_mean,
#             'Saturation_mean': genotype_data.Saturation_mean,
#             'Value_mean': genotype_data.Value_mean,
#         }
#     else:
#         table_data = None

#     return render(request, 'database2.html', {'username': username, 'user_info': user_info, 'raw_image': raw_image,
#                                               'image': image, 'images': image_files, 'table_data': table_data})

def adatabase2(request, image_name):
    if 'user_info' not in request.session:
        return redirect('/')

    user_info = request.session['user_info']
    username = user_info['user']

    current_directory = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_directory)
    static_folder = os.path.join(project_root, 'static')

    # 这些仅用于找图片展示
    database_file_folder = os.path.join(static_folder, 'DatabaseDisplay')
    get_detect_folder = os.path.join(database_file_folder, 'DetectedImage')
    image_path = os.path.join(get_detect_folder, image_name)

    get_complete_folder = os.path.join(database_file_folder, 'CompleteForDisplay')
    gp_folder = os.path.splitext(image_name)[0]
    gp_complete_folder = os.path.join(get_complete_folder, gp_folder)
    gp_folder_name = os.path.basename(gp_complete_folder)

    if not os.path.exists(image_path):
        return HttpResponse('Image not found', status=404)

    raw_image = {'url': f'DatabaseDisplay/InputImagePage1/{image_name}'}
    image = {'url': f'DatabaseDisplay/DetectedImage/{image_name}', 'gpname': gp_folder, 'name': image_name}

    image_files = [
        {'url': f'DatabaseDisplay/CompleteForDisplay/{gp_folder_name}/{filename}',
         'name': filename, 'gpname': os.path.splitext(filename)[0]}
        for filename in (os.listdir(gp_complete_folder) if os.path.exists(gp_complete_folder) else [])
        if filename.endswith(('.png', '.jpg', 'jpeg'))
    ]

    # ⭐ 只读数据库，不再导入 Excel
    genotype_data = RiceGenotype.objects.filter(genotype=gp_folder).first()
    table_data = None
    if genotype_data:
        table_data = {
            'genotype': genotype_data.genotype,
            'species': genotype_data.species,
            'region': genotype_data.region,
            'raw_classify': genotype_data.raw_classify,
            'current_classify': genotype_data.current_classify,
            'area': genotype_data.area,
            'length': genotype_data.length,
            'width': genotype_data.width,
            'l_w': genotype_data.l_w,
            'perimeter': genotype_data.perimeter,
            'Circularity': genotype_data.Circularity,
            'Compacthness': genotype_data.Compacthness,
            'Red_mean': genotype_data.Red_mean,
            'Green_mean': genotype_data.Green_mean,
            'Blue_mean': genotype_data.Blue_mean,
            'Hue_mean': genotype_data.Hue_mean,
            'Saturation_mean': genotype_data.Saturation_mean,
            'Value_mean': genotype_data.Value_mean,
        }

    return render(request, 'database2.html', {
        'username': username,
        'user_info': user_info,
        'raw_image': raw_image,
        'image': image,
        'images': image_files,
        'table_data': table_data
    })


def use(request):
    # 检查用户是否已登录
    # if 'username' in request.session:
    if 'user_info' in request.session:
        user_info = request.session.get('user_info')
        username = user_info['user']
        role = user_info['role']
        # username = request.session.get('username')
    else:
        # 用户未登录，您可以选择如何处理，例如，重定向到登录页面
        return redirect('/')
    return render(request, 'use.html', {'username': username,'user_info': user_info})


def cutout_plant_from_original(img, binary_final_img):
    # 提取图像的掩膜
    mask = binary_final_img > 0
    # 对三个通道分别处理
    r = img[:, :, 0] * binary_final_img
    g = img[:, :, 1] * binary_final_img
    b = img[:, :, 2] * binary_final_img
    # 将三个通道处理结果合起来
    # img_temp=np.dstack([r.astype(np.uint8),g.astype(np.uint8),b.astype(np.uint8)])
    img_temp = np.dstack([r, g, b])
    return img_temp
def ccc(request):
    return render(request,"try.html")


@csrf_exempt
def complety(request):
    from .single_runtime import extract_view
    return extract_view(request)

@csrf_exempt

def user_single(request):
    user_info = request.session.get('user_info')
    username = user_info['user']
    data_list = models.User.objects.filter(user=username).first()
    return render(request,"dex.html", {'username': username,'data_list':data_list,'user_info':user_info})


def trySee(request):
    user_info = request.session.get('user_info')
    username = user_info['user']
    nid = request.GET.get('nid')

    if request.method == 'GET':
        # 获取用户信息
        user = User.objects.get(pk=nid)

        # 获取 Detection 表中相关的数据
        detections = Detection.objects.filter(user=user)

        # 获取 Single 表中相关的数据
        # single_data = Single.objects.filter(image__user=user)
        single_data = Single.objects.select_related('image__user__role').filter(image__user=user)
        context = {
            'username': username,
            'user': user,
            'detections': detections,
            'single_data': single_data,
        }

        return render(request, "try.html", context)

    return redirect("/user_show/")
