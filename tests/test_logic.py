"""核心逻辑单元测试：旋转、踢墙、7-bag、T-spin、计分、消行、软降"""
from __future__ import annotations
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tetris_game.board import Board, Piece
from tetris_game.pieces import ALL_CELLS, Bag7, kicks_for

FAILS = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        FAILS.append(f"{name} {detail}")
        print(f"  ✗ {name} {detail}")
    else:
        print(f"  ✓ {name}")


# ---------------- 方块形状
def test_shapes():
    print("形状（每个旋转态 4 格、包围盒正确）")
    for name, states in ALL_CELLS.items():
        n = 4 if name == "I" else 3
        for rot, cells in enumerate(states):
            check(f"{name} rot{rot} 4格", len(cells) == 4, f"cells={cells}")
            check(f"{name} rot{rot} 范围内", all(0 <= x < n and 0 <= y < n for x, y in cells),
                  f"cells={cells}")
    # 标准出生态抽查
    check("T 出生态", sorted(ALL_CELLS["T"][0]) == [(0, 1), (1, 0), (1, 1), (2, 1)])
    check("I 出生态", sorted(ALL_CELLS["I"][0]) == [(0, 1), (1, 1), (2, 1), (3, 1)])
    check("J 出生态", sorted(ALL_CELLS["J"][0]) == [(0, 0), (0, 1), (1, 1), (2, 1)])
    check("O 不变", ALL_CELLS["O"][0] == ALL_CELLS["O"][1] == ALL_CELLS["O"][2] == ALL_CELLS["O"][3])
    # 旋转闭环
    for name in "IJLOSTZ":
        cells = ALL_CELLS[name]
        check(f"{name} 转4次回原位", sorted(cells[0]) == sorted(cells[(0 + 4) % 4]))


# ---------------- 踢墙
def test_kicks():
    print("SRS 踢墙表完整性")
    for name in ("T", "I", "O"):
        table = kicks_for(name)
        for frm, to in [(0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2), (3, 0), (0, 3)]:
            check(f"{name} kick {(frm, to)}", (frm, to) in table and len(table[(frm, to)]) > 0)


# ---------------- 7-bag
def test_bag():
    print("7-bag 随机性")
    rng = random.Random(42)
    bag = Bag7(rng)
    seen = set()
    ok = True
    for i in range(7):
        nxt = bag.next()
        if nxt in seen:
            ok = False
        seen.add(nxt)
    check("每组 7 个不重复", ok)
    check("7-bag 覆盖全部 7 种", seen == set("IJLOSTZ"))
    a = Bag7(random.Random(7))
    b = Bag7(random.Random(7))
    check("同种子序列一致", [a.next() for _ in range(21)] == [b.next() for _ in range(21)])
    a1 = a.peek(5)
    a2 = a.peek(5)
    check("peek 不消耗队列", a1 == a2 and len(a1) == 5)


# ---------------- 场地基础
def test_board_basic():
    print("场地基础（移动/旋转/碰撞/软降）")
    b = Board("sprint40")
    b.next_queue = ["T", "I", "O", "S", "Z"]
    b.spawn()
    check("出生不越界", b.piece is not None and not b.game_over)
    check("初始无方块", len(b.grid) == 0)
    check("左移", b.try_move(-1, 0))
    check("左移后不出界", b.piece is not None and b.piece.x >= 0)
    r0 = b.piece.rot
    check("旋转成功", b.try_rotate(1) and b.piece.rot == (r0 + 1) % 4)
    b.update(0.05)  # 20G 落地（短步长，避免直接触发锁定）
    check("20G 落地", b.piece is not None and b.piece.grounded)
    before = b.pieces_placed
    b.hard_drop()
    ev = b.lock()
    check("硬降后锁定", ev is not None and b.piece is None)
    check("锁定后场上有 4 格", len(b.grid) == 4)
    check("硬降加分", b.score >= 2 * b.pieces_placed, f"score={b.score}")
    # 软降
    b2 = Board("sprint40")
    b2.next_queue = ["L"]
    b2.spawn()
    b2.update(0.016)  # 落地
    y0 = b2.piece.y
    b2.soft_drop_step()
    check("软降一格", b2.piece.y == y0 + 1)


