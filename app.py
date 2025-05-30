from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import asyncio
from utils import SkillExtractor, ExcelHandler, ImageDownloader
import xlwings as xw
import pandas as pd
from urllib.parse import urlparse, parse_qs
import random
import string
from PIL import Image

app = Flask(__name__)
CORS(app)

# 统一读取项目配置
with open('project_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
EXCEL_PATH = config['EXCEL_PATH']
SHEET_NAME = config['SHEET_NAME']
IMG_SAVE_DIR = config['IMG_SAVE_DIR']
EXCEL_VALUES = config['EXCEL_VALUES']

@app.route('/bow/get', methods=['POST'])
def ocr_excel():
    try:
        data = request.get_json()
    except Exception as e:
        print(f"[ERROR] 解析请求体失败: {e}")
        return jsonify({'error': f'解析请求体失败: {e}'}), 400
    try:
        img_url = data.get('img_url')
    except Exception as e:
        print(f"[ERROR] 获取 img_url 失败: {e}")
        return jsonify({'error': f'获取 img_url 失败: {e}'}), 400
    if not img_url:
        print("[ERROR] img_url is required")
        return jsonify({'error': 'img_url is required'}), 400
    # 1. 下载图片（aiohttp异步，封装类）
    try:
        os.makedirs(IMG_SAVE_DIR, exist_ok=True)
    except Exception as e:
        print(f"[ERROR] 创建图片保存目录失败: {e}")
        return jsonify({'error': f'创建图片保存目录失败: {e}'}), 500
    try:
        parsed_url = urlparse(img_url)
        query = parse_qs(parsed_url.query)
        fileid_list = query.get('fileid', [])
        if fileid_list and fileid_list[0]:
            img_name = fileid_list[0] + '.png'
        else:
            img_name = ''.join(random.choices(string.ascii_letters + string.digits, k=16)) + '.png'
        # 确保 img_name 里没有任何斜杠，防止路径混用和文件写入异常
        img_name = img_name.replace('/', '_').replace('\\', '_')
        img_path = os.path.join(IMG_SAVE_DIR, img_name)
        print("[INFO] 图片保存路径: {}".format(img_path.replace('\\', '/')))
        # 新增：如果本地已存在同名图片，则直接使用本地文件，不再下载
        if os.path.exists(img_path):
            print(f"[INFO] 本地已存在图片 {img_path}，跳过下载。")
            need_download = False
        else:
            need_download = True
    except Exception as e:
        print(f"[ERROR] 解析图片路径失败: {e}")
        return jsonify({'error': f'解析图片路径失败: {e}'}), 500
    try:
        if need_download:
            asyncio.run(ImageDownloader.download_image_by_url(url=img_url, path=img_path))
    except Exception as e:
        print(f"[ERROR] 图片下载失败: {e}")
        return jsonify({'error': f'图片下载失败: {e}'}), 500
    # 2. OCR识别前，先用 PIL 检查图片有效性
    try:
        with Image.open(img_path) as im:
            im.verify()
    except Exception as e:
        print(f"[ERROR] 图片文件无效或已损坏: {e}")
        return jsonify({'error': f'图片文件无效或已损坏: {e}'}), 500
    # 2. OCR识别
    try:
        extractor = SkillExtractor()
    except Exception as e:
        print(f"[ERROR] 初始化SkillExtractor失败: {e}")
        return jsonify({'error': f'初始化SkillExtractor失败: {e}'}), 500
    try:
        # 修正：确保图片路径分隔符规范，避免 OCR 读取失败
        img_path = os.path.relpath(img_path)
        skill_dict = asyncio.run(extractor.extract(img_path))
        print(f"[INFO] OCR识别结果: {skill_dict}")
    except Exception as e:
        print(f"[ERROR] OCR识别失败: {e}")
        return jsonify({'error': f'OCR识别失败: {e}'}), 500
    # 3. 生成cell_map
    try:
        cell_map = {k: v['cell'] for k, v in EXCEL_VALUES.items() if 'cell' in v}
        print(f"[INFO] 生成的cell_map: {cell_map}")
    except Exception as e:
        print(f"[ERROR] 生成cell_map失败: {e}")
        return jsonify({'error': f'生成cell_map失败: {e}'}), 500
    # 4. 写入Excel
    try:
        handler = ExcelHandler(EXCEL_PATH, SHEET_NAME)
        handler.write_data(skill_dict, cell_map)
    except Exception as e:
        print(f"[ERROR] 写入Excel失败: {e}")
        return jsonify({'error': f'写入Excel失败: {e}'}), 500
    # 5. 用xlwings触发Excel计算并读取A45-B51
    try:
        with xw.App(visible=False) as app_xl:
            wb = app_xl.books.open(EXCEL_PATH)
            ws = wb.sheets[SHEET_NAME]
            df = ws.range('A45:B51').options(pd.DataFrame, header=False, index=False).value
            wb.save()
            wb.close()
        # 转为json
        result = df.to_dict(orient='split')
        # 新增：转为csv字符串
        csv_str = df.to_csv(index=False, header=False, encoding='utf-8')
    except Exception as e:
        print(f"[ERROR] Excel公式计算或读取失败: {e}")
        return jsonify({'error': f'Excel公式计算或读取失败: {e}'}), 500
    return jsonify({
        'ocr_result': skill_dict,
        'excel_result': result,
        'excel_csv': csv_str
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)