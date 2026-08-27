# -*- coding: utf-8 -*-
"""智慧胸痛 App 图标生成器
产出：
- 应用图标 app_icon_1024.png（蓝渐变圆角方块 + 白心形 + 心电波形）
- 首页九宫格 8 个图标（白底圆角卡片 + 蓝色/红色图形）
- 底部 tab 3 个图标 x 2 状态（灰/蓝）
"""
import math
import os
from PIL import Image, ImageDraw

ROOT = r"D:\xiongtongzhongxin\FastapiAdmin-master\frontend\app\src\static"
ICON_DIR = os.path.join(ROOT, "icons")
TAB_DIR = os.path.join(ROOT, "tab")
os.makedirs(ICON_DIR, exist_ok=True)
os.makedirs(TAB_DIR, exist_ok=True)

# ── 调色板 ──
BLUE = (37, 99, 235)        # #2563eb 主蓝
BLUE_DARK = (29, 78, 216)   # #1d4ed8
BLUE_LIGHT = (14, 165, 233) # #0ea5e9
RED = (239, 68, 68)         # #ef4444
GRAY = (156, 163, 175)      # #9ca3af
WHITE = (255, 255, 255)
BORDER = (228, 231, 235)    # #e4e7eb


def vgrad(w, h, top, bottom):
    """垂直渐变 RGBA 图"""
    img = Image.new("RGBA", (w, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
        for x in range(w):
            img.putpixel((x, y), c)
    return img


def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def heart_points(cx, cy, scale, steps=240):
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * scale, cy - y * scale))
    return pts


