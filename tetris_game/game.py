"""游戏主逻辑：状态机、输入（DAS/ARR）、更新、绘制"""
from __future__ import annotations
import json
import math
import os
import random
from typing import Callable

import pygame

from . import ui
from .audio import Synth
from .board import Board
from .constants import (WIN_W, WIN_H, TEXT_MAIN, TEXT_DIM, ACCENT, ACCENT2,
                        DANGER, GOOD, MODES, MODE_NAME, MODE_DESC, MODE_CFG, PIECE_COLORS,
                        COLS, ROWS, DAS, ARR, SOFT_DROP_SEC,
                        SKINS, SKIN_ORDER, BG_THEMES, BG_THEME_NAME)
from .pieces import ALL_CELLS, Bag7
from .renderer import Renderer, make_particles_for_clear, update_particles, draw_bg_theme

SCENE_RECT = pygame.Rect(286, 88, 766, 584)

DEFAULT_KEYBINDS = {
    "move_left": pygame.K_LEFT,
    "move_right": pygame.K_RIGHT,
    "soft_drop": pygame.K_DOWN,
    "rotate_cw": pygame.K_UP,
    "rotate_ccw": pygame.K_z,
    "rotate_180": pygame.K_a,
    "hard_drop": pygame.K_SPACE,
    "hold": pygame.K_c,
    "pause": pygame.K_ESCAPE,
    "restart": pygame.K_r,
    "view_left": pygame.K_q,
    "view_right": pygame.K_e,
    "view_reset": pygame.K_v,
    "view_front": pygame.K_f,
}

KEYBIND_LABELS = {
    "move_left": "左移", "move_right": "右移", "soft_drop": "软降",
    "rotate_cw": "顺时针旋转", "rotate_ccw": "逆时针旋转",
    "rotate_180": "旋转 180°", "hard_drop": "硬降", "hold": "暂存",
    "pause": "暂停", "restart": "重新开始", "view_left": "视角向左",
    "view_right": "视角向右", "view_reset": "复位视角",
    "view_front": "正面视角",
}

GRAVITY_SPEEDS = {
    "off": 0.0,
    "very_slow": 0.15,
    "slow": 0.35,
    "normal": 1.0,
    "fast": 2.0,
}
GRAVITY_NAMES = {
    "off": "关闭", "very_slow": "极慢", "slow": "慢速",
    "normal": "标准", "fast": "快速",
}

