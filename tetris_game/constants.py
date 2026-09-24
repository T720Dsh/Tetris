"""全局常量：窗口、布局、颜色、手感参数"""
from __future__ import annotations

# ---------------------------------------------------------------- 窗口
WIN_W, WIN_H = 1280, 800
FPS = 60
TITLE = "TETRIS 3D RUSH · 竞速方块"

# ---------------------------------------------------------------- 场地
COLS, ROWS = 10, 20          # 可见场地 10 x 20
HIDDEN_TOP = 2               # 顶部隐藏行（出生用）
LOCK_DELAY = 0.500           # 锁定延迟（秒）
LOCK_MAX_RESET = 15          # 锁定延迟重置上限（防无限蹭）
SOFT_DROP_SEC = 0.045        # 软降每格秒数（≈22 格/秒）
DAS = 0.120                  # 移动首按延迟（秒）
ARR = 0.030                  # 移动重复间隔（秒）
GRAVITY_20G = 20.0           # 20G：每帧下落格数（60fps 下即瞬间落地）

# ---------------------------------------------------------------- 模式
# goal:   lines  = 消行数达标 | score = 分数达标 | time = 存活满时间 | survive = 无尽存活
# record: time  = 最佳用时（越小越好）| score = 最高分 | survive = 存活时间（越大越好）
MODES = ("sprint20", "sprint40", "sprint100", "marathon", "blitz120", "cheese40", "endless")
MODE_NAME = {
    "sprint20": "竞速 20 行",
    "sprint40": "竞速 40 行",
    "sprint100": "竞速 100 行",
    "marathon": "马拉松 1500",
    "blitz120": "限时 120 秒",
    "cheese40": "奶酪突击 40",
    "endless": "无尽生存",
}
MODE_DESC = {
    "sprint20": "热手冲刺，最快消 20 行",
    "sprint40": "以最快速度消 40 行",
    "sprint100": "以最快速度消 100 行",
    "marathon": "经典马拉松，达成 1500 分",
    "blitz120": "120 秒内冲击最高分",
    "cheese40": "场地预埋 10 行乱序垃圾，最快清 40 行",
    "endless": "重力持续加速，撑得越久越好",
}
MODE_CFG = {
    "sprint20":  {"goal": "lines",   "target": 20,  "gravity": "20g",     "garbage": 0,  "record": "time"},
    "sprint40":  {"goal": "lines",   "target": 40,  "gravity": "20g",     "garbage": 0,  "record": "time"},
    "sprint100": {"goal": "lines",   "target": 100, "gravity": "20g",     "garbage": 0,  "record": "time"},
    "marathon":  {"goal": "score",   "target": 1500, "gravity": "marathon", "garbage": 0, "record": "score"},
    "blitz120":  {"goal": "time",    "target": 120, "gravity": "20g",     "garbage": 0,  "record": "score"},
    "cheese40":  {"goal": "lines",   "target": 40,  "gravity": "20g",     "garbage": 10, "record": "time"},
    "endless":   {"goal": "survive", "target": 0,   "gravity": "endless", "garbage": 0,  "record": "survive"},
}

# ---------------------------------------------------------------- 颜色（霓虹风）
BG_TOP = (14, 16, 34)
BG_BOT = (8, 9, 22)

PIECE_COLORS = {
    "I": (0, 224, 255),
    "O": (255, 214, 0),
    "T": (178, 102, 255),
    "S": (0, 230, 118),
    "Z": (255, 77, 109),
    "J": (77, 150, 255),
    "L": (255, 158, 0),
}
GHOST_ALPHA = 70
GRID_LINE = (255, 255, 255)
GRID_ALPHA = 22

PANEL_FILL = (16, 20, 44, 150)
PANEL_BORDER = (110, 130, 255, 90)
ACCENT = (0, 224, 255)
ACCENT2 = (178, 102, 255)
DANGER = (255, 60, 90)
GOOD = (0, 230, 118)
TEXT_MAIN = (235, 240, 255)
TEXT_DIM = (150, 160, 200)

# 渲染
CELL = 20                      # 等距半宽（像素）
CUBE_H = 22                    # 方块挤出高度
BOARD_CX = 655                 # 场地在屏幕上的中心
BOARD_CY = 425

# ---------------------------------------------------------------- 方块材质（皮肤）
# top/east/south/edge：三面与描边的明暗系数；saturation：饱和度；glow：活动块辉光；
# alpha：不透明度；edge_w：描边宽度；pattern：顶面装饰图案
SKINS = {
    "neon":    {"name": "霓虹",   "top": 1.18, "east": 0.92, "south": 0.62, "edge": 0.45,
                "saturation": 1.00, "glow": True,  "alpha": 255, "edge_w": 1, "pattern": None},
    "crystal": {"name": "水晶",   "top": 1.32, "east": 1.00, "south": 0.72, "edge": 0.55,
                "saturation": 1.00, "glow": False, "alpha": 235, "edge_w": 1, "pattern": "crystal"},
    "metal":   {"name": "金属",   "top": 0.88, "east": 0.62, "south": 0.40, "edge": 0.28,
                "saturation": 0.55, "glow": False, "alpha": 255, "edge_w": 1, "pattern": "metal"},
    "pixel":   {"name": "像素",   "top": 1.02, "east": 0.80, "south": 0.58, "edge": 0.12,
                "saturation": 0.90, "glow": False, "alpha": 255, "edge_w": 2, "pattern": "pixel"},
    "candy":   {"name": "糖果",   "top": 1.14, "east": 0.90, "south": 0.68, "edge": 0.34,
                "saturation": 0.95, "glow": False, "alpha": 255, "edge_w": 1, "pattern": "candy"},
    "aurora":  {"name": "流光",   "top": 1.26, "east": 0.96, "south": 0.66, "edge": 0.50,
                "saturation": 1.15, "glow": True, "alpha": 255, "edge_w": 1, "pattern": None},
}
SKIN_ORDER = ("neon", "crystal", "metal", "pixel", "candy", "aurora")

# ---------------------------------------------------------------- 背景主题
BG_THEMES = ("default", "nebula", "city", "aurora", "grid", "custom")
BG_THEME_NAME = {
    "default": "深蓝霓虹",
    "nebula": "星云深空",
    "city": "城市夜景",
    "aurora": "极光流",
    "grid": "赛博网格",
    "custom": "自定义图片",
}
