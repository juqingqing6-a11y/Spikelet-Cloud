"""spike_test URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin

from django.urls import path
# from spike20240525.spike import views
from spike import views
from django.conf.urls.static import static
from django.conf import settings
from rest_framework_simplejwt.views import TokenObtainPairView

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('', views.login),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register),
    path('index/', views.index, name='index'),   
    path('user_single/', views.user_single),
    path('user_show/', views.user_show),
    path('user_add/', views.user_add),
    path('user_delete/', views.user_delete),
    path('user_show/<int:nid>/edit/', views.user_edit),
    path('sort/', views.sort),
    path('analyse/', views.new_analyse, name='upload-image'),   
    path('analyse/status/', views.analyse_status, name='analyse-status'),
    path('analyse/progress/', views.analyse_progress, name='analyse-progress'),  # ★ 新增 SSE 端点
    path('upload/', views.upload),
    path('entity/', views.entity),
    # path('show/', views.show_images),
    # 修改后的index界面
    path('test/', views.test, name='test'),
    path('atest/', views.atest),
    path('forget/', views.forget),
    # 测试yolov5和yolov7模型
    # path('ready/', views.ready, name='ready'),
    path('use/', views.use, name='use'),
    path('ccc/', views.ccc),
    path('complety/', views.complety, name='complety'),
    # path('totalImages/',views.totalImages,name='totalImages'),
    path('download/',views.download,name='download'),
    path('downloadSingle/',views.downloadSingle,name='downloadSingle'),
    path('getLatestDetection/', views.getLatestDetection, name='getLatestDetection'),
    path('try/',views.trySee),
    path('downloadTestimage/', views.downloadTestimage,name='downloadTestimage'),
    # path('pdf/', views.pdf_view, name='pdf_view'),
    # 增加数据库
    path('adatabase/', views.adatabase, name='adatabase'),
    path('adatabase2/<str:image_name>/', views.adatabase2, name='adatabase2'),
    path('downloadwhole/<str:image_name>/', views.downloadwhole, name='downloadwhole')

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # 添加这行URL配置来提供batch文件夹中图片的URL
    urlpatterns += static(settings.BATCH_URL, document_root=settings.BATCH_ROOT)
    # urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
