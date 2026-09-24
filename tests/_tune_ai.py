"""离线调参：找出能稳定打通 40 行的贪心启发式权重"""
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tetris_game.constants import COLS, ROWS
from tetris_game.pieces import ALL_CELLS, Bag7


def place_y(grid, name, x, rot):
    y0 = 0
    while True:
        cells2 = [(x + cx, y0 + 1 + cy) for cx, cy in ALL_CELLS[name][rot]]
        if any(c < 0 or c >= COLS or r >= ROWS or (c >= 0 and r >= 0 and (c, r) in grid)
               for c, r in cells2):
            break
        y0 += 1
    return [(x + cx, y0 + cy) for cx, cy in ALL_CELLS[name][rot]]


def collapse(grid, cleared):
    if not cleared:
        return grid
    ng = {}
    for (c, r), v in grid.items():
        drop = sum(1 for rr in cleared if rr > r)
        ng[(c, r + drop)] = v
    return ng


def simulate(weights, seed, target=40, max_pieces=2500):
    rng = random.Random(seed)
    bag = Bag7(rng)
    grid = {}
    lines = 0
    pieces = 0
    for _ in range(max_pieces):
        name = bag.next()
        best, best_s = None, -1e18
        rots = range(4) if name != "O" else (0,)
        for rot in rots:
            for x in range(COLS):
                cells = place_y(grid, name, x, rot)
                if any(c < 0 or c >= COLS or r >= ROWS or r < 0 for c, r in cells):
                    continue
                ng = dict(grid)
                for c, r in cells:
                    ng[(c, r)] = name
                cleared = [r for r in range(ROWS) if all((c, r) in ng for c in range(COLS))]
                eroded = sum(1 for c, r in cells if r in cleared)
                for r in cleared:
                    for c in range(COLS):
                        ng.pop((c, r), None)
                ng = collapse(ng, cleared)
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
                s = (weights["landing"] * landing + weights["eroded"] * eroded +
                     weights["holes"] * holes + weights["bump"] * bump +
                     weights["lines"] * len(cleared) + weights["height"] * sum(heights))
                if s > best_s:
                    best_s, best = s, (rot, x)
        rot, x = best
        cells = place_y(grid, name, x, rot)
        if any(r < 0 or c < 0 or c >= COLS or r >= ROWS for c, r in cells):
            return lines, pieces  # 顶出
        for c, r in cells:
            grid[(c, r)] = name
        cleared = [r for r in range(ROWS) if all((c, r) in grid for c in range(COLS))]
        if cleared:
            lines += len(cleared)
            for r in cleared:
                for c in range(COLS):
                    grid.pop((c, r), None)
            grid = collapse(grid, cleared)
        pieces += 1
        if lines >= target:
            return lines, pieces
    return lines, pieces


if __name__ == "__main__":
    candidates = [
        {"landing": -0.51, "eroded": 0.76, "holes": -0.76, "bump": -0.36, "lines": 8, "height": 0.0},
        {"landing": -1.0, "eroded": 1.5, "holes": -3.0, "bump": -1.5, "lines": 20, "height": 0.0},
        {"landing": -0.8, "eroded": 2.0, "holes": -2.5, "bump": -2.0, "lines": 15, "height": -0.05},
        {"landing": -0.3, "eroded": 0.5, "holes": -0.5, "bump": -0.2, "lines": 10, "height": 0.0},
        {"landing": -1.2, "eroded": 3.0, "holes": -4.0, "bump": -2.5, "lines": 25, "height": -0.1},
    ]
    for w in candidates:
        ok = 0
        total = 0
        worst = 0
        worst_pieces = 0
        for seed in range(8):
            lines, pieces = simulate(w, seed)
            total += lines
            if lines >= 40:
                ok += 1
            else:
                worst = max(worst, lines)
                worst_pieces = max(worst_pieces, pieces)
        print(f"通关 {ok}/8  均行数 {total/8:.1f}  最差 {worst} (pieces={worst_pieces})  <- {w}")