def draw_app_icon(size=1024):
    """蓝渐变圆角方块 + 白色心形 + 蓝色心电波形"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pad = size * 0.035
    grad = vgrad(size, size, BLUE, BLUE_LIGHT)
    mask = rounded_mask(size, int(size * 0.22))
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    # 白色心形（居中，参数方程 x∈[-16,16] y∈[-17,5]，scale 控制大小）
    scale = size / 62  # 1024 时约 16.5，整体在画布内
    cx, cy = size * 0.5, size * 0.54
    pts = heart_points(cx, cy, scale)
    d.polygon(pts, fill=WHITE)
    # 心电波形（深蓝色，居于心形中部）
    ecg = [
        (cx - size * 0.17, cy),
        (cx - size * 0.09, cy),
        (cx - size * 0.05, cy - size * 0.07),
        (cx + size * 0.02, cy + size * 0.08),
        (cx + size * 0.08, cy - size * 0.05),
        (cx + size * 0.12, cy),
        (cx + size * 0.17, cy),
    ]
    d.line(ecg, fill=BLUE_DARK, width=int(size * 0.028), joint="curve")
    img.save(os.path.join(ICON_DIR, "app_icon_1024.png"))
    return img


# ── 九宫格图标：白底圆角卡片 + 图形 ──

def card_canvas(size=200):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, size - 7, size - 7], radius=int(size * 0.18), fill=WHITE, outline=BORDER, width=3)
    return img, ImageDraw.Draw(img)


def save_nav(name, img):
    img.save(os.path.join(ICON_DIR, f"nav_{name}.png"))


def make_data_icon():
    img, d = card_canvas()
    # 蓝色文档 + 白色横线 + 折角
    d.rounded_rectangle([62, 44, 138, 156], radius=14, fill=BLUE)
    for y in (78, 102, 126):
        d.line([(76, y), (124, y)], fill=WHITE, width=7)
    d.polygon([(118, 44), (138, 64), (118, 64)], fill=BLUE_LIGHT)
    save_nav("data", img)


def make_analysis_icon():
    img, d = card_canvas()
    # 蓝色柱状图
    bars = [(66, 100, 88, 158), (92, 62, 114, 158), (118, 124, 140, 158)]
    for x1, y1, x2, y2 in bars:
        d.rounded_rectangle([x1, y1, x2, y2], radius=8, fill=BLUE)
    d.line([(60, 158), (146, 158)], fill=BLUE_LIGHT, width=6)
    save_nav("analysis", img)


def make_followup_icon():
    img, d = card_canvas()
    # 蓝色日历 + 白色对勾
    d.rounded_rectangle([60, 50, 140, 152], radius=16, fill=BLUE)
    d.rounded_rectangle([60, 50, 140, 76], radius=12, fill=BLUE_DARK)
    for x in (78, 122):
        d.rounded_rectangle([x - 4, 38, x + 4, 58], radius=3, fill=BLUE_DARK)
    d.line([(76, 112), (92, 128), (124, 94)], fill=WHITE, width=9, joint="curve")
    save_nav("followup", img)


def make_hospital_icon():
    img, d = card_canvas()
    # 蓝色建筑 + 白色十字
    d.rounded_rectangle([58, 58, 142, 156], radius=12, fill=BLUE)
    d.line([(100, 44), (100, 62)], fill=BLUE, width=10)
    d.rounded_rectangle([88, 78, 112, 140], radius=6, fill=WHITE)
    d.rounded_rectangle([82, 102, 118, 116], radius=6, fill=WHITE)
    save_nav("hospital", img)


def make_meeting_icon():
    img, d = card_canvas()
    # 蓝色演示屏 + 白色播放三角 + 底座
    d.rounded_rectangle([58, 44, 142, 128], radius=12, fill=BLUE)
    d.rounded_rectangle([84, 128, 116, 142], radius=4, fill=BLUE)
    d.line([(70, 148), (130, 148)], fill=BLUE, width=7)
    d.polygon([(86, 62), (86, 110), (122, 86)], fill=WHITE)
    save_nav("meeting", img)


def make_academy_icon():
    img, d = card_canvas()
    # 蓝色书本（两页打开）
    d.rounded_rectangle([60, 52, 98, 148], radius=10, fill=BLUE)
    d.rounded_rectangle([102, 52, 140, 148], radius=10, fill=BLUE_DARK)
    d.line([(100, 52), (100, 148)], fill=WHITE, width=5)
    for y in (76, 100, 124):
        d.line([(70, y), (90, y)], fill=WHITE, width=5)
        d.line([(110, y), (130, y)], fill=WHITE, width=5)
    save_nav("academy", img)


def make_ecg_icon():
    img, d = card_canvas()
    # 红色心电波形 + 蓝色圆点
    ecg = [(58, 102), (80, 102), (90, 80), (100, 122), (110, 94), (120, 102), (142, 102)]
    d.line(ecg, fill=RED, width=8, joint="curve")
    d.ellipse([56, 60, 72, 76], fill=BLUE)
    d.ellipse([128, 132, 144, 148], fill=BLUE_LIGHT)
    save_nav("ecg", img)


def make_triage_icon():
    img, d = card_canvas()
    # 蓝色急救箱 + 白色十字 + 红色提手
    d.rounded_rectangle([56, 64, 144, 148], radius=16, fill=BLUE)
    d.rounded_rectangle([84, 44, 116, 62], radius=8, fill=RED)
    d.rounded_rectangle([88, 86, 112, 128], radius=6, fill=WHITE)
    d.rounded_rectangle([80, 102, 120, 112], radius=6, fill=WHITE)
    d.line([(56, 118), (72, 118)], fill=BLUE_LIGHT, width=7)
    save_nav("triage", img)


# ── tab 图标：透明底单色 ──

def tab_canvas(size=200):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def save_tab(name, color, img):
    img.save(os.path.join(TAB_DIR, f"{name}_{'active' if color == BLUE else 'gray'}.png"))


def make_tab_home(color):
    img, d = tab_canvas()
    d.polygon([(100, 36), (44, 84), (156, 84)], fill=color)
    d.rounded_rectangle([54, 82, 146, 158], radius=10, fill=color)
    d.rounded_rectangle([88, 116, 112, 158], radius=6, fill=WHITE)
    save_tab("home", color, img)


def make_tab_chat(color):
    img, d = tab_canvas()
    d.rounded_rectangle([40, 44, 160, 132], radius=28, fill=color)
    d.polygon([(58, 132), (58, 160), (84, 132)], fill=color)
    for cx in (78, 100, 122):
        d.ellipse([cx - 9, 82, cx + 9, 100], fill=WHITE)
    save_tab("chat", color, img)


def make_tab_user(color):
    img, d = tab_canvas()
    d.ellipse([78, 34, 122, 78], fill=color)
    d.pieslice([46, 96, 154, 216], 180, 360, fill=color)
    save_tab("user", color, img)


if __name__ == "__main__":
    draw_app_icon(1024)
    # favicon 192
    app = draw_app_icon(192)
    app.save(os.path.join(ICON_DIR, "app_icon_192.png"))
    make_data_icon()
    make_analysis_icon()
    make_followup_icon()
    make_hospital_icon()
    make_meeting_icon()
    make_academy_icon()
    make_ecg_icon()
    make_triage_icon()
    for c in (GRAY, BLUE):
        make_tab_home(c)
        make_tab_chat(c)
        make_tab_user(c)
    print("ALL ICONS GENERATED")
    for f in sorted(os.listdir(ICON_DIR)) + sorted(os.listdir(TAB_DIR)):
        print(f)
