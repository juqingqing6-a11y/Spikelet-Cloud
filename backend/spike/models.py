from django.db import models


# Create your models here.
class Group(models.Model):
    """角色表"""

    description = models.CharField(verbose_name='用户权限', max_length=255)
    role = models.CharField(verbose_name='角色', max_length=8)


class User(models.Model):
    """用户信息表"""

    user = models.CharField(verbose_name='用户名', max_length=32)
    email = models.EmailField(verbose_name='邮箱')
    password = models.CharField(verbose_name='密码', max_length=64)
    role = models.ForeignKey(Group, verbose_name='角色外键', on_delete=models.CASCADE)

    def to_dict(self):
        return {
            'user': self.user,
            'role': self.role.role,  # 使用 self.role.role 获取 Group 对象的角色字符串
            # 添加其他需要保存的字段
        }


class Rice(models.Model):
    """计算稻穗的面积，周长，圆度以及长宽比"""
    area = models.FloatField(verbose_name='面积')
    perimeter = models.FloatField(verbose_name='周长')
    circularity = models.FloatField(verbose_name='圆度')
    aspect_ratio = models.FloatField(verbose_name='长宽比')


class Detection(models.Model):
    """在页面上展示目标检测结果"""
    pic = models.CharField(verbose_name='图片名称', max_length=255, default='path/to/result.jpg')
    target_pic = models.CharField(verbose_name='目标图片路径', max_length=255)
    result_pic = models.CharField(verbose_name='结果图片路径', max_length=255)
    user = models.ForeignKey(User, verbose_name='user外键', on_delete=models.CASCADE)


class Result(models.Model):
    """保存结果信息表"""
    select_model = models.CharField(verbose_name='选用的AI模型', max_length=255)
    single_total = models.CharField(verbose_name='总穗粒数', max_length=255)
    single_completed = models.CharField(verbose_name='完整穗粒总数', max_length=255)
    image = models.ForeignKey(Detection, verbose_name='detection外键', on_delete=models.CASCADE)


class Single(models.Model):
    """单张处理的时候性状表"""
    area = models.CharField(verbose_name='面积', max_length=10)
    length = models.CharField(verbose_name='长', max_length=10)
    width = models.CharField(verbose_name='宽', max_length=10)
    l_w = models.CharField(verbose_name='长宽比', max_length=10)   # 增加长宽比
    red_mean = models.CharField(verbose_name='红色均值', max_length=10)
    green_mean = models.CharField(verbose_name='绿色均值', max_length=10)
    blue_mean = models.CharField(verbose_name='蓝色均值', max_length=10)
    perimeter = models.CharField(verbose_name='周长', max_length=10)
    circularity = models.CharField(verbose_name='圆度', max_length=10)
    diameter = models.CharField(verbose_name='直径', max_length=10)
    compactness = models.CharField(verbose_name='紧致率', max_length=10)
    eccentricity = models.CharField(verbose_name='离心率', max_length=10)
    area_p_ratio = models.CharField(verbose_name='面积周长比', max_length=10)
    convex_area = models.CharField(verbose_name='凸包面积', max_length=10)
    hsv_h = models.CharField(verbose_name='hsv_h', max_length=10)
    hsv_s = models.CharField(verbose_name='hsv_s', max_length=10)
    hsv_v = models.CharField(verbose_name='hsv_v', max_length=10)
    lab_l = models.CharField(verbose_name='lab_l', max_length=10)
    lab_a = models.CharField(verbose_name='lab_a', max_length=10)
    lab_b = models.CharField(verbose_name='lab_b', max_length=10)
    yuv_y = models.CharField(verbose_name='yuv_y', max_length=10)
    yuv_u = models.CharField(verbose_name='yuv_u', max_length=10)
    yuv_v = models.CharField(verbose_name='yuv_v', max_length=10)
    xyz_x = models.CharField(verbose_name='xyz_x', max_length=10)
    xyz_y = models.CharField(verbose_name='xyz_y', max_length=10)
    xyz_z = models.CharField(verbose_name='xyz_z', max_length=10)
    cmy_c = models.CharField(verbose_name='cmy_c', max_length=10)
    cmy_m = models.CharField(verbose_name='cmy_m', max_length=10)
    cmy_y = models.CharField(verbose_name='cmy_y', max_length=10)
    image = models.ForeignKey(Detection, verbose_name='detection外键', on_delete=models.CASCADE)


class Batches(models.Model):
    """在页面上展示目标检测结果"""
    pic = models.CharField(verbose_name='图片名称', max_length=255, default='path/to/result.jpg')
    target_pic = models.CharField(verbose_name='上传图片路径', max_length=255)
    result_pic = models.CharField(verbose_name='结果图片路径', max_length=255)
    spike_pic = models.CharField(verbose_name='小穗粒存放路径', max_length=255)
    user = models.ForeignKey(User, verbose_name='user外键', on_delete=models.CASCADE)


class Results(models.Model):
    """保存结果信息表"""
    select_model = models.CharField(verbose_name='选用的AI模型', max_length=255)
    total = models.CharField(verbose_name='总穗数', max_length=255)
    sum = models.CharField(verbose_name='完整穗粒数', max_length=255)
    image = models.ForeignKey(Batches, verbose_name='Batches外键', on_delete=models.CASCADE)


