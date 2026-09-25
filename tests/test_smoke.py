"""冒烟测试：无头模式下模拟完整游玩流程，验证游戏循环不崩溃、可通关"""
from __future__ import annotations
import math
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

pygame.init()
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except Exception:
    pass

from tetris_game.game import Game
from tetris_game.constants import COLS, ROWS
from tetris_game.pieces import ALL_CELLS

FAILS = []


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(name)
        print(f"  ✗ {name} {detail}")
    else:
        print(f"  ✓ {name}")


def make_game() -> Game:
    screen = pygame.display.set_mode((1280, 800))
    return Game(screen, os.path.join(os.path.dirname(__file__), "_smoke_records.json"))


def test_menu_navigation():
    print("菜单导航")
    g = make_game()
    g.buttons = g._make_menu_buttons()
    check("初始状态为菜单", g.state == "menu")
    check("菜单按钮 9 个", len(g.buttons) == 9)
    g._move_selection(1)
    check("向下选择", g._selected_action() == "start:sprint40", f"act={g._selected_action()}")
    g._set_hover(6)
    check("选到无尽生存", g._selected_action() == "start:endless", f"act={g._selected_action()}")
    g._set_hover(7)
    check("选到设置", g._selected_action() == "settings", f"act={g._selected_action()}")
    g._set_hover(8)
    check("选到退出", g._selected_action() == "quit", f"act={g._selected_action()}")
    g._activate("start:sprint40")
    check("开局进入倒计时", g.state == "countdown" and g.board is not None)


def test_new_modes():
    print("新模式：奶酪突击 / 限时 / 无尽")
    g = make_game()
    # 奶酪：预埋垃圾行 + 行数目标
    g.new_game("cheese40")
    g.update(4.0)
    b = g.board
    n_garbage = sum(1 for (c, r) in b.grid if r >= ROWS - 10)
    check("奶酪模式预埋垃圾行", n_garbage >= 80, f"cells={n_garbage}")
    b.lines = 39
    check("奶酪行数目标未到", b.goal_met() is False)
    b.lines = 40
    check("奶酪行数达标判定", b.goal_met() is True)
    # 限时：时间到自动通关，纪录为分数
    g.new_game("blitz120")
    g.update(4.0)
    g.board.score = 500
    g.elapsed = 119.5
    g.update(0.6)
    check("限时时间到通关", g.state == "gameover" and g.win, f"state={g.state}")
    check("限时纪录为分数", g.records["blitz120"] == 500, f"rec={g.records['blitz120']}")
    # 无尽：重力随时间加速
    g.new_game("endless")
    g.update(4.0)
    b2 = g.board
    b2.gravity_scale_override = None
    g1 = b2.gravity_per_frame(1 / 60)
    b2.clock = 100.0
    g2 = b2.gravity_per_frame(1 / 60)
    check("无尽重力加速", g2 > g1, f"t0={g1:.3f} t100={g2:.3f}")


def test_random_play():
    print("随机输入游玩不崩溃")
    g = make_game()
    g.new_game("sprint40")
    g.update(4.0)
    keys = [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_z,
            pygame.K_a, pygame.K_DOWN, pygame.K_c]
    rng = random.Random(3)
    for i in range(900):
        if g.state != "playing":
            break
        if rng.random() < 0.5:
            g.on_key_down(rng.choice(keys), 0)
            g.on_key_up(rng.choice(keys))
        if rng.random() < 0.08:
            g.on_key_down(pygame.K_SPACE, 0)
            g.on_key_up(pygame.K_SPACE)
        g.update(1 / 60)
    b = g.board
    check("随机游玩后已放块 > 0", b.pieces_placed > 0, f"placed={b.pieces_placed}")
    check("计时进行", g.elapsed > 1.0, f"elapsed={g.elapsed:.2f}")
    check("PPS 计算正常", g.pps >= 0, f"pps={g.pps:.2f}")


