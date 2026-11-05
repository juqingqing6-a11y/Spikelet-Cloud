# middleware.py

import jwt
from django.http import JsonResponse
from django.conf import settings


class AuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 检查用户是否已登录
        if not request.user.is_authenticated:
            return JsonResponse({'error': '未经授权'}, status=401)

        # 获取请求头中的令牌
        token = request.META.get('HTTP_AUTHORIZATION', '').split(' ')[-1]

        if not token:
            return JsonResponse({'error': '未经授权'}, status=401)

        try:
            # 验证令牌
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': '令牌已过期'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': '无效令牌'}, status=401)

        response = self.get_response(request)
        return response
