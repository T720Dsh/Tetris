class_name TetrisConstants
extends RefCounted
## 全局常量：场地、模式、材质、背景、手感参数（移植自 1.3）

# ---------------- 场地
const COLS := 10
const ROWS := 20
const HIDDEN_TOP := 2
const LOCK_DELAY := 0.5
const LOCK_MAX_RESET := 15
const SOFT_DROP_SEC := 0.045
const DAS := 0.12
const ARR := 0.03
const BASE_GRAVITY_CPS := 1.0

# ---------------- 模式
const MODES: Array[String] = ["sprint20", "sprint40", "sprint100", "marathon", "blitz120", "cheese40", "endless"]
const MODE_NAME := {
	"sprint20": "竞速 20 行", "sprint40": "竞速 40 行", "sprint100": "竞速 100 行",
	"marathon": "马拉松 1500", "blitz120": "限时 120 秒", "cheese40": "奶酪突击 40",
	"endless": "无尽生存",
}
const MODE_DESC := {
	"sprint20": "热手冲刺，最快消 20 行",
	"sprint40": "以最快速度消 40 行",
	"sprint100": "以最快速度消 100 行",
	"marathon": "经典马拉松，达成 1500 分",
	"blitz120": "120 秒内冲击最高分",
	"cheese40": "场地预埋 10 行乱序垃圾，最快清 40 行",
	"endless": "重力持续加速，撑得越久越好",
}
const MODE_CFG := {
	"sprint20":  {"goal": "lines", "target": 20, "gravity": "20g", "garbage": 0, "record": "time"},
	"sprint40":  {"goal": "lines", "target": 40, "gravity": "20g", "garbage": 0, "record": "time"},
	"sprint100": {"goal": "lines", "target": 100, "gravity": "20g", "garbage": 0, "record": "time"},
	"marathon":  {"goal": "score", "target": 1500, "gravity": "marathon", "garbage": 0, "record": "score"},
	"blitz120":  {"goal": "time", "target": 120, "gravity": "20g", "garbage": 0, "record": "score"},
	"cheese40":  {"goal": "lines", "target": 40, "gravity": "20g", "garbage": 10, "record": "time"},
	"endless":   {"goal": "survive", "target": 0, "gravity": "endless", "garbage": 0, "record": "survive"},
}

# ---------------- 方块颜色（霓虹基色）
const PIECE_COLORS := {
	"I": Color(0.0, 0.94, 0.94),
	"O": Color(0.94, 0.94, 0.0),
	"T": Color(0.63, 0.0, 0.94),
	"S": Color(0.0, 0.94, 0.0),
	"Z": Color(0.94, 0.0, 0.0),
	"J": Color(0.0, 0.0, 0.94),
	"L": Color(0.94, 0.63, 0.0),
}

# ---------------- 材质（皮肤）
const SKIN_ORDER: Array[String] = ["luminous", "neon", "crystal", "metal", "pixel", "candy", "aurora"]
# 每套：名称 / 饱和度 / 金属度 / 粗糙度 / 自发光强度 / 辉光 / 顶面亮度 / 侧面亮度 / 暗面亮度
const SKINS := {
	"luminous": {"name": "光感玻璃", "sat": 0.94, "metal": 0.10, "rough": 0.22, "glow": 0.85, "emiss": 0.55, "top": 1.08, "mid": 0.80, "low": 0.58},
	"neon":     {"name": "霓虹",   "sat": 0.92, "metal": 0.05, "rough": 0.30, "glow": 1.00, "emiss": 0.85, "top": 1.10, "mid": 0.82, "low": 0.58},
	"crystal":  {"name": "水晶",   "sat": 1.00, "metal": 0.00, "rough": 0.10, "glow": 0.30, "emiss": 0.30, "top": 1.24, "mid": 0.92, "low": 0.66},
	"metal":    {"name": "金属",   "sat": 0.55, "metal": 0.92, "rough": 0.30, "glow": 0.0,  "emiss": 0.0,  "top": 0.88, "mid": 0.62, "low": 0.40},
	"pixel":    {"name": "像素",   "sat": 0.90, "metal": 0.00, "rough": 0.85, "glow": 0.0,  "emiss": 0.0,  "top": 1.02, "mid": 0.80, "low": 0.58},
	"candy":    {"name": "糖果",   "sat": 0.95, "metal": 0.05, "rough": 0.45, "glow": 0.40, "emiss": 0.30, "top": 1.14, "mid": 0.90, "low": 0.68},
	"aurora":   {"name": "流光",   "sat": 1.15, "metal": 0.15, "rough": 0.15, "glow": 1.20, "emiss": 0.95, "top": 1.26, "mid": 0.96, "low": 0.66},
}