# ------------------------------------------------------------ 贪心 AI（棋盘级摆放验证通关链路）
def _candidate_score(grid, name, x, y, rot):
    """调参确认的启发式：landing/eroded/holes/bump + 强消行奖励，分数越高越好"""
    cells = [(x + cx, y + cy) for cx, cy in ALL_CELLS[name][rot]]
    ng = dict(grid)
    for c, r in cells:
        if r < 0:
            return -1e9
        ng[(c, r)] = name
    clear_rows = [r for r in range(ROWS)
                  if all((c, r) in ng for c in range(COLS))]
    eroded = 0
    for r in clear_rows:
        eroded += sum(1 for c, rr in cells if rr == r)
        for c in range(COLS):
            ng.pop((c, r), None)
    heights = [0] * COLS
    for c in range(COLS):
        for r in range(ROWS):
            if (c, r) in ng:
                heights[c] = ROWS - r
                break
    holes = 0
    for c in range(COLS):
        seen = False
        for r in range(ROWS):
            if (c, r) in ng:
                seen = True
            elif seen:
                holes += 1
    bump = sum(abs(heights[i] - heights[i + 1]) for i in range(COLS - 1))
    landing = ROWS - min(r for _, r in cells)
    return (landing * -0.51 + eroded * 0.76 + holes * -0.76 +
            bump * -0.36 + len(clear_rows) * 8.0)


def _landing_y(grid, name, x, rot):
    """从顶部下落，返回落点 y（与离线调参模拟一致）"""
    y = 0
    while True:
        cells = [(x + cx, y + 1 + cy) for cx, cy in ALL_CELLS[name][rot]]
        if any(c < 0 or c >= COLS or r >= ROWS or (c >= 0 and r >= 0 and (c, r) in grid)
               for c, r in cells):
            break
        y += 1
    return y


def ai_best_move(board):
    """返回 (rot, x)，对当前方块找最优落点（离线调参同款逻辑）"""
    p = board.piece
    best = None
    best_score = -1e9
    rots = range(4) if p.name != "O" else (0,)
    for rot in rots:
        for x in range(COLS):
            y = _landing_y(board.grid, p.name, x, rot)
            cells = [(x + cx, y + cy) for cx, cy in ALL_CELLS[p.name][rot]]
            if any(c < 0 or c >= COLS or r >= ROWS or r < 0 for c, r in cells):
                continue
            s = _candidate_score(board.grid, p.name, x, y, rot)
            if s > best_score:
                best_score = s
                best = (rot, x)
    return best


def test_sprint_completion():
    print("竞速 40 行通关链路（锁定→消行→结算→纪录）")
    from tetris_game.board import Piece
    g = make_game()
    g.new_game("sprint40")
    g.update(4.0)
    b = g.board
    # 第一步：预填底部两行，用真实锁定流程消 2 行
    for r in (18, 19):
        for c in range(COLS):
            b.grid[(c, r)] = "O"
    for c in range(COLS):
        if c in (4, 5, 6, 7):
            b.grid.pop((c, 19), None)
    b.piece = Piece("I", 4, 18, 0)   # 补齐 (4..7,19)
    ev = b.lock()
    check("预填两行真实消行", ev is not None and b.lines == 2, f"lines={b.lines}")
    # 第二步：计数器推到 39，再真实消 1 行 → 触发通关
    b.lines = 39
    for c in range(COLS):
        if c not in (4, 5, 6, 7):
            b.grid[(c, 19)] = "O"
    b.piece = Piece("I", 4, 18, 0)
    ev2 = b.lock()
    check("第 40 行消除", ev2 is not None and b.lines == 40, f"lines={b.lines}")
    g._spawn_next()
    check("通关进入结算", g.state == "gameover" and g.win, f"state={g.state} win={g.win}")
    check("用时记录已保存", g.records["sprint40"] is not None)


def test_pause_and_restart():
    print("暂停/重开/设置")
    g = make_game()
    g.new_game("sprint100")
    g.update(4.0)
    g.on_key_down(pygame.K_ESCAPE, 0)
    check("ESC 暂停", g.state == "paused", f"state={g.state}")
    g._activate("resume")
    check("继续", g.state == "playing")
    g.on_key_down(pygame.K_ESCAPE, 0)
    g._activate("settings")
    check("进入设置", g.state == "settings")
    g.settings_idx = next(i for i, item in enumerate(g.settings_items) if item[0] == "volume")
    g._settings_key(pygame.K_RIGHT)
    check("音量调整生效", g.settings["volume"] > 0.7, f"vol={g.settings['volume']}")
    g.settings_idx = next(i for i, item in enumerate(g.settings_items) if item[0] == "gravity_speed")
    g.settings["gravity_speed"] = "very_slow"
    g._settings_key(pygame.K_LEFT)
    check("自动下落可关闭", g.settings["gravity_speed"] == "off"
          and g.board.gravity_scale_override == 0.0)
    g.settings["gravity_speed"] = "very_slow"
    g.board.gravity_scale_override = 0.15
    g.save_settings()
    g._settings_key(pygame.K_ESCAPE)
    check("设置返回暂停", g.state == "paused", f"state={g.state}")
    g._activate("restart")
    check("重开进入倒计时", g.state == "countdown")