class Download(models.Model):
    """批量图片性状表"""
    # pic = models.CharField(verbose_name='图片名称', max_length=255, default='path/to/result.jpg')

    area = models.CharField(verbose_name='area', max_length=10)                # 面积
    length = models.CharField(verbose_name='length', max_length=10)                # 长
    width = models.CharField(verbose_name='width', max_length=10)                 # 宽
    l_w = models.CharField(verbose_name='长宽比', max_length=10)  # 增加长宽比
    red_mean = models.CharField(verbose_name='red mean', max_length=10)         # 红色均值
    green_mean = models.CharField(verbose_name='green mean', max_length=10)       # 绿色均值
    blue_mean = models.CharField(verbose_name='blue mean', max_length=10)        # 蓝色均值
    perimeter = models.CharField(verbose_name='perimeter', max_length=10)            # 周长
    circularity = models.CharField(verbose_name='circularity', max_length=10)          # 圆度
    diameter = models.CharField(verbose_name='diameter', max_length=10)             # 直径
    compactness = models.CharField(verbose_name='compactness', max_length=10)        # 紧致度
    eccentricity = models.CharField(verbose_name='eccentricity', max_length=10)       # 离心率
    area_p_ratio = models.CharField(verbose_name='area perimeter ratio', max_length=10)    # 面积周长比
    convex_area = models.CharField(verbose_name='convex area', max_length=10)       # 凸包面积
    hsv_h = models.CharField(verbose_name='hsv_h', max_length=10)
    hsv_s = models.CharField(verbose_name='hsv_s', max_length=10)
    hsv_v = models.CharField(verbose_name='hsv_v', max_length=10)
    lab_l = models.CharField(verbose_name='lab_l', max_length=10)
    lab_a = models.CharField(verbose_name='lab_a', max_length=10)
    lab_b = models.CharField(verbose_name='lab_b', max_length=10)
    yuv_y = models.CharField(verbose_name='yuv_y', max_length=10)
    yuv_u = models.CharField(verbose_name='yuv_u', max_length=10)
    yuv_v = models.CharField(verbose_name='yuv_v', max_length=10)
    xyz_x = models.CharField(verbose_name='xyz_x', max_length=10)
    xyz_y = models.CharField(verbose_name='xyz_y', max_length=10)
    xyz_z = models.CharField(verbose_name='xyz_z', max_length=10)
    cmy_c = models.CharField(verbose_name='cmy_c', max_length=10)
    cmy_m = models.CharField(verbose_name='cmy_m', max_length=10)
    cmy_y = models.CharField(verbose_name='cmy_y', max_length=10)
    image = models.ForeignKey(Batches, verbose_name='Batches外键', on_delete=models.CASCADE)


#### add genotype database ####
# class RiceGenotype(models.Model):

#     ### add genotype ###
#     genotype = models.CharField(verbose_name='Genotype', max_length=50)
#     species = models.CharField(verbose_name='Species', max_length=50)
#     region = models.CharField(verbose_name='Region', max_length=50)
#     raw_classify = models.CharField(verbose_name='Raw classify', max_length=50)
#     current_classify = models.CharField(verbose_name='Current classify', max_length=50)
#     ### add genotype end ###

#     ### add traits ###
#     area = models.FloatField(verbose_name='Area', max_length=10)
#     length = models.FloatField(verbose_name='Length', max_length=10)
#     width = models.FloatField(verbose_name='Width', max_length=10)
#     l_w = models.FloatField(verbose_name='L_W', max_length=10)
#     perimeter = models.FloatField(verbose_name='Perimeter', max_length=10)
#     diameter = models.FloatField(verbose_name='Diameter', max_length=10)
#     Circularity = models.FloatField(verbose_name='Circularity', max_length=10)
#     Compacthness = models.FloatField(verbose_name='Compacthness', max_length=10)
#     Red_mean = models.CharField(verbose_name='Red mean', max_length=10)
#     Green_mean = models.CharField(verbose_name='Green mean', max_length=10)
#     Blue_mean = models.CharField(verbose_name='Blue mean', max_length=10)
#     Hue_mean = models.FloatField(verbose_name='Hue mean', max_length=10)
#     Saturation_mean = models.FloatField(verbose_name='Saturation mean', max_length=10)
#     Value_mean = models.FloatField(verbose_name='Value mean', max_length=10)
#     ### add traits end ###

class RiceGenotype(models.Model):
    ### add genotype ###
    genotype = models.CharField(verbose_name='Genotype', max_length=50, unique=True, db_index=True)
    species = models.CharField(verbose_name='Species', max_length=50, null=True, blank=True)
    region = models.CharField(verbose_name='Region', max_length=50, null=True, blank=True)
    raw_classify = models.CharField(verbose_name='Raw classify', max_length=50, null=True, blank=True)
    current_classify = models.CharField(verbose_name='Current classify', max_length=50, null=True, blank=True)
    ### add genotype end ###

    area = models.FloatField(verbose_name='Area')
    length = models.FloatField(verbose_name='Length')
    width = models.FloatField(verbose_name='Width')
    l_w = models.FloatField(verbose_name='L_W')
    perimeter = models.FloatField(verbose_name='Perimeter')
    diameter = models.FloatField(verbose_name='Diameter')
    Circularity = models.FloatField(verbose_name='Circularity')
    Compacthness = models.FloatField(verbose_name='Compacthness')

    # 你当前项目里 RGB 用的是 CharField，可以暂时保留；若以后想存 Int，再迁移一次
    Red_mean = models.CharField(verbose_name='Red mean', max_length=10, null=True, blank=True)
    Green_mean = models.CharField(verbose_name='Green mean', max_length=10, null=True, blank=True)
    Blue_mean = models.CharField(verbose_name='Blue mean', max_length=10, null=True, blank=True)

    Hue_mean = models.FloatField(verbose_name='Hue mean', null=True, blank=True)
    Saturation_mean = models.FloatField(verbose_name='Saturation mean', null=True, blank=True)
    Value_mean = models.FloatField(verbose_name='Value mean', null=True, blank=True)


#### add traits database  end ####