# ---------------- 消行
def test_line_clear():
    print("消行与计分")
    b = Board("sprint40")
    for c in range(10):
        if c not in (4, 5, 6, 7):
            b.grid[(c, 19)] = "O"      # 19 行缺 4-7 列
    for c in range(3):
        b.grid[(c, 17)] = "L"          # 上方的堆
    b.piece = Piece("I", 4, 18, 0)     # 占 (4..7, 19)，补齐 19 行
    ev = b.lock()
    check("消 1 行", len(ev.rows) == 1 and 19 in ev.rows, f"rows={ev.rows}")
    check("行数统计", b.lines == 1)
    check("分数 100", b.score == 100, f"score={b.score}")
    check("19 行已清空", all((c, 19) not in b.grid for c in range(10)))
    check("上方方块下落", (0, 18) in b.grid and (2, 18) in b.grid, f"keys={sorted(b.grid)}")

    b2 = Board("sprint40")
    for r in range(16, 20):
        for c in range(10):
            b2.grid[(c, r)] = "Z"
    for c in range(4, 8):
        b2.grid.pop((c, 19), None)
    b2.piece = Piece("I", 4, 18, 0)    # 补齐 (4..7,19) → 四行齐
    ev2 = b2.lock()
    check("Tetris 消 4 行", len(ev2.rows) == 4, f"rows={ev2.rows}")
    check("Tetris + 全清 = 4300", b2.score == 4300, f"score={b2.score}")
    check("Tetris 置 b2b", b2.b2b is True)
    check("Tetris 后全空", len(b2.grid) == 0 and ev2.perfect)


# ---------------- T-spin
def test_tspin():
    print("T-spin 判定")
    b = Board("sprint40")
    for c, r in [(6, 16), (10, 16), (10, 20)]:   # T 在 (7,17) rot=1 的三个角
        b.grid[(c, r)] = "O"
    b.piece = Piece("T", 7, 17, 1)
    b.piece.rotated = True
    ev = b.lock()
    check("3 角 T-spin", ev.tspin == "full", f"tspin={ev.tspin}")
    check("T-spin 0 消行得分 400", b.score == 400, f"score={b.score}")

    # mini：2 角 + 旋转（T at (5,10) rot=1，四角 (4,9),(8,9),(4,13),(8,13) 全在场内）
    b2 = Board("sprint40")
    for c, r in [(4, 9), (8, 9)]:
        b2.grid[(c, r)] = "O"
    b2.piece = Piece("T", 5, 10, 1)
    b2.piece.rotated = True
    ev2 = b2.lock()
    check("2 角 mini T-spin", ev2.tspin == "mini", f"tspin={ev2.tspin}")

    b3 = Board("sprint40")
    for c, r in [(6, 16), (10, 16), (10, 20)]:
        b3.grid[(c, r)] = "O"
    b3.piece = Piece("T", 7, 17, 1)
    b3.piece.rotated = False
    ev3 = b3.lock()
    check("未旋转不算 T-spin", ev3.tspin is None, f"tspin={ev3.tspin}")

    # T-spin double（消 2 行）
    b4 = Board("sprint40")
    for c, r in [(6, 16), (10, 16), (10, 20)]:
        b4.grid[(c, r)] = "O"
    for r in (18, 19):
        for c in range(10):
            if not (c == 8 and r == 18):   # 留 T 的 (8,18) 格
                b4.grid[(c, r)] = "S"
    b4.piece = Piece("T", 7, 17, 1)
    b4.piece.rotated = True
    ev4 = b4.lock()
    check("T-spin double", len(ev4.rows) == 2 and ev4.tspin == "full", f"rows={ev4.rows}")
    check("T-spin double 得分 1200", b4.score == 1200, f"score={b4.score}")