_SETTINGS_DEFAULTS = {
    "das": DAS, "arr": ARR, "ghost": True, "sound": True, "volume": 0.7,
    "skin": "neon", "bg_theme": "default", "custom_bg": "", "fullscreen": False,
    "gravity_speed": "very_slow", "view_sensitivity": 0.25, "settings_version": 3,
}


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Game:
    def __init__(self, screen: pygame.Surface, records_path: str,
                 fullscreen_toggle: Callable[[bool | None], bool] | None = None):
        self.screen = screen
        self.records_path = records_path
        self.fonts = ui.Fonts()
        self.renderer = Renderer()
        self.renderer.set_viewport(SCENE_RECT)
        self.records = self._load_records()
        self.settings = self._load_settings()
        self.fullscreen_toggle = fullscreen_toggle
        self.renderer.set_skin(self.settings["skin"])
        if self.settings["bg_theme"] == "custom" and self.settings.get("custom_bg"):
            if not self.renderer.load_custom_bg(self.settings["custom_bg"]):
                self.settings["bg_theme"] = "default"
        self.synth = Synth()
        self.rng = random.Random()
        self.state = "menu"
        self.mode = "sprint40"
        self.board: Board | None = None
        self.bag: Bag7 | None = None

        # 计时
        self.elapsed = 0.0
        self.bg_time = 0.0
        self.countdown = 0.0
        self.pps = 0.0

        # 特效
        self.particles: list[dict] = []
        self.rings: list[dict] = []
        self.popups: list[dict] = []
        self.flash_rows: list[tuple[int, float]] = []
        self.shake = 0.0
        self.combo_banner = 0.0
        self.danger_warn_t = 0.0
        self.dust: list[dict] = []
        self._init_dust()
        self.stage_ambient = self._build_stage_ambient()

        # 输入状态
        self.keys_held: set[int] = set()
        self.das_acc = 0.0
        self.arr_acc = 0.0
        self.soft_acc = 0.0
        self.mouse_pos = (0, 0)
        self.dragging = False
        self.last_mouse = (0, 0)
        self.drag_filtered = (0.0, 0.0)
        self.buttons: list[ui.Button] = []
        self.win = False
        self.new_record = False

        # 设置界面状态
        self.settings_idx = 0
        self.settings_return_state = "menu"
        self.keybind_idx = 0
        self.binding_capture: str | None = None
        self.binding_notice = ""
        self.settings_items = [
            ("das", "移动延迟 DAS", 0.040, 0.300, 0.005),
            ("arr", "重复间隔 ARR", 0.000, 0.120, 0.005),
            ("gravity_speed", "自动下落", None, None, tuple(GRAVITY_SPEEDS)),
            ("ghost", "幽灵投影", None, None, None),
            ("sound", "音效", None, None, None),
            ("volume", "音量", 0.0, 1.0, 0.05),
            ("view_sensitivity", "视角灵敏度", 0.10, 0.65, 0.05),
            ("skin", "方块材质", None, None, tuple(SKIN_ORDER)),
            ("bg_theme", "背景主题", None, None, tuple(BG_THEMES)),
            ("bg_upload", "上传背景图…", None, None, None),
            ("fullscreen", "全屏显示", None, None, None),
            ("controls", "自定义键位…", None, None, None),
        ]

    # ------------------------------------------------------------ 记录
    def _load_records(self) -> dict:
        defaults = {m: None for m in MODES}
        try:
            with open(self.records_path, "r", encoding="utf-8") as f:
                defaults.update(json.load(f))
        except Exception:
            pass
        return defaults

    def save_records(self) -> None:
        try:
            with open(self.records_path, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ------------------------------------------------------------ 设置持久化
    def _settings_path(self) -> str:
        d = os.path.dirname(os.path.abspath(self.records_path))
        return os.path.join(d, "settings.json")

    def _load_settings(self) -> dict:
        st = dict(_SETTINGS_DEFAULTS)
        st["keybinds"] = dict(DEFAULT_KEYBINDS)
        try:
            with open(self._settings_path(), "r", encoding="utf-8") as f:
                loaded = json.load(f)
                bindings = loaded.pop("keybinds", {})
                old_version = int(loaded.get("settings_version", 0))
                st.update(loaded)
                # v3 changes the mouse curve.  Migrate the formerly aggressive
                # default even for players who already have a settings file.
                if old_version < 3:
                    st["view_sensitivity"] = 0.25
                st["settings_version"] = 3
                for action, key in bindings.items():
                    if action in DEFAULT_KEYBINDS and isinstance(key, int):
                        st["keybinds"][action] = key
        except Exception:
            pass
        return st

    def set_fullscreen_state(self, enabled: bool) -> None:
        self.settings["fullscreen"] = bool(enabled)
        self.save_settings()

    def _key(self, action: str) -> int:
        return self.settings["keybinds"].get(action, DEFAULT_KEYBINDS[action])

    def _pressed(self, action: str, key: int) -> bool:
        return key == self._key(action)

    def _held(self, action: str) -> bool:
        return self._key(action) in self.keys_held

    def save_settings(self) -> None:
        try:
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ------------------------------------------------------------ 开局
    def new_game(self, mode: str) -> None:
        self.mode = mode
        self.board = Board(mode)
        gravity_key = self.settings.get("gravity_speed", "very_slow")
        self.board.gravity_scale_override = GRAVITY_SPEEDS.get(gravity_key, 0.15)
        self.bag = Bag7(self.rng)
        self.board.bag = self.bag
        cfg = MODE_CFG.get(mode, {})
        if cfg.get("garbage"):
            self.board.seed_garbage(cfg["garbage"], self.rng)
        self.board.refill_next(self.bag)
        self.board.spawn()
        self.elapsed = 0.0
        self.countdown = 3.0
        self.win = False
        self.new_record = False
        self.particles.clear()
        self.rings.clear()
        self.popups.clear()
        self.flash_rows.clear()
        self.shake = 0.0
        self.state = "countdown"
        self.sound("countdown")

    def restart(self) -> None:
        self.new_game(self.mode)

    # ------------------------------------------------------------ 音效
    def sound(self, name: str) -> None:
        if self.settings["sound"]:
            self.synth.play(name)

    # ------------------------------------------------------------ 输入事件
    def on_key_down(self, key: int, mods: int) -> None:
        self.keys_held.add(key)

        if self.state == "menu":
            self._menu_key(key)
            return
        if self.state == "settings":
            self._settings_key(key)
            return
        if self.state == "keybinds":
            self._keybinds_key(key)
            return
        if self.state == "countdown":
            return
        if self.state == "gameover":
            if key in (pygame.K_RETURN, pygame.K_r, pygame.K_SPACE):
                self.restart()
            elif key == pygame.K_ESCAPE:
                self.state = "menu"
            return
        if self.state == "paused":
            if self._pressed("pause", key) or key == pygame.K_RETURN:
                self.state = "playing"
            elif self._pressed("restart", key):
                self.restart()
            return

        # playing
        b = self.board
        if self._pressed("pause", key):
            self.state = "paused"
        elif self._pressed("restart", key):
            self.restart()
        elif self._pressed("rotate_cw", key):
            self._try_rotate(1)
        elif self._pressed("rotate_ccw", key):
            self._try_rotate(-1)
        elif self._pressed("rotate_180", key):
            self._try_rotate(2)
        elif self._pressed("view_left", key):
            self.rotate_view(-0.10, 0.0)
        elif self._pressed("view_right", key):
            self.rotate_view(0.10, 0.0)
        elif self._pressed("view_reset", key):
            self.renderer.set_view(0.0, 0.0)
        elif self._pressed("view_front", key):
            self.renderer.set_front_view()
        elif self._pressed("hard_drop", key):
            self._hard_drop()
        elif self._pressed("hold", key):
            self._hold()
        elif key in (self._key("move_left"), self._key("move_right")):
            self.das_acc = 0.0
            self.arr_acc = 0.0
            self._move_held(key)

    def on_key_up(self, key: int) -> None:
        self.keys_held.discard(key)
        if key in (self._key("move_left"), self._key("move_right")):
            self.das_acc = 0.0
            self.arr_acc = 0.0

    def _menu_key(self, key: int) -> None:
        if key in (pygame.K_UP, pygame.K_w):
            self._move_selection(-1)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self._move_selection(1)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self._activate_selected()
        elif key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _settings_key(self, key: int) -> None:
        key_name, _, lo, hi, step = self.settings_items[self.settings_idx]
        if key_name == "controls" and key in (pygame.K_LEFT, pygame.K_RIGHT,
                                                pygame.K_SPACE, pygame.K_RETURN):
            self.state = "keybinds"
            self.keybind_idx = 0
            self.binding_capture = None
            self.binding_notice = "选择一项后按 Enter 或直接点击，再按新键"
            self.keys_held.clear()
            self.buttons = []
            self.sound("ui_ok")
            return
        if key_name == "bg_upload":
            if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_SPACE, pygame.K_RETURN):
                self._pick_bg_image()
            elif key in (pygame.K_ESCAPE, pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
                if key == pygame.K_ESCAPE:
                    self.sound("ui_ok")
                    self._back_from_settings()
                else:
                    self.settings_idx = (self.settings_idx - 1 if key in (pygame.K_UP, pygame.K_w)
                                         else self.settings_idx + 1) % len(self.settings_items)
                    self.sound("ui_move")
            return
        if key == pygame.K_ESCAPE:
            self.sound("ui_ok")
            self._back_from_settings()
            return
        if key in (pygame.K_UP, pygame.K_w):
            self.settings_idx = (self.settings_idx - 1) % len(self.settings_items)
            self.sound("ui_move")
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.settings_idx = (self.settings_idx + 1) % len(self.settings_items)
            self.sound("ui_move")
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            if key_name == "fullscreen":
                target = not self.settings["fullscreen"]
                if self.fullscreen_toggle:
                    target = self.fullscreen_toggle(target)
                self.settings["fullscreen"] = target
            elif step is None:
                # 开关
                self.settings[key_name] = not self.settings[key_name]
            elif isinstance(step, tuple):
                # 循环选项（材质 / 背景）
                opts = step
                i = opts.index(self.settings[key_name])
                d = 1 if key == pygame.K_RIGHT else -1
                self.settings[key_name] = opts[(i + d) % len(opts)]
            else:
                d = 1 if key == pygame.K_RIGHT else -1
                self.settings[key_name] = _clamp(self.settings[key_name] + d * step, lo, hi)
            if key_name == "skin":
                self.renderer.set_skin(self.settings["skin"])
            elif key_name == "gravity_speed" and self.board:
                self.board.gravity_scale_override = GRAVITY_SPEEDS[self.settings["gravity_speed"]]
            self.save_settings()
            self.sound("ui_move")

    def _keybinds_key(self, key: int) -> None:
        actions = list(KEYBIND_LABELS)
        if self.binding_capture is not None:
            if key == pygame.K_ESCAPE:
                self.binding_capture = None
                self.binding_notice = "已取消修改"
                self.sound("ui_move")
                return
            if key == pygame.K_UNKNOWN:
                self.binding_notice = "未识别这个按键，请换一个键"
                return
            action = self.binding_capture
            old_key = self._key(action)
            conflict = next((name for name in actions
                             if name != action and self._key(name) == key), None)
            self.settings["keybinds"][action] = key
            if conflict:
                self.settings["keybinds"][conflict] = old_key
                self.binding_notice = (f"已设置 {KEYBIND_LABELS[action]}，并与"
                                       f" {KEYBIND_LABELS[conflict]} 交换")
            else:
                self.binding_notice = f"已设置 {KEYBIND_LABELS[action]}"
            self.binding_capture = None
            self.save_settings()
            self.sound("ui_ok")
            return
        if key == pygame.K_ESCAPE:
            self.state = "settings"
            self.buttons = []
        elif key in (pygame.K_UP, pygame.K_w):
            self.keybind_idx = (self.keybind_idx - 1) % len(actions)
            self.sound("ui_move")
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.keybind_idx = (self.keybind_idx + 1) % len(actions)
            self.sound("ui_move")
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self.binding_capture = actions[self.keybind_idx]
            self.binding_notice = "等待按键输入…"
            self.sound("ui_ok")
        elif key in (pygame.K_BACKSPACE, pygame.K_DELETE):
            action = actions[self.keybind_idx]
            self.settings["keybinds"][action] = DEFAULT_KEYBINDS[action]
            self.binding_notice = f"{KEYBIND_LABELS[action]} 已恢复默认"
            self.save_settings()
            self.sound("ui_move")
        elif key == pygame.K_F2:
            self.settings["keybinds"] = dict(DEFAULT_KEYBINDS)
            self.binding_notice = "全部键位已恢复默认"
            self.save_settings()
            self.sound("ui_ok")

    def _pick_bg_image(self) -> None:
        """弹出系统文件对话框选择背景图（无头环境跳过）"""
        if os.environ.get("SDL_VIDEODRIVER") == "dummy":
            self.sound("gameover")
            return
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askopenfilename(
                title="选择背景图片",
                filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
                           ("所有文件", "*.*")])
            root.destroy()
        except Exception:
            path = ""
        if path and self.renderer.load_custom_bg(path):
            self.settings["custom_bg"] = path
            self.settings["bg_theme"] = "custom"
            self.save_settings()
            self.sound("ui_ok")
        else:
            self.sound("gameover")

    def _try_rotate(self, d: int) -> None:
        if self.board and self.board.piece and self.board.try_rotate(d):
            self.sound("rotate")
            if self.board.piece.grounded:
                self.board.reset_lock()

    def _hard_drop(self) -> None:
        if not self.board or not self.board.piece:
            return
        d = self.board.hard_drop()
        self.shake = max(self.shake, 6 + min(d, 12) * 0.4)
        self.sound("harddrop")
        self._lock_current()

    def _hold(self) -> None:
        if self.board and self.board.do_hold(self.bag):
            self.sound("hold")

    def _move_held(self, key: int) -> None:
        dx = -1 if key == self._key("move_left") else 1
        if self.board and self.board.try_move(dx, 0):
            self.sound("move")
            if self.board.piece and self.board.piece.grounded:
                self.board.reset_lock()

    def _lock_current(self) -> None:
        if not self.board:
            return
        ev = self.board.lock()
        self._after_lock(ev)
        self._spawn_next()

    def _spawn_next(self) -> None:
        if not self.board:
            return
        if not self.board.spawn():
            self._game_over(win=False)
            return
        if self.board.goal_met():
            self._game_over(win=True)

    # ------------------------------------------------------------ 结算
    def _after_lock(self, ev) -> None:
        if ev is None or self.board is None:
            return
        b = self.board
        n = len(ev.rows)
        color = PIECE_COLORS.get("T", ACCENT)
        if ev.rows:
            color = PIECE_COLORS.get(b.piece.name if b.piece else "T", ACCENT)
            for r in ev.rows:
                self.flash_rows.append((r, 0.20))
                cells = [(c, r) for c in range(COLS)]
                self.particles += make_particles_for_clear(self.renderer, cells, color, self.rng,
                                                           burst=10 if n == 4 else 6)
            cx, cy = self.renderer.to_screen(5, ev.rows[0] + 0.5)
            self.rings.append({"x": cx, "y": cy, "r": 10, "t": 0.0, "dur": 0.4, "color": color})
            self.shake = max(self.shake, 4 + n * 2.5)
            self.sound(["line1", "line2", "line3", "tetris"][min(n, 4) - 1])
            if n == 4:
                self.popups.append(self._popup("TETRIS! +%d" % ev.score, (7, ev.rows[0] + 0.5), GOOD))
        if ev.tspin:
            self.sound("tspin")
            label = "T-SPIN MINI" if ev.tspin == "mini" else "T-SPIN"
            row = ev.rows[0] if ev.rows else ev.piece_y + 1
            self.popups.append(self._popup(label, (5.5, row + 0.5), ACCENT2))
        if ev.perfect:
            self.sound("pc")
            self.popups.append(self._popup("PERFECT CLEAR! +3500", (5, 3), GOOD))
        if ev.combo >= 2:
            self.combo_banner = 1.0
            self.sound("combo")
        if ev.score and n != 4:
            row = ev.rows[0] if ev.rows else 4
            self.popups.append(self._popup("+%d" % ev.score, (7, row + 0.5), ACCENT))

    def _popup(self, text: str, cell_pos: tuple[float, float], color) -> dict:
        x, y = self.renderer.to_screen(cell_pos[0], cell_pos[1])
        return {"text": text, "color": color, "x": x, "y": y, "t": 0.0, "dur": 0.9}

    def _game_over(self, win: bool) -> None:
        self.win = win
        b = self.board
        is_rec = self._is_record()
        if win:
            self.sound("record" if is_rec else "go")
        else:
            self.sound("gameover")
        if is_rec:
            self.new_record = True
            cfg = MODE_CFG.get(self.mode, {})
            if cfg.get("record") == "score":
                cur = self.records[self.mode] or 0
                self.records[self.mode] = max(cur, b.score)
            else:  # time / survive
                self.records[self.mode] = self.elapsed
            self.save_records()
        self.state = "gameover"

    def _is_record(self) -> bool:
        b = self.board
        cfg = MODE_CFG.get(self.mode, {})
        kind = cfg.get("record", "time")
        if kind == "score":
            if not self.win:
                return False
            old = self.records[self.mode] or 0
            return b.score > old
        if kind == "survive":
            old = self.records[self.mode]
            return old is None or self.elapsed > old
        if not self.win:
            return False
        old = self.records[self.mode]
        return old is None or self.elapsed < old

    # ------------------------------------------------------------ 更新
    def update(self, dt: float) -> None:
        self.bg_time += dt
        # 特效更新
        update_particles(self.particles, dt)
        for r in self.rings:
            r["t"] += dt
        self.rings[:] = [r for r in self.rings if r["t"] < r["dur"]]
        for p in self.popups:
            p["t"] += dt
        self.popups[:] = [p for p in self.popups if p["t"] < p["dur"]]
        self.flash_rows[:] = [(r, t - dt) for r, t in self.flash_rows if t - dt > 0]
        self.shake = max(0.0, self.shake - dt * 26.0)
        self.combo_banner = max(0.0, self.combo_banner - dt * 0.6)
        for d in self.dust:
            d["x"] -= d["vx"] * dt
            d["y"] -= d["vy"] * dt
            if d["x"] < -20 or d["y"] < -20:
                d["x"] = WIN_W + 20
                d["y"] = random.uniform(80, WIN_H - 80)
                d["vx"] = random.uniform(4, 16)
                d["vy"] = random.uniform(2, 10)

        if self.state == "countdown":
            prev = self.countdown
            self.countdown -= dt
            if int(math.ceil(prev)) != int(math.ceil(self.countdown)) and self.countdown > 0:
                self.sound("countdown")
            if self.countdown <= 0.0:
                self.state = "playing"
                self.sound("go")
            return

        if self.state != "playing":
            return
        if not self.board:
            return

        b = self.board
        # 移动输入（DAS / ARR）
        left = self._held("move_left")
        right = self._held("move_right")
        if left != right:
            self.das_acc += dt
            if self.das_acc >= self.settings["das"]:
                self.arr_acc += dt
                step = self.settings["arr"] or 0.001
                while self.arr_acc >= step:
                    dx = -1 if left else 1
                    if not b.try_move(dx, 0):
                        break
                    if b.piece and b.piece.grounded:
                        b.reset_lock()
                    self.arr_acc -= step
        # 软降
        if self._held("soft_drop"):
            self.soft_acc += dt
            while self.soft_acc >= SOFT_DROP_SEC:
                if not b.soft_drop_step():
                    break
                self.soft_acc -= SOFT_DROP_SEC
        else:
            self.soft_acc = 0.0

        # 重力与锁定
        b.update(dt)
        if b.piece is None and not b.game_over:
            ev = b.last_event
            b.last_event = None
            self._after_lock(ev)
            self._spawn_next()

        self.elapsed += dt
        self.pps = b.pieces_placed / self.elapsed if self.elapsed > 0 else 0.0

        # 限时模式：时间到 → 通关
        cfg = MODE_CFG.get(self.mode, {})
        if cfg.get("goal") == "time" and self.elapsed >= cfg["target"]:
            self._game_over(win=True)
            return

        # 栈高告警
        if b.danger_level() > 0.72:
            self.danger_warn_t -= dt
            if self.danger_warn_t <= 0:
                self.danger_warn_t = 1.4
                self.sound("warning")

        if b.game_over:
            self._game_over(win=False)

    # ------------------------------------------------------------ 菜单
    def _make_menu_buttons(self) -> list[ui.Button]:
        btns: list[ui.Button] = []
        for i, m in enumerate(MODES):
            cfg = MODE_CFG[m]
            best = self.records[m]
            if cfg["record"] == "score":
                best_txt = f"最高分 {best}" if best else "暂无纪录"
            else:
                best_txt = f"最佳 {ui.format_time(best)}" if best else "暂无纪录"
            x = 220 + (i % 2) * 430
            y = 218 + (i // 2) * 76
            btns.append(ui.Button(pygame.Rect(x, y, 410, 66), MODE_NAME[m], f"start:{m}",
                                  sub=f"{MODE_DESC[m]}   ·   {best_txt}"))
        btns.append(ui.Button(pygame.Rect(650, 446, 198, 66), "设置", "settings"))
        btns.append(ui.Button(pygame.Rect(862, 446, 198, 66), "退出游戏", "quit"))
        return btns

    def _selected_index(self) -> int:
        for i, b in enumerate(self.buttons):
            if b.hover:
                return i
        return 0

    def _selected_action(self) -> str:
        if not self.buttons:
            return ""
        return self.buttons[self._selected_index()].action

    def _move_selection(self, d: int) -> None:
        if not self.buttons:
            return
        idx = self._selected_index()
        self._set_hover((idx + d) % len(self.buttons))
        self.sound("ui_move")

    def _set_hover(self, i: int) -> None:
        for j, b in enumerate(self.buttons):
            b.hover = (j == i)

    def _activate_selected(self) -> None:
        act = self._selected_action()
        if act:
            self._activate(act)

    def _activate(self, act: str) -> None:
        if act.startswith("start:"):
            self.sound("ui_ok")
            self.new_game(act[6:])
        elif act == "settings":
            self.settings_return_state = "paused" if self.state == "paused" else "menu"
            self.state = "settings"
            self.sound("ui_ok")
        elif act == "quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif act == "resume":
            self.state = "playing"
        elif act == "restart":
            self.restart()
        elif act == "back_menu":
            self.state = "menu"
        elif act == "back_settings":
            self.sound("ui_ok")
            self._back_from_settings()

    def _back_from_settings(self) -> None:
        self.state = self.settings_return_state

    def handle_click(self, pos: tuple[int, int]) -> None:
        for b in self.buttons:
            if b.hit(pos):
                self._activate(b.action)
                return
        # 设置项点击
        if self.state == "settings":
            for i, (kn, _, _, _, _) in enumerate(self.settings_items):
                col, row = i // 6, i % 6
                rect = pygame.Rect(286 + col * 360, 174 + row * 58, 340, 46)
                if rect.collidepoint(pos):
                    self.settings_idx = i
                    if kn == "bg_upload":
                        self._pick_bg_image()
                    elif kn == "controls":
                        self.state = "keybinds"
                        self.keybind_idx = 0
                        self.binding_capture = None
                        self.binding_notice = "点击动作或按 Enter，然后按下新键"
                        self.keys_held.clear()
                    return
        elif self.state == "keybinds":
            actions = list(KEYBIND_LABELS)
            for i in range(len(actions)):
                col, row = i // 7, i % 7
                rect = pygame.Rect(310 + col * 340, 188 + row * 52, 320, 42)
                if rect.collidepoint(pos):
                    self.keybind_idx = i
                    self.binding_capture = actions[i]
                    self.binding_notice = "等待按键输入…"
                    self.sound("ui_ok")
                    return

    def handle_hover(self, pos: tuple[int, int]) -> None:
        self.mouse_pos = pos
        for b in self.buttons:
            b.hover = b.hit(pos)

    # ------------------------------------------------------------ 视角控制（360° 转动）
    def rotate_view(self, dyaw: float, dpitch: float) -> None:
        self.renderer.set_view(self.renderer.yaw + dyaw, self.renderer.pitch + dpitch)

    def drag_start(self, pos: tuple[int, int]) -> None:
        if self.state == "playing" and SCENE_RECT.collidepoint(pos):
            self.dragging = True
            self.last_mouse = pos
            self.drag_filtered = (0.0, 0.0)

    def drag_move(self, pos: tuple[int, int]) -> None:
        if not self.dragging:
            return
        dx = pos[0] - self.last_mouse[0]
        dy = pos[1] - self.last_mouse[1]
        self.last_mouse = pos
        # Suppress one-pixel hand jitter and soften sudden pointer jumps.  Upward
        # dragging tilts toward top-down, matching a conventional orbit camera.
        if abs(dx) < 2:
            dx = 0
        if abs(dy) < 2:
            dy = 0
        fx = self.drag_filtered[0] * 0.58 + _clamp(dx, -30, 30) * 0.42
        fy = self.drag_filtered[1] * 0.58 + _clamp(dy, -30, 30) * 0.42
        self.drag_filtered = (fx, fy)
        sensitivity = self.settings.get("view_sensitivity", 0.25)
        self.rotate_view(fx * 0.0036 * sensitivity, -fy * 0.0030 * sensitivity)

    def drag_end(self) -> None:
        self.dragging = False
        self.drag_filtered = (0.0, 0.0)

    # ------------------------------------------------------------ 绘制
    def _init_dust(self) -> None:
        for _ in range(26):
            self.dust.append({
                "x": random.uniform(0, WIN_W), "y": random.uniform(0, WIN_H),
                "vx": random.uniform(4, 16), "vy": random.uniform(2, 10),
                "size": random.uniform(1, 3), "a": random.uniform(20, 70),
            })

    def _build_stage_ambient(self) -> pygame.Surface:
        """Cached soft light volume behind the board (no per-frame blur cost)."""
        layer = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        center = (672, 372)
        for i in range(18, 0, -1):
            k = i / 18.0
            rect = pygame.Rect(0, 0, int(900 * k), int(590 * k))
            rect.center = center
            alpha = max(1, int(5 * (1.0 - k) + 1))
            pygame.draw.ellipse(layer, (34, 70, 180, alpha), rect)
        horizon = pygame.Surface((WIN_W, 180), pygame.SRCALPHA)
        for y in range(90):
            alpha = int(14 * (1.0 - y / 90.0) ** 2)
            pygame.draw.line(horizon, (84, 48, 180, alpha),
                             (0, 90 - y), (WIN_W, 90 - y))
            pygame.draw.line(horizon, (28, 115, 190, alpha),
                             (0, 90 + y), (WIN_W, 90 + y))
        layer.blit(horizon, (0, 285))
        return layer

    def draw_background(self) -> None:
        s = self.screen
        theme = self.settings["bg_theme"]
        if theme != "default":
            draw_bg_theme(s, theme, self.bg_time, self.renderer.custom_bg,
                          random.Random(7))
        else:
            # 垂直渐变必须整块覆盖，否则上一帧内容会残影（逐行 1px 线会留黑缝）
            for y in range(0, WIN_H, 4):
                t = y / WIN_H
                c = (int(14 + (8 - 14) * t), int(16 + (9 - 16) * t), int(34 + (22 - 34) * t))
                pygame.draw.rect(s, c, (0, y, WIN_W, 4))
            s.blit(self.stage_ambient, (0, 0))
            # Slow, low-contrast light ribbons keep the stage alive without
            # competing with the matrix. Their motion is tied to game time.
            ribbons = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            for index, (color, base, amplitude, speed) in enumerate((
                    ((28, 168, 255, 17), 292, 25, 0.34),
                    ((167, 72, 255, 13), 344, 36, -0.23))):
                points = []
                for x in range(-32, WIN_W + 64, 32):
                    y = base + amplitude * math.sin(x * 0.008 + self.bg_time * speed + index)
                    points.append((x, y))
                pygame.draw.aalines(ribbons, color, False, points)
            s.blit(ribbons, (0, 0))
        for d in self.dust:
            tmp = pygame.Surface((d["size"] * 2 + 2, d["size"] * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (180, 200, 255, int(d["a"])),
                               (int(d["size"]) + 1, int(d["size"]) + 1), int(d["size"]))
            s.blit(tmp, (int(d["x"]), int(d["y"])))

    def draw(self) -> None:
        s = self.screen
        self.draw_background()

        if self.state == "menu":
            self._draw_menu()
            return

        # 3D 场景绘制到子表面以支持震屏
        scene = pygame.Surface(SCENE_RECT.size, pygame.SRCALPHA)
        self.renderer.set_surface_offset(SCENE_RECT.x, SCENE_RECT.y)
        b = self.board
        if b:
            self.renderer.draw_stage_light(scene, self.bg_time, b.danger_level())
            self.renderer.draw_floor(scene)
            self.renderer.draw_platform(scene)
            for (c, r), name in sorted(b.grid.items(),
                                       key=lambda kv: self.renderer.sort_key(*kv[0])):
                self.renderer.draw_cube(scene, c, r, PIECE_COLORS[name])
            # 消行闪光带
            for r, t in self.flash_rows:
                x0, y0 = self.renderer.to_screen(0, r)
                x1, y1 = self.renderer.to_screen(COLS, r)
                x2, y2 = self.renderer.to_screen(COLS, r + 1)
                x3, y3 = self.renderer.to_screen(0, r + 1)
                a = int(200 * (t / 0.2))
                tmp = pygame.Surface(scene.get_size(), pygame.SRCALPHA)
                pygame.draw.polygon(tmp, (255, 255, 255, a), [(x0, y0), (x1, y1), (x2, y2), (x3, y3)])
                scene.blit(tmp, (0, 0))
            # 幽灵 + 活动方块
            p = b.piece
            if p:
                self.renderer.piece_shadow(scene, p.x, p.y + b.drop_distance(), 4, 2)
            if p and self.settings["ghost"]:
                gy = p.y + b.drop_distance()
                ghost_cells = [(p.x + cx, gy + cy) for cx, cy in ALL_CELLS[p.name][p.rot]]
                self.renderer.draw_ghost(scene, ghost_cells, PIECE_COLORS[p.name])
            if p:
                fall = b.drop_frac if b.gravity_per_frame(0.016) < 1.0 else 0.0
                cells = sorted(p.cells(),
                               key=lambda cc: self.renderer.sort_key(cc[0], cc[1] + fall))
                for c, r in cells:
                    self.renderer.draw_cube(scene, c, r + fall, PIECE_COLORS[p.name], glow=True)
            # 粒子与波纹
            self.renderer.draw_particles(scene, self.particles)
            for r in self.rings:
                k = r["t"] / r["dur"]
                rad = r["r"] + 90 * k
                self.renderer.draw_ring(scene, r["x"], r["y"], rad, int(200 * (1 - k)), r["color"])
            # 分数弹窗
            for p in self.popups:
                a = 255 if p["t"] < p["dur"] - 0.3 else int(255 * (p["dur"] - p["t"]) / 0.3)
                ui.text(scene, self.fonts, p["text"], 20,
                        (p["x"], p["y"] - 30 * (p["t"] / p["dur"])),
                        color=p["color"], anchor="center", shadow=True, alpha=a)
        self.renderer.set_surface_offset(0, 0)

        shx = int(self.shake * random.uniform(-1, 1))
        shy = int(self.shake * random.uniform(-1, 1))
        s.blit(scene, (SCENE_RECT.x + shx, SCENE_RECT.y + shy))

        if b and b.danger_level() > 0.6:
            ui.draw_vignette(s, int(60 * (b.danger_level() - 0.6) / 0.4))

        self._draw_hud()

        if self.combo_banner > 0 and b:
            a = int(255 * min(1.0, self.combo_banner * 2))
            ui.text(s, self.fonts, f"COMBO ×{b.combo}", 30, (845, 66),
                    color=ACCENT2, anchor="center", alpha=a)

        if self.state == "countdown":
            self._draw_countdown()
        elif self.state == "paused":
            self._draw_paused()
        elif self.state == "settings":
            self._draw_settings()
        elif self.state == "keybinds":
            self._draw_keybinds()
        elif self.state == "gameover":
            self._draw_gameover()

    # ------------------------------------------------------------ 主菜单
    def _draw_menu(self) -> None:
        s, f = self.screen, self.fonts
        # 标题光晕
        title_glow = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        for i in range(30, 0, -1):
            a = int(7 * (1 - i / 30) ** 2)
            pygame.draw.circle(title_glow, (45, 90, 255, a), (640, 106), i * 5)
        s.blit(title_glow, (0, 0))
        ui.text(s, f, "TETRIS 3D RUSH", 62, (640, 120), color=ACCENT, anchor="center", bold=True)
        ui.text(s, f, "伪 3D · 竞速俄罗斯方块", 22, (640, 172), color=TEXT_DIM, anchor="center")
        ui.panel(s, pygame.Rect(196, 198, 888, 338), fill=(10, 14, 34, 115),
                 border=(90, 120, 220, 45), radius=20)
        self.buttons = self._make_menu_buttons()
        for b in self.buttons:
            b.draw(s, f)
        ui.text(s, f, "↑↓ 选择   Enter 开始   F11 / Alt+Enter 全屏", 15,
                (640, WIN_H - 60), color=TEXT_DIM, anchor="center", shadow=False)
        ui.text(s, f, "竞速规则：指南计分 · 7-bag · SRS 踢墙 · T-spin 判定 · 硬降 ×2/格",
                15, (640, WIN_H - 36), color=TEXT_DIM, anchor="center", shadow=False)

    # ------------------------------------------------------------ HUD
    def _draw_hud(self) -> None:
        s, f = self.screen, self.fonts
        b = self.board
        if b is None:
            return
        cfg = MODE_CFG.get(self.mode, {})
        left = pygame.Rect(16, 20, 252, 402)
        ui.panel(s, left, fill=(10, 15, 34, 180), border=(98, 137, 218, 62), radius=16)
        pygame.draw.line(s, ACCENT, (32, 21), (104, 21), 2)
        ui.text(s, f, "LIVE SESSION", 12, (32, 38), color=ACCENT, bold=True)
        ui.text(s, f, MODE_NAME[self.mode], 22, (32, 62), color=TEXT_MAIN, bold=True)
        ui.text(s, f, ui.format_time(self.elapsed), 40, (32, 98), color=TEXT_MAIN, bold=True)
        ui.text(s, f, "SURVIVAL" if self.mode == "endless" else "ELAPSED", 11,
                (34, 142), color=TEXT_DIM, shadow=False)
        if cfg.get("goal") == "time":
            rem = max(0.0, cfg["target"] - self.elapsed)
            ui.text(s, f, ui.format_time(rem), 23, (244, 116), color=ACCENT,
                    anchor="midright", bold=True)
            ui.text(s, f, "剩余", 12, (244, 143), color=GOOD,
                    anchor="midright", shadow=False)

        goal = cfg.get("goal")
        if goal == "lines":
            ratio = b.lines / max(1, cfg["target"])
            progress_text = f"目标进度  {b.lines} / {cfg['target']} 行"
        elif goal == "score":
            ratio = b.score / max(1, cfg["target"])
            progress_text = f"目标进度  {b.score} / {cfg['target']} 分"
        elif goal == "time":
            ratio = self.elapsed / max(1, cfg["target"])
            progress_text = f"限时进度  {min(self.elapsed, cfg['target']):.1f} / {cfg['target']} 秒"
        else:
            ratio = min(1.0, b.danger_level())
            progress_text = "堆叠压力"
        ui.text(s, f, progress_text, 13, (32, 171), color=TEXT_DIM, shadow=False)
        bar = pygame.Rect(32, 194, 212, 4)
        pygame.draw.rect(s, (37, 48, 80), bar, border_radius=2)
        fill = bar.copy()
        fill.width = max(3, int(bar.width * _clamp(ratio, 0.0, 1.0)))
        pygame.draw.rect(s, DANGER if ratio > 0.78 else ACCENT, fill, border_radius=2)

        rows = [
            ("分数", str(b.score)),
            ("行数", str(b.lines)),
            ("等级", str(b.level)),
            ("已放块", str(b.pieces_placed)),
            ("PPS", f"{self.pps:.2f}"),
            ("连击", f"×{b.combo}" if b.combo >= 2 else "—"),
        ]
        for i, (label, value) in enumerate(rows):
            col, row = i % 2, i // 2
            x = 32 + col * 108
            y = 224 + row * 54
            ui.text(s, f, label, 12, (x, y), color=TEXT_DIM, shadow=False)
            ui.text(s, f, value, 22, (x, y + 18), color=TEXT_MAIN, bold=True)

        best = self.records[self.mode]
        if cfg.get("record") == "score":
            best_value = f"{best} 分" if best else "—"
        else:
            best_value = ui.format_time(best) if best else "—"
        record_card = pygame.Rect(16, 440, 252, 116)
        ui.panel(s, record_card, fill=(9, 14, 31, 165),
                 border=(104, 122, 196, 46), radius=14)
        ui.text(s, f, "PERSONAL BEST", 11, (32, 459), color=ACCENT2, bold=True)
        ui.text(s, f, best_value, 27, (32, 482), color=TEXT_MAIN, bold=True)
        ui.text(s, f, "当前模式历史最佳", 12, (32, 523), color=TEXT_DIM, shadow=False)

        # 右侧：暂存 + 下一块
        ui.panel(s, pygame.Rect(1044, 20, 220, 590), fill=(10, 15, 34, 180),
                 border=(98, 137, 218, 62), radius=16)
        pygame.draw.line(s, ACCENT2, (1176, 21), (1248, 21), 2)
        ui.text(s, f, "PIECE FLOW", 12, (1154, 42), color=ACCENT2,
                anchor="center", bold=True)
        ui.draw_preview(s, f, "暂存  HOLD", b.hold, (1154, 116), cell=13,
                        skin=self.renderer.current_skin, box_size=(184, 104))
        ui.text(s, f, "接下来  NEXT", 12, (1154, 185), color=TEXT_DIM,
                anchor="center", shadow=False)
        for i, name in enumerate(b.next_queue[:5]):
            ui.draw_preview(s, f, "", name, (1154, 224 + i * 70), cell=11,
                            skin=self.renderer.current_skin, box_size=(184, 56))

        def kn(action):
            return pygame.key.name(self._key(action)).upper()
        ui.text(s, f, f"{kn('move_left')}/{kn('move_right')} 移动   {kn('soft_drop')} 软降   "
                f"{kn('rotate_cw')} 旋转   {kn('hard_drop')} 硬降   {kn('hold')} 暂存",
                14, (WIN_W // 2, WIN_H - 46), color=TEXT_DIM, anchor="center", shadow=False)
        ui.text(s, f, f"{kn('pause')} 暂停   {kn('restart')} 重开   {kn('view_front')} 正面视角   "
                "F11 全屏   场地内按住左键拖拽视角",
                14, (WIN_W // 2, WIN_H - 25), color=TEXT_DIM, anchor="center", shadow=False)

    def _draw_countdown(self) -> None:
        n = int(math.ceil(self.countdown))
        txt = "GO!" if n <= 0 else str(n)
        color = GOOD if n <= 0 else TEXT_MAIN
        frac = self.countdown - math.floor(self.countdown) if self.countdown > 0 else 1.0
        a = int(255 * frac) if self.countdown > 0 else 255
        tmp = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        ui.text(tmp, self.fonts, txt, 120, (640, 300), color=color, anchor="center", alpha=a)
        self.screen.blit(tmp, (0, 0))

    def _draw_paused(self) -> None:
        self._overlay("已暂停", [
            ui.Button(pygame.Rect(490, 300, 300, 54), "继续游戏", "resume"),
            ui.Button(pygame.Rect(490, 368, 300, 54), "重新开始", "restart"),
            ui.Button(pygame.Rect(490, 436, 300, 54), "设置", "settings"),
            ui.Button(pygame.Rect(490, 504, 300, 54), "返回主菜单", "back_menu"),
        ])

    def _draw_gameover(self) -> None:
        b = self.board
        cfg = MODE_CFG.get(self.mode, {})
        if self.win:
            if self.mode == "marathon":
                title = "马拉松通关！"
                sub = f"最终分数 {b.score}"
            elif cfg.get("goal") == "time":
                title = "时间到！"
                sub = f"得分 {b.score} · 消行 {b.lines}"
            else:
                title = "完成！"
                sub = f"用时 {ui.format_time(self.elapsed)}"
        else:
            if self.mode == "endless":
                title = "力竭倒下"
                sub = f"生存 {ui.format_time(self.elapsed)} · 分数 {b.score}"
            else:
                title = "游戏结束"
                sub = f"分数 {b.score} · 消行 {b.lines}"
        if self.new_record:
            sub += "   ★ 新纪录！"
        self._overlay(title, [
            ui.Button(pygame.Rect(490, 430, 300, 54), "再来一局", "restart", accent=True),
            ui.Button(pygame.Rect(490, 500, 300, 54), "返回主菜单", "back_menu"),
        ], sub=sub)

    def _overlay(self, title: str, buttons: list[ui.Button], sub: str | None = None) -> None:
        s, f = self.screen, self.fonts
        tmp = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(tmp, (5, 6, 16, 170), (0, 0, WIN_W, WIN_H))
        s.blit(tmp, (0, 0))
        ui.panel(s, pygame.Rect(430, 210, 420, 400))
        ui.text(s, f, title, 40, (640, 240), color=ACCENT, anchor="center", bold=True)
        if sub:
            ui.text(s, f, sub, 20, (640, 300), color=TEXT_MAIN, anchor="center")
        self.buttons = buttons
        for b in buttons:
            b.draw(s, f)

    # ------------------------------------------------------------ 设置界面
    def _draw_settings(self) -> None:
        s, f = self.screen, self.fonts
        tmp = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(tmp, (5, 6, 16, 180), (0, 0, WIN_W, WIN_H))
        s.blit(tmp, (0, 0))
        ui.panel(s, pygame.Rect(246, 70, 788, 644))
        ui.text(s, f, "设置", 36, (640, 108), color=ACCENT, anchor="center", bold=True)
        ui.text(s, f, "操作手感", 14, (306, 150), color=TEXT_DIM, shadow=False)
        ui.text(s, f, "画面与个性化", 14, (666, 150), color=TEXT_DIM, shadow=False)
        st = self.settings
        for i, (key, label, _, _, _) in enumerate(self.settings_items):
            if key == "das":
                val = f"{st['das'] * 1000:.0f} ms"
            elif key == "arr":
                val = f"{st['arr'] * 1000:.0f} ms"
            elif key == "gravity_speed":
                val = GRAVITY_NAMES.get(st["gravity_speed"], "极慢")
            elif key == "ghost":
                val = "开" if st["ghost"] else "关"
            elif key == "sound":
                val = "开" if st["sound"] else "关"
            elif key == "skin":
                val = SKINS.get(st["skin"], SKINS["neon"])["name"]
            elif key == "bg_theme":
                t = st["bg_theme"]
                val = BG_THEME_NAME.get(t, t)
                if t == "custom" and not st.get("custom_bg"):
                    val += "（未选择）"
            elif key == "bg_upload":
                val = "选择图片…" if not st.get("custom_bg") else os.path.basename(st["custom_bg"])
                if len(val) > 16:
                    val = val[:13] + "…"
            elif key == "view_sensitivity":
                val = f"{int(st['view_sensitivity'] * 100)}%"
            elif key == "fullscreen":
                val = "开" if st["fullscreen"] else "关"
            elif key == "controls":
                val = "进入设置"
            else:
                val = f"{int(st['volume'] * 100)}%"
            sel = i == self.settings_idx
            col, row = i // 6, i % 6
            rect = pygame.Rect(286 + col * 360, 174 + row * 58, 340, 46)
            fill = (30, 40, 82, 220) if sel else (13, 18, 42, 180)
            border = ACCENT if sel else (95, 120, 210, 55)
            ui.panel(s, rect, fill=fill, border=border, radius=9)
            ui.text(s, f, label, 16, (rect.x + 14, rect.centery),
                    color=ACCENT if sel else TEXT_MAIN, anchor="midleft", shadow=False)
            vcol = ACCENT if sel else ACCENT2
            ui.text(s, f, val, 16, (rect.right - 14, rect.centery),
                    color=vcol, anchor="midright", bold=sel, shadow=False)
        ui.text(s, f, "← → 调整/切换    ↑ ↓ 选择    Enter 进入    Esc 返回", 15, (640, 548),
                color=TEXT_DIM, anchor="center", shadow=False)
        ui.text(s, f, "F11 / Alt+Enter 全屏 · F 正面视角 · 全屏时 Esc 返回窗口", 14, (640, 578),
                color=TEXT_DIM, anchor="center", shadow=False)
        self.buttons = [ui.Button(pygame.Rect(540, 626, 200, 48), "返回", "back_settings")]
        self.buttons[0].draw(s, f)

    def _draw_keybinds(self) -> None:
        s, f = self.screen, self.fonts
        tmp = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(tmp, (5, 6, 16, 205), (0, 0, WIN_W, WIN_H))
        s.blit(tmp, (0, 0))
        ui.panel(s, pygame.Rect(270, 82, 740, 632))
        ui.text(s, f, "自定义键位", 34, (640, 116), color=ACCENT,
                anchor="center", bold=True)
        notice = self.binding_notice or "点击动作或按 Enter，然后按下新键"
        ui.text(s, f, notice, 14, (640, 156),
                color=GOOD if self.binding_notice.startswith("已") else TEXT_DIM,
                anchor="center", shadow=False)
        actions = list(KEYBIND_LABELS)
        for i, action in enumerate(actions):
            col, row = i // 7, i % 7
            rect = pygame.Rect(310 + col * 340, 188 + row * 52, 320, 42)
            selected = i == self.keybind_idx
            fill = (31, 40, 82, 220) if selected else (15, 20, 45, 175)
            border = ACCENT if selected else (100, 125, 210, 65)
            ui.panel(s, rect, fill=fill, border=border, radius=9)
            ui.text(s, f, KEYBIND_LABELS[action], 16, (rect.x + 15, rect.centery),
                    color=TEXT_MAIN, anchor="midleft", shadow=False)
            key_name = pygame.key.name(self._key(action)).upper()
            ui.text(s, f, key_name, 16, (rect.right - 15, rect.centery),
                    color=ACCENT if selected else ACCENT2, anchor="midright", bold=selected)
        if self.binding_capture is not None:
            ui.panel(s, pygame.Rect(380, 326, 520, 148), fill=(12, 18, 46, 245),
                     border=ACCENT, radius=16)
            ui.text(s, f, f"正在设置：{KEYBIND_LABELS[self.binding_capture]}", 23,
                    (640, 364), color=TEXT_MAIN, anchor="center", bold=True)
            ui.text(s, f, "请按下新按键", 30, (640, 410), color=ACCENT,
                    anchor="center", bold=True)
            ui.text(s, f, "Esc 取消", 14, (640, 450), color=TEXT_DIM,
                    anchor="center", shadow=False)
        ui.text(s, f, "↑ ↓ 选择   Enter 修改   Backspace 恢复当前默认   F2 全部恢复   Esc 返回",
                14, (640, 681), color=TEXT_DIM, anchor="center", shadow=False)
        self.buttons = []
