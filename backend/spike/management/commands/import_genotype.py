# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from spike.models import RiceGenotype
import pandas as pd
import math
import os

# Excel→模型字段映射（与你的 views.py 一致）
COLMAP = {
    'genotype': 'genotype',
    'species': 'species',
    'origin country': 'region',
    'classify1': 'raw_classify',
    'classify2': 'current_classify',
    'area': 'area',
    'length': 'length',
    'width': 'width',
    'l/w': 'l_w',
    'perimeter': 'perimeter',
    'diameter': 'diameter',
    'circu': 'Circularity',
    'compacthness': 'Compacthness',
    'r': 'Red_mean',
    'g': 'Green_mean',
    'b': 'Blue_mean',
    'h': 'Hue_mean',
    's': 'Saturation_mean',
    'v': 'Value_mean',
}

# 这些是“关键数值列”，如果缺失就跳过该行（避免写入 None 到非空 FloatField）
REQUIRED_NUMERIC = [
    'area', 'length', 'width', 'l_w', 'perimeter',
    'diameter', 'Circularity', 'Compacthness'
]

OPTIONAL_NUMERIC = ['Hue_mean', 'Saturation_mean', 'Value_mean']
RGB_FIELDS = ['Red_mean', 'Green_mean', 'Blue_mean']
TEXT_FIELDS = ['species', 'region', 'raw_classify', 'current_classify']

def is_nan_like(x):
    if x is None:
        return True
    if isinstance(x, float) and math.isnan(x):
        return True
    s = str(x).strip()
    return s == '' or s.lower() == 'nan'

def nz_str(x, default='Unknown'):
    return default if is_nan_like(x) else str(x).strip()

def safe_float(x):
    if is_nan_like(x):
        return None
    try:
        return float(x)
    except Exception:
        return None

def safe_int(x):
    fx = safe_float(x)
    if fx is None:
        return None
    try:
        return int(round(fx))
    except Exception:
        return None

class Command(BaseCommand):
    help = "Import genotype & trait data from an Excel file into RiceGenotype table."

    def add_arguments(self, parser):
        parser.add_argument('excel_path', type=str, help='Path to database_used_1105.xlsx')
        parser.add_argument('--truncate', action='store_true',
                            help='Clear RiceGenotype table before import.')

    def handle(self, *args, **options):
        excel_path = options['excel_path']
        if not os.path.exists(excel_path):
            raise CommandError(f"Excel file not found: {excel_path}")

        self.stdout.write(self.style.WARNING(f"Reading: {excel_path}"))
        df = pd.read_excel(excel_path, engine='openpyxl')

        # 列名清洗与校验
        df.columns = [c.strip() for c in df.columns]
        missing = [c for c in COLMAP.keys() if c not in df.columns]
        if missing:
            raise CommandError(f"Missing columns in Excel: {missing}")

        # 只保留需要列并重命名为模型字段
        df = df[list(COLMAP.keys())].rename(columns=COLMAP)

        # 记录统计
        total = len(df)
        imported = 0
        skipped = 0
        first_skip_msg = None

        with transaction.atomic():
            if options['truncate']:
                RiceGenotype.objects.all().delete()
                self.stdout.write(self.style.WARNING("Truncated RiceGenotype table."))

            # 逐行清洗并写库
            for i, row in df.iterrows():
                # genotype 缺失 → 跳过
                genotype = row.get('genotype')
                if is_nan_like(genotype):
                    skipped += 1
                    if first_skip_msg is None:
                        first_skip_msg = f"Row {i}: genotype is empty, skipped."
                    continue
                genotype = str(genotype).strip()

                # 文本列占位
                cleaned = {
                    'species': nz_str(row.get('species')),
                    'region': nz_str(row.get('region')),
                    'raw_classify': nz_str(row.get('raw_classify')),
                    'current_classify': nz_str(row.get('current_classify')),
                }

                # 关键数值列
                for col in REQUIRED_NUMERIC:
                    val = safe_float(row.get(col))
                    if val is None:
                        skipped += 1
                        if first_skip_msg is None:
                            first_skip_msg = f"Row {i}: required numeric '{col}' is missing, skipped."
                        break
                    cleaned[col] = val
                else:
                    # 可选数值列
                    for col in OPTIONAL_NUMERIC:
                        cleaned[col] = safe_float(row.get(col))

                    # RGB：转为整数，再转字符串（你的模型是 CharField）
                    for rgb_src, model_col in zip(['Red_mean', 'Green_mean', 'Blue_mean'], RGB_FIELDS):
                        v = safe_int(row.get(COLMAP[[k for k,vv in COLMAP.items() if vv == model_col][0]]))
                        cleaned[model_col] = None if v is None else str(v)

                    # 到这里说明关键列没缺失，可以写库
                    RiceGenotype.objects.update_or_create(
                        genotype=genotype,
                        defaults=cleaned
                    )
                    imported += 1
                    continue  # 成功写库，处理下一行

                # 如果上面 for-else 被 break（关键列缺失），这里会执行；跳过本行
                continue

        # 总结输出
        self.stdout.write(self.style.SUCCESS(
            f"Done. total={total}, imported={imported}, skipped={skipped}"
        ))
        if first_skip_msg:
            self.stdout.write(self.style.WARNING(f"First skip reason: {first_skip_msg}"))
