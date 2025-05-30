# -*- coding: utf-8 -*-
import re
import json
import os
from paddleocr import PaddleOCR
from difflib import SequenceMatcher
import time
import tempfile

class SkillExtractor:
    def __init__(self, skill_list=None, ocr_kwargs=None):
        self.skill_list = skill_list or [
            "攻击", "逆袭", "无伤", "怨恨", "巧击", "急袭", "超会心", "龙属性攻击强化", "水属性攻击强化", "火属性攻击强化", "冰属性攻击强化", "雷属性攻击强化", "会心击【属性】", "蓄力大师", "连击", "因祸得福", "属性吸收", "挑战者", "看破", "弱点特效", "力量解放", "无我之境", "通常弹·通常箭强化", "贯穿弹·龙之箭强化", "散弹•刚射强化", "特殊射击强化", "套·黑蚀龙之力", "套·冻峰龙之反叛", "属性变换"
        ]
        self.ocr_kwargs = ocr_kwargs or dict(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False
        )
        try:
            self.ocr = PaddleOCR(**self.ocr_kwargs)
        except Exception as e:
            raise RuntimeError(f"初始化PaddleOCR失败: {e}")
        self.cache = {}  # url -> 结果缓存

    @staticmethod
    def similar(a, b):
        result = SequenceMatcher(None, a, b).ratio()
        return result

    @staticmethod
    def normalize_text(text):
        normalized = text.replace('•', '.').replace('·', '.').replace(' ', '').replace('　', '')
        return normalized

    @staticmethod
    def get_base_attack(attack_str):
        match = re.search(r'\((\d+)\)', attack_str)
        if match:
            return int(match.group(1))
        else:
            raise ValueError(f"攻击力字符串格式错误: {attack_str}")

    @staticmethod
    def get_crit_rate(crit_str):
        crit_str = crit_str.replace('％', '%')
        if '%' in crit_str:
            try:
                crit_rate = int(crit_str.strip().replace('%', ''))
                return crit_rate
            except Exception as e:
                raise ValueError(f"会心率字符串转数字失败: {crit_str}, {e}")
        else:
            raise ValueError(f"会心率字符串格式错误: {crit_str}")

    @staticmethod
    def calc_original_attack(panel_attack, attack_level):
        if attack_level == 1:
            return panel_attack - 3
        elif attack_level == 2:
            return panel_attack - 5
        elif attack_level == 3:
            return panel_attack - 7
        elif attack_level == 4:
            return int(round((panel_attack - 8) / 1.02))
        elif attack_level == 5:
            return int(round((panel_attack - 9) / 1.04))
        else:
            return panel_attack

    async def extract(self, image_path, output_dir=None):
        """
        支持 image_path（本地图片路径），自动缓存结果。
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)
        # 检查缓存
        if image_path in self.cache:
            return self.cache[image_path]

        skill_dict = {}
        ocr_time = None
        # 直接读取本地图片
        tmp_path = image_path
        try:
            start_time = time.time()
            result = self.ocr.predict(input=tmp_path)
            ocr_time = time.time() - start_time
        except Exception as e:
            raise RuntimeError(f"OCR识别失败: {e}")
        try:
            for res in result:
                res.print()
                res.save_to_img(output_dir)
                res.save_to_json(output_dir)
        except Exception as e:
            raise RuntimeError(f"OCR结果保存失败: {e}")
        # 读取json
        json_path = f"{output_dir}/" + os.path.basename(tmp_path).split('.')[0] + "_res.json"
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"读取OCR json失败: {json_path}, {e}")
        # 结构化数据
        try:
            results = []
            for text, score, poly in zip(data['rec_texts'], data['rec_scores'], data['rec_polys']):
                if score > 0.75 and text.strip():
                    results.append({'text': text, 'score': score, 'poly': poly})
        except Exception as e:
            raise RuntimeError(f"结构化OCR结果失败: {e}")
        # 攻击力、会心率
        for i, res in enumerate(results):
            try:
                if self.similar(res['text'], "攻击力") > 0.8:
                    attack_str = results[i+1]['text']
                    skill_dict["基础攻击力"] = self.get_base_attack(attack_str)
                    continue
                if self.similar(res['text'], "会心率") > 0.8:
                    crit_str = results[i+1]['text']
                    skill_dict["会心率"] = self.get_crit_rate(crit_str)
                    continue
            except Exception as e:
                pass
        # 技能等级提取
        for skill in self.skill_list:
            for i, res in enumerate(results):
                try:
                    if self.similar(self.normalize_text(res["text"]), self.normalize_text(skill)) > 0.8:
                        # 特殊处理“套·黑蚀龙之力”和“套·冻峰龙之反叛”
                        if skill in ["套·黑蚀龙之力", "套·冻峰龙之反叛"]:
                            for j in range(i+1, len(results)):
                                xj_text = self.normalize_text(results[j]["text"])
                                match = re.search(r"(\d+)\s*件", xj_text)
                                if match:
                                    skill_dict[skill] = int(match.group(1))
                                    break
                            break
                        # 普通技能等级查找
                        for j in range(i+1, len(results)):
                            lv_text = results[j]["text"].lower()
                            if "lv" in lv_text:
                                match = re.search(r"lv\.?\s*([0-9]+)", lv_text)
                                if match:
                                    skill_dict[skill] = int(match.group(1))
                                else:
                                    match = re.search(r"lv[\.|\s]*([0-9]+)", lv_text)
                                    if match:
                                        skill_dict[skill] = int(match.group(1))
                                break
                        break
                except Exception as e:
                    pass
        # 原始面板
        try:
            if "基础攻击力" in skill_dict and "攻击" in skill_dict:
                skill_dict["原始面板"] = self.calc_original_attack(skill_dict["基础攻击力"], skill_dict["攻击"])
        except Exception as e:
            pass
        skill_dict['ocr_time'] = ocr_time
        # 写入缓存
        self.cache[image_path] = skill_dict
        return skill_dict
    

# 用法示例：
# extractor = SkillExtractor()
# skill_dict = extractor.extract('bow.png')
# print(skill_dict)
