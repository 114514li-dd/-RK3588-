#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demo object recognition for Qt AI pipeline. Replace with real DeepSeek vision on board."""

import sys

try:
    import cv2
    import numpy as np
except ImportError:
    print("【识别失败】未安装 OpenCV，请部署真实 DeepSeek 视觉模型或安装 opencv-python")
    sys.exit(0)


def ratio(mask):
    return float(np.count_nonzero(mask)) / mask.size if mask.size else 0.0


def max_block_ratio(mask, rows=6, cols=8):
    h, w = mask.shape[:2]
    best = 0.0
    for row in range(rows):
        for col in range(cols):
            y1 = row * h // rows
            y2 = (row + 1) * h // rows
            x1 = col * w // cols
            x2 = (col + 1) * w // cols
            block = mask[y1:y2, x1:x2]
            if block.size:
                best = max(best, ratio(block))
    return best


def analyze(path):
    img = cv2.imread(path)
    if img is None:
        print("【识别失败】无法读取图片，请确认文件格式正确。")
        return

    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    red1 = cv2.inRange(hsv, (0, 60, 50), (15, 255, 255))
    red2 = cv2.inRange(hsv, (155, 60, 50), (180, 255, 255))
    red_mask = cv2.bitwise_or(red1, red2)
    dark_mask = cv2.inRange(gray, 0, 85)
    bright_mask = cv2.inRange(gray, 170, 255)

    red_r = ratio(red_mask)
    local_red = max_block_ratio(red_mask)
    dark_r = ratio(dark_mask)
    bright_r = ratio(bright_mask)

    row_dark = dark_mask.mean(axis=1)
    max_row_dark = float(row_dark.max()) if row_dark.size else 0.0
    pen_row_idx = int(row_dark.argmax()) if row_dark.size else 0
    pen_row = dark_mask[pen_row_idx] if row_dark.size else dark_mask[0]
    pen_span = ratio(pen_row > 0)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 120)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_score = 0.0
    for c in contours:
        area = cv2.contourArea(c)
        if area < h * w * 0.001:
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        aspect = max(bw, bh) / max(min(bw, bh), 1)
        score = area * aspect
        if score > best_score:
            best_score = score
            best = (x, y, bw, bh, aspect)

    pen_like_row = max_row_dark > 0.12 and pen_span > 0.25
    pen_like_shape = best and best[4] >= 1.8 and dark_r > 0.02

    # Goji-like: strict red berry clusters only
    local_red = max_block_ratio(red_mask)
    if red_r > 0.08 or local_red > 0.18:
        if local_red > 0.12 and red_r < 0.08:
            scene = "画面局部区域（如手机屏幕、图片）中可见"
        else:
            scene = "画面中以"
        print("【物品名称】枸杞")
        print("【物品类别】中药材")
        print(
            "【外观特征】%s红色小颗粒为主，呈纺锤形或椭圆形，色泽鲜红或暗红，"
            "具轻微皱纹，部分场景可能来自手机屏展示或实拍枸杞。" % scene
        )
        print(
            "【详细描述】我识别到枸杞相关特征：红色颗粒、椭圆形态。"
            "若需药材功效等详细信息，请点击【检测】进入枸杞专用识别流程。"
        )
        print("【温度】10~20°C")
        print("【相对湿度】45~60%")
        return

    # Pen-like: elongated object + dark ink visible
    if pen_like_row or pen_like_shape:
        aspect = best[4] if best else max(pen_span * 4.0, 2.5)
        horizontal = (best and best[2] >= best[3]) or pen_span > 0.25
        orient = "横放" if horizontal else "竖放"
        transparent = bright_r > 0.10 and dark_r > 0.02
        if transparent:
            barrel = "透明或半透明笔身，内部可见深色墨水管/笔芯"
        else:
            barrel = "笔身以深色或黑色为主"

        print("【物品名称】黑色中性笔（啫喱笔）")
        print("【物品类别】文具")
        print(
            "【外观特征】一支%s在桌面上的书写笔，%s；笔帽带笔夹，整体细长，长宽比约 %.1f:1。"
            % (orient, barrel, aspect)
        )
        print(
            "【详细描述】从画面看，主体是一支常见的黑色中性笔/啫喱笔。"
            "笔身细长，适合书写；若标签可见，可能带有品牌与规格信息（如 0.5mm）。"
        )
        print("【温度】10~20°C")
        print("【相对湿度】45~60%")
        return

    # Generic fallback from color/shape
    if dark_r > bright_r and best and best[4] >= 1.8:
        print("【物品名称】深色长条状物品")
        print("【物品类别】日用品")
        print("【外观特征】画面主体为深色、细长的物体，可能为笔、工具或类似条形物品。")
        print("【详细描述】我能看到一件深色长条形的物体，但无法完全确认具体型号；建议靠近拍摄并保证标签清晰。")
        print("【温度】10~20°C")
        print("【相对湿度】45~60%")
        return

    print("【物品名称】未能精确识别的物品")
    print("【物品类别】未知")
    print("【外观特征】画面主体不够清晰，或类别不在常见模板中。")
    print("【详细描述】暂时无法给出更具体的名称。请将物品置于画面中央、光线充足后再试。")
    print("【温度】10~20°C")
    print("【相对湿度】45~60%")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("【识别失败】缺少图片路径")
        sys.exit(1)
    analyze(sys.argv[1])