def test_keybinding_settings():
    print("自定义键位与冲突交换")
    g = make_game()
    g.settings["keybinds"] = dict(g.settings["keybinds"])
    old_left = g._key("move_left")
    old_right = g._key("move_right")
    g.state = "keybinds"
    g.keybind_idx = list(g.settings["keybinds"]).index("move_left")
    g._keybinds_key(pygame.K_RETURN)
    check("Enter 进入按键捕获", g.binding_capture == "move_left")
    g._keybinds_key(old_right)
    check("新键位生效", g._key("move_left") == old_right)
    check("冲突键位自动交换", g._key("move_right") == old_left)
    g._keybinds_key(pygame.K_F2)
    from tetris_game.game import DEFAULT_KEYBINDS
    check("F2 恢复全部默认", g.settings["keybinds"] == DEFAULT_KEYBINDS)


def test_fullscreen_setting_callback():
    print("全屏设置回调")
    calls = []
    screen = pygame.display.set_mode((1280, 800))
    g = Game(screen, os.path.join(os.path.dirname(__file__), "_smoke_records.json"),
             fullscreen_toggle=lambda enabled=None: calls.append(enabled) or bool(enabled))
    g.state = "settings"
    g.settings_idx = next(i for i, item in enumerate(g.settings_items) if item[0] == "fullscreen")
    before = g.settings["fullscreen"]
    g._settings_key(pygame.K_RIGHT)
    check("设置页调用全屏切换", calls == [not before])
    check("全屏状态同步", g.settings["fullscreen"] is (not before))
    g.set_fullscreen_state(False)


def test_gameover_screens():
    print("游戏结束与返回菜单")
    g = make_game()
    g.new_game("sprint40")
    g.update(4.0)
    g.board.game_over = True
    g.update(1 / 60)
    check("顶出进入结束页", g.state == "gameover" and not g.win, f"state={g.state}")
    g._activate("back_menu")
    check("返回菜单", g.state == "menu")
    g._activate("start:marathon")
    check("马拉松开局", g.state == "countdown" and g.mode == "marathon")


def test_draw_all_states():
    print("各状态渲染不崩溃")
    g = make_game()
    g.draw()
    g.new_game("sprint40")
    g.draw()
    g.update(4.0)
    for _ in range(30):
        g.update(1 / 60)
    g.draw()
    g.on_key_down(pygame.K_ESCAPE, 0)
    g.draw()
    g._activate("settings")
    g.draw()
    g._settings_key(pygame.K_ESCAPE)
    g._activate("restart")
    g.update(4.0)
    g.board.game_over = True
    g.update(1 / 60)
    g.draw()
    check("全部状态渲染通过", True)


