"""方块定义、旋转生成、7-bag 随机生成器与 SRS 踢墙表"""
from __future__ import annotations
import random
from typing import Iterator

# ---------------------------------------------------------------- 方块定义
# 每种方块只定义出生态（旋转 0）的格子坐标，其余旋转态由旋转函数生成。
# 坐标系：x 向右，y 向下；原点为方块 3x3/4x4 包围盒左上角。
SPAWN_CELLS: dict[str, list[tuple[int, int]]] = {
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "O": [(1, 0), (2, 0), (1, 1), (2, 1)],
}
PIECE_NAMES = list(SPAWN_CELLS)

ALL_CELLS: dict[str, list[list[tuple[int, int]]]] = {}


def _rot_cw(cells: list[tuple[int, int]], n: int) -> list[tuple[int, int]]:
    """顺时针旋转 90°（包围盒边长 n）。y 向下坐标系： (x,y) -> (n-1-y, x)"""
    return [(n - 1 - y, x) for x, y in cells]


def _rot_ccw(cells: list[tuple[int, int]], n: int) -> list[tuple[int, int]]:
    """逆时针旋转 90°： (x,y) -> (y, n-1-x)"""
    return [(y, n - 1 - x) for x, y in cells]


def _build_states() -> None:
    for name, spawn in SPAWN_CELLS.items():
        n = 4 if name == "I" else 3
        s0 = sorted(spawn)
        if name == "O":
            # SRS 中 O 块旋转不位移：所有旋转态相同
            ALL_CELLS[name] = [s0, s0, s0, s0]
            continue
        s1 = sorted(_rot_cw(s0, n))
        s2 = sorted(_rot_cw(s1, n))
        s3 = sorted(_rot_ccw(s0, n))
        ALL_CELLS[name] = [s0, s1, s2, s3]


_build_states()

# ---------------------------------------------------------------- SRS 踢墙表
# 键：(当前态, 目标态)；值：依次尝试的 (dx, dy) 偏移，y 向下为正。
KICKS_JLSTZ: dict[tuple[int, int], list[tuple[int, int]]] = {
    (0, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (1, 0): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (1, 2): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (2, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (2, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    (3, 2): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (3, 0): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (0, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
}
KICKS_I: dict[tuple[int, int], list[tuple[int, int]]] = {
    (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
    (1, 0): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
    (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
    (2, 1): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
    (2, 3): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
    (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
    (3, 0): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
    (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
}
KICKS_O: dict[tuple[int, int], list[tuple[int, int]]] = {(0, 1): [(0, 0)], (1, 0): [(0, 0)],
                                                        (1, 2): [(0, 0)], (2, 1): [(0, 0)],
                                                        (2, 3): [(0, 0)], (3, 2): [(0, 0)],
                                                        (3, 0): [(0, 0)], (0, 3): [(0, 0)]}


def kicks_for(name: str) -> dict[tuple[int, int], list[tuple[int, int]]]:
    if name == "I":
        return KICKS_I
    if name == "O":
        return KICKS_O
    return KICKS_JLSTZ


def t_spin_corners(ox: int, oy: int) -> list[tuple[int, int]]:
    """T 方块 3x3 包围盒的四角（用于 T-spin 判定）"""
    return [(ox - 1, oy - 1), (ox + 3, oy - 1), (ox - 1, oy + 3), (ox + 3, oy + 3)]


# ---------------------------------------------------------------- 7-bag 生成器
class Bag7:
    """7-bag 随机：每 7 个为一组，组内不重复。"""

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self._bag: list[str] = []

    def _refill(self) -> None:
        bag = PIECE_NAMES[:]
        self.rng.shuffle(bag)
        self._bag.extend(bag)

    def next(self) -> str:
        if not self._bag:
            self._refill()
        return self._bag.pop(0)

    def peek(self, n: int) -> list[str]:
        out: list[str] = []
        while len(self._bag) < n:
            self._refill()
        for i in range(n):
            out.append(self._bag[i])
        return out


def bag_iterator(rng: random.Random | None = None) -> Iterator[str]:
    bag = Bag7(rng)
    while True:
        yield bag.next()