# ---------------- 背景主题
const BG_THEMES: Array[String] = ["default", "nebula", "city", "aurora", "grid", "custom"]
const BG_THEME_NAME := {
	"default": "深蓝霓虹", "nebula": "星云深空", "city": "城市夜景",
	"aurora": "极光流", "grid": "赛博网格", "custom": "自定义图片",
}

# 主题环境色 (上/下渐变, 雾色, 装饰类型)
const BG_THEMES_CFG := {
	"default": {"sky_top": Color(0.055, 0.063, 0.133), "sky_bottom": Color(0.031, 0.035, 0.086), "fog": Color(0.04, 0.05, 0.10), "deco": "default"},
	"nebula":  {"sky_top": Color(0.05, 0.02, 0.12), "sky_bottom": Color(0.01, 0.01, 0.04), "fog": Color(0.02, 0.015, 0.06), "deco": "nebula"},
	"city":    {"sky_top": Color(0.04, 0.05, 0.09), "sky_bottom": Color(0.02, 0.03, 0.07), "fog": Color(0.03, 0.04, 0.08), "deco": "city"},
	"aurora":  {"sky_top": Color(0.01, 0.05, 0.10), "sky_bottom": Color(0.00, 0.01, 0.05), "fog": Color(0.01, 0.03, 0.07), "deco": "aurora"},
	"grid":    {"sky_top": Color(0.02, 0.03, 0.06), "sky_bottom": Color(0.01, 0.01, 0.03), "fog": Color(0.015, 0.02, 0.05), "deco": "grid"},
}

# ---------------- 手感
const GRAVITY_SPEEDS := {"off": 0.0, "very_slow": 0.15, "slow": 0.35, "normal": 1.0, "fast": 2.0}
const GRAVITY_NAMES := {"off": "关闭", "very_slow": "极慢", "slow": "慢速", "normal": "标准", "fast": "快速"}

# 默认键位（物理键码，Key 枚举）
const DEFAULT_KEYBINDS := {
	"move_left": KEY_LEFT, "move_right": KEY_RIGHT, "soft_drop": KEY_DOWN,
	"rotate_cw": KEY_UP, "rotate_ccw": KEY_Z, "rotate_180": KEY_A,
	"hard_drop": KEY_SPACE, "hold": KEY_C, "pause": KEY_ESCAPE,
	"restart": KEY_R, "view_left": KEY_Q, "view_right": KEY_E,
	"view_reset": KEY_V, "view_front": KEY_F,
}
const KEYBIND_LABELS := {
	"move_left": "左移", "move_right": "右移", "soft_drop": "软降",
	"rotate_cw": "顺时针旋转", "rotate_ccw": "逆时针旋转", "rotate_180": "旋转 180°",
	"hard_drop": "硬降", "hold": "暂存", "pause": "暂停", "restart": "重新开始",
	"view_left": "视角向左", "view_right": "视角向右", "view_reset": "复位视角", "view_front": "正面视角",
}

# 视角
const VIEW_DIST_DEFAULT := 18.0
const VIEW_DIST_MIN := 9.0
const VIEW_DIST_MAX := 32.0
const VIEW_SENSITIVITY_DEFAULT := 0.25
