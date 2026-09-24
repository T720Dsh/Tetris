"""游戏主逻辑：状态机、输入（DAS/ARR）、更新、绘制"""
from __future__ import annotations
import json
import math
import os
import random

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

SCENE_RECT = pygame.Rect(300, 110, 760, 520)
MOVE_KEYS = (pygame.K_LEFT, pygame.K_RIGHT)

_SETTINGS_DEFAULTS = {
    "das": DAS, "arr": ARR, "ghost": True, "sound": True, "volume": 0.7,
    "skin": "neon", "bg_theme": "default", "custom_bg": "",
}


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Game:
    def __init__(self, screen: pygame.Surface, records_path: str):
        self.screen = screen
        self.records_path = records_path
        self.fonts = ui.Fonts()
        self.renderer = Renderer()
        self.records = self._load_records()
        self.settings = self._load_settings()
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

        # 输入状态
        self.keys_held: set[int] = set()
        self.das_acc = 0.0
        self.arr_acc = 0.0
        self.soft_acc = 0.0
        self.mouse_pos = (0, 0)
        self.dragging = False
        self.last_mouse = (0, 0)
        self.buttons: list[ui.Button] = []
        self.win = False
        self.new_record = False

        # 设置界面状态
        self.settings_idx = 0
        self.settings_items = [
            ("das", "移动延迟 DAS", 0.040, 0.300, 0.005),
            ("arr", "重复间隔 ARR", 0.000, 0.120, 0.005),
            ("ghost", "幽灵投影", None, None, None),
            ("sound", "音效", None, None, None),
            ("volume", "音量", 0.0, 1.0, 0.05),
            ("skin", "方块材质", None, None, tuple(SKIN_ORDER)),
            ("bg_theme", "背景主题", None, None, tuple(BG_THEMES)),
            ("bg_upload", "上传背景图…", None, None, None),
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
        try:
            with open(self._settings_path(), "r", encoding="utf-8") as f:
                st.update(json.load(f))
        except Exception:
            pass
        return st

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
        shift = bool(mods & pygame.KMOD_SHIFT)

        if self.state == "menu":
            self._menu_key(key)
            return
        if self.state == "settings":
            self._settings_key(key)
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
            if key in (pygame.K_ESCAPE, pygame.K_p, pygame.K_RETURN):
                self.state = "playing"
            elif key == pygame.K_r:
                self.restart()
            return

        # playing
        b = self.board
        if key in (pygame.K_ESCAPE, pygame.K_p):
            self.state = "paused"
        elif key == pygame.K_r:
            self.restart()
        elif key in (pygame.K_UP, pygame.K_x, pygame.K_w):
            self._try_rotate(1)
        elif key in (pygame.K_z, pygame.K_LCTRL):
            self._try_rotate(-1)
        elif key == pygame.K_a:
            self._try_rotate(2)
        elif key == pygame.K_q:
            self.rotate_view(-0.10, 0.0)
        elif key == pygame.K_e:
            self.rotate_view(0.10, 0.0)
        elif key == pygame.K_v:
            self.renderer.set_view(0.0, 0.0)
        elif key == pygame.K_SPACE:
            self._hard_drop()
        elif key == pygame.K_c or shift:
            self._hold()
        elif key in MOVE_KEYS:
            self.das_acc = 0.0
            self.arr_acc = 0.0
            self._move_held(key)

    def on_key_up(self, key: int) -> None:
        self.keys_held.discard(key)
        if key in MOVE_KEYS:
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
        if key in (pygame.K_ESCAPE, pygame.K_RETURN):
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
            if step is None:
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
            self.save_settings()
            self.sound("ui_move")

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
        dx = -1 if key == pygame.K_LEFT else 1
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
        left = pygame.K_LEFT in self.keys_held
        right = pygame.K_RIGHT in self.keys_held
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
        if pygame.K_DOWN in self.keys_held or pygame.K_s in self.keys_held:
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
        y = 232
        for m in MODES:
            cfg = MODE_CFG[m]
            best = self.records[m]
            if cfg["record"] == "score":
                best_txt = f"最高分 {best}" if best else "暂无纪录"
            else:
                best_txt = f"最佳 {ui.format_time(best)}" if best else "暂无纪录"
            btns.append(ui.Button(pygame.Rect(420, y, 440, 56), MODE_NAME[m], f"start:{m}",
                                  sub=f"{MODE_DESC[m]}   ·   {best_txt}"))
            y += 62
        btns.append(ui.Button(pygame.Rect(420, y + 4, 214, 48), "设置", "settings"))
        btns.append(ui.Button(pygame.Rect(646, y + 4, 214, 48), "退出游戏", "quit"))
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
        if self.board is not None and self.state != "menu":
            self.state = "paused"
        else:
            self.state = "menu"

    def handle_click(self, pos: tuple[int, int]) -> None:
        for b in self.buttons:
            if b.hit(pos):
                self._activate(b.action)
                return
        # 设置项点击
        if self.state == "settings":
            y = 196
            for i, (kn, _, _, _, _) in enumerate(self.settings_items):
                if pygame.Rect(410, y - 10, 460, 42).collidepoint(pos):
                    self.settings_idx = i
                    if kn == "bg_upload":
                        self._pick_bg_image()
                    return
                y += 46

    def handle_hover(self, pos: tuple[int, int]) -> None:
        self.mouse_pos = pos
        for b in self.buttons:
            b.hover = b.hit(pos)

    # ------------------------------------------------------------ 视角控制（360° 转动）
    def rotate_view(self, dyaw: float, dpitch: float) -> None:
        self.renderer.set_view(self.renderer.yaw + dyaw, self.renderer.pitch + dpitch)

    def drag_start(self, pos: tuple[int, int]) -> None:
        if self.state == "playing":
            self.dragging = True
            self.last_mouse = pos

    def drag_move(self, pos: tuple[int, int]) -> None:
        if not self.dragging:
            return
        dx = pos[0] - self.last_mouse[0]
        dy = pos[1] - self.last_mouse[1]
        self.last_mouse = pos
        self.rotate_view(dx * 0.006, dy * 0.005)

    def drag_end(self) -> None:
        self.dragging = False

    # ------------------------------------------------------------ 绘制
    def _init_dust(self) -> None:
        for _ in range(26):
            self.dust.append({
                "x": random.uniform(0, WIN_W), "y": random.uniform(0, WIN_H),
                "vx": random.uniform(4, 16), "vy": random.uniform(2, 10),
                "size": random.uniform(1, 3), "a": random.uniform(20, 70),
            })

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
            if p and self.settings["ghost"]:
                gy = p.y + b.drop_distance()
                ghost_cells = [(p.x + cx, gy + cy) for cx, cy in ALL_CELLS[p.name][p.rot]]
                self.renderer.draw_ghost(scene, ghost_cells, PIECE_COLORS[p.name])
            if p:
                fall = b.drop_frac if b.gravity_per_frame(0.016) < 1.0 else 0.0
                self.renderer.piece_shadow(scene, p.x, p.y + b.drop_distance(), 4, 2)
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
        elif self.state == "gameover":
            self._draw_gameover()

    # ------------------------------------------------------------ 主菜单
    def _draw_menu(self) -> None:
        s, f = self.screen, self.fonts
        # 标题光晕
        for i in range(30, 0, -1):
            a = int(10 * (1 - i / 30))
            pygame.draw.circle(s, (60, 90, 255, a), (640, 96), i * 5)
        ui.text(s, f, "TETRIS 3D RUSH", 62, (640, 120), color=ACCENT, anchor="center", bold=True)
        ui.text(s, f, "伪 3D · 竞速俄罗斯方块", 22, (640, 172), color=TEXT_DIM, anchor="center")
        self.buttons = self._make_menu_buttons()
        for b in self.buttons:
            b.draw(s, f)
        ui.text(s, f, "↑↓ 选择   Enter 开始   ←→ 在玩法中移动方块", 15,
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
        ui.panel(s, pygame.Rect(16, 16, 300, 620))
        ui.text(s, f, MODE_NAME[self.mode], 24, (30, 32), color=ACCENT)
        ui.text(s, f, ui.format_time(self.elapsed), 44, (30, 72), color=TEXT_MAIN, bold=True)
        ui.text(s, f, "已生存" if self.mode == "endless" else "计时", 15, (30, 124),
                color=TEXT_DIM, shadow=False)
        if cfg.get("goal") == "time":
            rem = max(0.0, cfg["target"] - self.elapsed)
            ui.text(s, f, ui.format_time(rem), 32, (206, 86), color=ACCENT, anchor="midright")
            ui.text(s, f, "剩余", 15, (206, 124), color=GOOD, anchor="midright", shadow=False)

        rows = [
            ("分数", str(b.score)),
            ("行数", f"{b.lines} / {cfg['target']}" if cfg.get("goal") == "lines" else str(b.lines)),
            ("等级", str(b.level)),
            ("已放块", str(b.pieces_placed)),
            ("PPS", f"{self.pps:.2f}"),
            ("连击", f"×{b.combo}" if b.combo >= 2 else "—"),
        ]
        y = 152
        for k, v in rows:
            ui.text(s, f, k, 16, (30, y), color=TEXT_DIM, shadow=False)
            ui.text(s, f, v, 20, (150, y - 4), color=TEXT_MAIN)
            y += 38
        ui.text(s, f, "最佳纪录", 16, (30, y + 4), color=TEXT_DIM, shadow=False)
        y += 34
        for m in MODES:
            cfgm = MODE_CFG[m]
            best = self.records[m]
            if cfgm["record"] == "score":
                v = f"{best} 分" if best else "—"
            else:
                v = ui.format_time(best) if best else "—"
            ui.text(s, f, MODE_NAME[m], 14, (30, y), color=TEXT_DIM, shadow=False)
            ui.text(s, f, v, 14, (196, y), color=TEXT_MAIN, shadow=False)
            y += 24

        # 右侧：暂存 + 下一块
        ui.panel(s, pygame.Rect(1030, 16, 234, 486))
        ui.draw_preview(s, f, "暂存 HOLD", b.hold, (1147, 190), skin=self.renderer.current_skin)
        ui.text(s, f, "NEXT", 16, (1147, 300), color=TEXT_DIM, anchor="center", shadow=False)
        for i, name in enumerate(b.next_queue[:5]):
            ui.draw_preview(s, f, "", name, (1147, 352 + i * 62), cell=13,
                             skin=self.renderer.current_skin)

        ui.text(s, f, "←→ 移动  ↓ 软降  ↑/X 旋转  Z 逆旋  A 180°  C 暂存  空格 硬降",
                14, (WIN_W // 2, WIN_H - 46), color=TEXT_DIM, anchor="center", shadow=False)
        ui.text(s, f, "Esc 暂停  R 重开  Q/E 旋转视角  V 复位视角  按住拖拽可 360° 转动",
                14, (WIN_W // 2, WIN_H - 26), color=TEXT_DIM, anchor="center", shadow=False)

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
        ui.panel(s, pygame.Rect(390, 105, 500, 550))
        ui.text(s, f, "设置", 34, (640, 133), color=ACCENT, anchor="center", bold=True)
        st = self.settings
        y = 196
        for i, (key, label, _, _, _) in enumerate(self.settings_items):
            if key == "das":
                val = f"{st['das'] * 1000:.0f} ms"
            elif key == "arr":
                val = f"{st['arr'] * 1000:.0f} ms"
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
            else:
                val = f"{int(st['volume'] * 100)}%"
            sel = i == self.settings_idx
            ui.text(s, f, label, 18, (430, y), color=ACCENT if sel else TEXT_MAIN, shadow=False)
            vcol = ACCENT if sel else ACCENT2
            ui.text(s, f, ("▸ " if sel else "") + val, 22, (770, y - 2),
                    color=vcol, anchor="midright")
            if sel:
                pygame.draw.rect(s, (ACCENT2 + (60,)), pygame.Rect(418, y - 16, 470, 34), 1, border_radius=8)
            y += 46
        ui.text(s, f, "← → 调整/切换    ↑ ↓ 选择   Esc 返回", 15, (640, 578),
                color=TEXT_DIM, anchor="center", shadow=False)
        ui.text(s, f, "背景图支持 png / jpg，自动裁剪铺满窗口", 14, (640, 600),
                color=TEXT_DIM, anchor="center", shadow=False)
        self.buttons = [ui.Button(pygame.Rect(540, 622, 200, 46), "返回", "back_settings")]
        self.buttons[0].draw(s, f)