def test_view_rotation():
    print("360° 视角旋转")
    g = make_game()
    g.new_game("sprint40")
    g.update(4.0)
    r = g.renderer
    check("默认视角为 0", r.yaw == 0.0 and r.pitch == 0.0, f"yaw={r.yaw}")
    x0, y0 = r.to_screen(5, 5)
    check("to_screen 与旧等距一致", abs(x0 - (5 - 5) * 20 - r.ox) < 1e-6, f"x={x0}")
    g.on_key_down(pygame.K_e, 0)
    check("E 键旋转视角", r.yaw > 0.0, f"yaw={r.yaw:.3f}")
    g.on_key_down(pygame.K_q, 0)
    check("Q 键反向旋转", r.yaw < 0.05, f"yaw={r.yaw:.3f}")
    g.on_key_down(pygame.K_v, 0)
    check("V 键复位视角", r.yaw == 0.0, f"yaw={r.yaw}")
    g.on_key_down(pygame.K_f, 0)
    x_left, y_top = r.to_screen(0, 0)
    x_right, y_bottom = r.to_screen(10, 20)
    check("F 键进入正面视角", x_right > x_left and y_bottom > y_top
          and r.pitch > math.radians(50), f"yaw={r.yaw:.3f} pitch={r.pitch:.3f}")
    # 180° 翻转后完整立体包围盒仍在中央裁切区内；垂直中心会为
    # 方块高度/平台厚度留出少量光学补偿，不再强绑地面中点。
    r.set_view(math.pi, 0.0)
    x1, y1 = r.to_screen(5, 9)
    from tetris_game.constants import BOARD_CX, BOARD_CY
    check("180° 视角场地居中", abs(x1 - BOARD_CX) < 1e-6 and abs(y1 - BOARD_CY) < 6,
          f"({x1:.1f},{y1:.1f}) vs ({BOARD_CX},{BOARD_CY})")
    r.set_front_view()
    bounds = r.playfield_bounds()
    from tetris_game.game import SCENE_RECT
    check("俯视完整场地不被裁切", SCENE_RECT.contains(bounds),
          f"bounds={bounds} scene={SCENE_RECT} zoom={r.zoom:.3f}")
    # 拖拽旋转
    r.set_view(0.0, 0.0)
    g.drag_start((600, 400))
    g.drag_move((640, 420))
    check("拖拽采用自然轨道方向", r.yaw > 0.0 and r.pitch < 0.0,
          f"yaw={r.yaw:.3f} pitch={r.pitch:.3f}")
    g.drag_end()
    g.drag_move((500, 300))   # 拖拽结束后不再响应
    check("拖拽结束停止旋转", r.yaw < 1.0, f"yaw={r.yaw:.3f}")
    # 渲染各角度不崩溃
    for deg in (45, 120, 200, 300):
        r.set_view(deg * math.pi / 180, 0.25)
        g.draw()
    check("各角度渲染通过", True)


def test_skins_and_backgrounds():
    print("方块材质与背景主题")
    g = make_game()
    g.new_game("sprint40")
    g.update(1.0)
    from tetris_game.constants import SKINS, SKIN_ORDER, BG_THEMES
    # 每种材质渲染不崩溃
    for name in SKIN_ORDER:
        g.renderer.set_skin(name)
        g.draw()
    check("六种材质渲染通过", True)
    g.renderer.set_skin("neon")
    # 设置界面循环切换材质/背景
    g.state = "settings"
    g.settings_idx = next(i for i, item in enumerate(g.settings_items) if item[0] == "skin")
    g.on_key_down(pygame.K_RIGHT, 0)   # 材质 -> 水晶
    check("设置切换材质", g.settings["skin"] == "crystal"
          and g.renderer.current_skin is SKINS["crystal"], g.settings["skin"])
    g.settings_idx = next(i for i, item in enumerate(g.settings_items) if item[0] == "bg_theme")
    g.on_key_down(pygame.K_RIGHT, 0)   # 背景 -> 星云
    check("设置切换背景", g.settings["bg_theme"] == "nebula", g.settings["bg_theme"])
    g.state = "playing"
    g.draw()
    # 各主题背景渲染
    from tetris_game.renderer import draw_bg_theme
    tmp = pygame.Surface((1280, 800))
    for theme in BG_THEMES:
        draw_bg_theme(tmp, theme, 0.5, g.renderer.custom_bg)
    check("六种背景主题渲染通过", True)
    # 自定义背景图
    bg_path = os.path.join(os.path.dirname(__file__), "_test_bg.png")
    pygame.image.save(tmp, bg_path)
    check("自定义背景加载", g.renderer.load_custom_bg(bg_path), "")
    g.settings["custom_bg"] = bg_path
    g.settings["bg_theme"] = "custom"
    g.draw()
    check("自定义背景绘制通过", True)
    # 设置持久化
    g.save_settings()
    g2 = make_game()
    check("设置持久化读取", g2.settings["skin"] == "crystal"
          and g2.settings["bg_theme"] == "custom", str(g2.settings))
    # 还原，避免污染后续测试
    g2.settings["skin"] = "neon"
    g2.settings["bg_theme"] = "default"
    g2.settings["custom_bg"] = ""
    g2.save_settings()


if __name__ == "__main__":
    test_menu_navigation()
    test_random_play()
    test_sprint_completion()
    test_new_modes()
    test_view_rotation()
    test_skins_and_backgrounds()
    test_pause_and_restart()
    test_keybinding_settings()
    test_fullscreen_setting_callback()
    test_gameover_screens()
    test_draw_all_states()
    print()
    if FAILS:
        print("失败：", FAILS)
        sys.exit(1)
    print("冒烟测试全部通过 ✔")