# ---------------- 连击
def test_combo():
    print("连击")
    b = Board("sprint40")
    for c in range(10):
        if c not in (4, 5, 6, 7):
            b.grid[(c, 19)] = "O"
    b.piece = Piece("I", 4, 18, 0)
    ev = b.lock()
    check("消行 combo=1", ev.combo == 1 and b.combo == 1, f"combo={b.combo}")
    b.piece = Piece("T", 0, 0, 0)
    b.piece.rotated = False
    ev2 = b.lock()
    check("无消行 combo 归零", b.combo == 0, f"combo={b.combo}")
    # 连击加分：第二次消行 combo=2 → +50
    b3 = Board("sprint40")
    for c in range(10):
        if c not in (4, 5, 6, 7):
            b3.grid[(c, 19)] = "O"
    b3.piece = Piece("I", 4, 18, 0)
    b3.lock()   # combo=1，清 19 行
    for c in range(3, 10):
        b3.grid[(c, 18)] = "O"
    b3.piece = Piece("L", 0, 17, 0)   # 占 (0..2,18)，补齐 18 行
    b3.piece.rotated = False
    ev3 = b3.lock()
    check("第二次消行 combo=2", ev3.combo == 2, f"combo={ev3.combo}")
    check("连击加分 50", ev3.points["combo"] == 50, f"points={ev3.points}")


# ---------------- 危险度与顶出
def test_danger_and_gameover():
    print("危险度与顶出")
    b = Board("sprint40")
    for r in range(0, 6):
        for c in range(10):
            b.grid[(c, r)] = "T"
    check("栈高告警", b.danger_level() > 0.5, f"danger={b.danger_level():.2f}")

    b2 = Board("sprint40")
    for r in range(-1, 4):
        for c in range(10):
            b2.grid[(c, r)] = "T"
    ok = b2.spawn("I")   # I 出生态在 -1 行 → 被堵
    check("顶部被堵 → 游戏结束", not ok and b2.game_over)


# ---------------- 新模式：奶酪 / 无尽 / 目标判定
def test_new_modes_logic():
    print("新模式：奶酪 / 无尽 / 目标判定")
    import random
    from tetris_game.constants import MODES, MODE_CFG, MODE_NAME, MODE_DESC

    check("模式定义齐全", len(MODES) == 7 and all(m in MODE_NAME and m in MODE_DESC and m in MODE_CFG for m in MODES), f"modes={MODES}")
    check("模式配置齐全", all(k in cfg for m, cfg in MODE_CFG.items() for k in ("goal", "target", "gravity", "garbage", "record")), "")

    b = Board("cheese40")
    rng = random.Random(11)
    b.seed_garbage(10, rng)
    rows = sorted(set(r for _, r in b.grid))
    check("奶酪垃圾行位于底部", rows == list(range(10, 20)), f"rows={rows}")
    check("奶酪每行有洞", all(any((c, r) not in b.grid for c in range(10)) for r in range(10, 20)), "")
    check("奶酪无整行预消", all(not all((c, r) in b.grid for c in range(10)) for r in range(10, 20)), "")

    b2 = Board("sprint20")
    b2.lines = 19
    check("sprint20 目标未到", b2.goal_met() is False)
    b2.lines = 20
    check("sprint20 目标达标", b2.goal_met() is True)
    b3 = Board("marathon")
    b3.score = 1499
    check("马拉松目标未到", b3.goal_met() is False)
    b3.score = 1500
    check("马拉松目标达标", b3.goal_met() is True)

    b4 = Board("endless")
    g0 = b4.gravity_per_frame(1 / 60)
    b4.clock = 20.0
    g20 = b4.gravity_per_frame(1 / 60)
    b4.clock = 200.0
    g200 = b4.gravity_per_frame(1 / 60)
    check("无尽重力随时间加速", g0 < g20 <= g200, f"{g0:.3f}/{g20:.3f}/{g200:.3f}")
    check("无尽重力有下限", g200 < 1.0, f"g={g200:.3f}")


if __name__ == "__main__":
    test_shapes()
    test_kicks()
    test_bag()
    test_board_basic()
    test_line_clear()
    test_tspin()
    test_combo()
    test_danger_and_gameover()
    test_new_modes_logic()
    print()
    if FAILS:
        print(f"共 {len(FAILS)} 项失败：")
        for f in FAILS:
            print(" -", f)
        sys.exit(1)
    print("全部通过 ✔")
