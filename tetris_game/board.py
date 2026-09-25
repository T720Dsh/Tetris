"""场地逻辑：网格、碰撞、消行、锁定、T-spin 判定、指南计分"""
from __future__ import annotations
from dataclasses import dataclass, field

from .constants import COLS, ROWS, HIDDEN_TOP, LOCK_DELAY, LOCK_MAX_RESET, BASE_GRAVITY_CPS
from .pieces import ALL_CELLS, t_spin_corners

FULL_H = ROWS + HIDDEN_TOP          # 含隐藏行的总行数（负行号为隐藏区）
TOP_ROW = -HIDDEN_TOP               # 最顶可见行（-2 为隐藏顶部）


@dataclass
class Piece:
    name: str
    x: int
    y: int
    rot: int = 0
    rotated: bool = False            # 本块是否发生过旋转（T-spin 判定用）
    grounded: bool = False

    def cells(self) -> list[tuple[int, int]]:
        return [(self.x + cx, self.y + cy) for cx, cy in ALL_CELLS[self.name][self.rot]]


@dataclass
class ClearEvent:
    """一次锁定后的结算信息"""
    rows: list[int] = field(default_factory=list)
    tspin: str | None = None          # None / "mini" / "full"
    b2b: bool = False
    combo: int = 0
    perfect: bool = False
    score: int = 0
    points: dict[str, int] = field(default_factory=dict)
    piece_y: int = 0                  # 锁定前方块的行位置


class Board:
    def __init__(self, mode: str = "sprint40"):
        self.mode = mode
        self.bag = None                          # 由 Game 注入，用于自动补队列
        self.grid: dict[tuple[int, int], str] = {}   # (c, r) -> piece name
        self.piece: Piece | None = None
        self.hold: str | None = None
        self.hold_used = False
        self.next_queue: list[str] = []
        self.garbage_seed: int = 0

        self.score = 0
        self.lines = 0
        self.level = 1
        self.pieces_placed = 0
        self.combo = 0
        self.b2b = False
        self.perfect_chain = 0

        self.lock_timer = 0.0
        self.lock_resets = 0
        self.gravity_acc = 0.0
        self.drop_frac = 0.0            # 渲染用下落插值
        self.gravity_scale_override: float | None = None  # 设置覆盖：模式重力倍率
        self.clock = 0.0                # 对局已进行秒数（无尽模式重力加速用）
        self.game_over = False
        self.marathon_clear = False
        self.last_event: ClearEvent | None = None

    # ------------------------------------------------------------ 重力
    def gravity_per_frame(self, dt: float) -> float:
        """返回每帧下落格数"""
        if self.mode == "marathon":
            s = (0.8 - (self.level - 1) * 0.007) ** (self.level - 1)   # 秒/格（指南公式）
            s = max(s, 0.015)
            gravity = dt / s
        elif self.mode == "endless":
            # 每 20 秒升一级，重力持续加速（指南公式加速）
            lv = 1 + int(self.clock // 20)
            s = (0.8 - (lv - 1) * 0.007) ** (lv - 1)
            s = max(s, 0.015)
            gravity = dt / s
        else:
            gravity = BASE_GRAVITY_CPS * dt
        scale = 1.0 if self.gravity_scale_override is None else self.gravity_scale_override
        return gravity * max(0.0, scale)

    # ------------------------------------------------------------ 垃圾行（奶酪模式）
    def seed_garbage(self, rows: int, rng) -> None:
        """在场地底部预埋乱序垃圾行：每行随机挖 1~2 个洞，保证可清且不会开局自动消行"""
        if rows <= 0:
            return
        for r in range(ROWS - rows, ROWS):
            cols = list(range(COLS))
            rng.shuffle(cols)
            holes = cols[:2] if rng.random() < 0.5 else cols[:1]
            for c in range(COLS):
                if c not in holes:
                    self.grid[(c, r)] = rng.choice(("J", "L", "S", "Z", "O", "T"))

    # ------------------------------------------------------------ 碰撞
    def collides(self, name: str, x: int, y: int, rot: int) -> bool:
        for cx, cy in ALL_CELLS[name][rot]:
            gx, gy = x + cx, y + cy
            if gx < 0 or gx >= COLS or gy >= ROWS:
                return True
            if gy >= TOP_ROW and (gx, gy) in self.grid:
                return True
        return False

    # ------------------------------------------------------------ 出块
    def spawn(self, name: str | None = None) -> bool:
        if name is None:
            if not self.next_queue and self.bag is not None:
                while len(self.next_queue) < 5:
                    self.next_queue.append(self.bag.next())
            name = self.next_queue.pop(0)
        x = 3
        y = -2 if name == "I" else -1
        if self.collides(name, x, y, 0):
            self.game_over = True
            return False
        self.piece = Piece(name, x, y, 0)
        self.lock_timer = 0.0
        self.lock_resets = 0
        self.gravity_acc = 0.0
        self.drop_frac = 0.0
        return True

    def refill_next(self, bag) -> None:
        while len(self.next_queue) < 5:
            self.next_queue.append(bag.next())

    # ------------------------------------------------------------ 移动 / 旋转
    def try_move(self, dx: int, dy: int) -> bool:
        if not self.piece or self.game_over:
            return False
        p = self.piece
        if not self.collides(p.name, p.x + dx, p.y + dy, p.rot):
            p.x += dx
            p.y += dy
            p.grounded = self._hits_ground()
            return True
        return False

    def try_rotate(self, direction: int) -> bool:
        """direction: 1=顺时针, -1=逆时针, 2=180°"""
        if not self.piece or self.game_over:
            return False
        p = self.piece
        new_rot = (p.rot + direction) % 4
        if direction == 2:
            # 180° 旋转：先转 1 再转 1，踢墙依次尝试
            for kx, ky in self._kicks(p, p.rot, (p.rot + 1) % 4):
                mid_rot = (p.rot + 1) % 4
                if self.collides(p.name, p.x + kx, p.y + ky, mid_rot):
                    continue
                for kx2, ky2 in self._kicks(p, mid_rot, new_rot):
                    if not self.collides(p.name, p.x + kx + kx2, p.y + ky + ky2, new_rot):
                        p.x += kx + kx2
                        p.y += ky + ky2
                        p.rot = new_rot
                        p.rotated = True
                        p.grounded = self._hits_ground()
                        return True
            return False
        for kx, ky in self._kicks(p, p.rot, new_rot):
            if not self.collides(p.name, p.x + kx, p.y + ky, new_rot):
                p.x += kx
                p.y += ky
                p.rot = new_rot
                p.rotated = True
                p.grounded = self._hits_ground()
                return True
        return False

    def _kicks(self, p: Piece, frm: int, to: int):
        from .pieces import kicks_for
        return kicks_for(p.name)[(frm, to)]

    def _hits_ground(self) -> bool:
        if not self.piece:
            return False
        p = self.piece
        return self.collides(p.name, p.x, p.y + 1, p.rot)

    def drop_distance(self) -> int:
        """硬降下落格数"""
        if not self.piece:
            return 0
        p = self.piece
        d = 0
        while not self.collides(p.name, p.x, p.y + d + 1, p.rot):
            d += 1
        return d

    def hard_drop(self) -> int:
        if not self.piece or self.game_over:
            return 0
        d = self.drop_distance()
        self.piece.y += d
        self.score += 2 * d
        self.drop_frac = 0.0
        return d

    def soft_drop_step(self) -> bool:
        if not self.piece or self.game_over:
            return False
        if self.try_move(0, 1):
            self.score += 1
            self.lock_timer = 0.0
            self.lock_resets = 0
            self.drop_frac = 0.0
            return True
        return False

    # ------------------------------------------------------------ 更新（重力 + 锁定）
    def update(self, dt: float) -> None:
        self.clock += dt
        if not self.piece or self.game_over:
            return
        p = self.piece
        g = self.gravity_per_frame(dt)
        if g >= 1.0:
            # 高重力：本帧至少下落一格，直接落到着地点
            if not p.grounded:
                self.piece.y += self.drop_distance()
                p.grounded = True
            self.drop_frac = 0.0
        else:
            self.gravity_acc += g
            while self.gravity_acc >= 1.0:
                if not self.try_move(0, 1):
                    break
                self.gravity_acc -= 1.0
            self.drop_frac = self.gravity_acc

        if p.grounded:
            self.lock_timer += dt
            self.drop_frac = 0.0
            if self.lock_timer >= LOCK_DELAY:
                self.lock()
        else:
            self.lock_timer = 0.0

    def reset_lock(self) -> None:
        """成功移动/旋转且仍贴地时重置锁定延迟（有限次数）"""
        if self.lock_resets < LOCK_MAX_RESET:
            self.lock_timer = 0.0
            self.lock_resets += 1

    # ------------------------------------------------------------ 锁定与结算
    def lock(self) -> ClearEvent | None:
        if not self.piece:
            return None
        p = self.piece
        for cx, cy in p.cells():
            if cy < TOP_ROW:
                self.game_over = True
                return None
            self.grid[(cx, cy)] = p.name

        ev = self._resolve(p)
        ev.piece_y = p.y
        self.pieces_placed += 1
        self.piece = None
        self.hold_used = False
        self.last_event = ev
        return ev

    def _resolve(self, p: Piece) -> ClearEvent:
        ev = ClearEvent()
        # 找出完整行（扫描整场，指南规则：任何满行都会消）
        rows = set()
        for r in range(ROWS):
            if all((c, r) in self.grid for c in range(COLS)):
                rows.add(r)
        ev.rows = sorted(rows)

        # T-spin 判定（墙/地板算作已占角）
        if p.name == "T" and p.rotated:
            corners = t_spin_corners(p.x, p.y)
            filled = sum(1 for c, r in corners
                         if (c < 0 or c >= COLS or r >= ROWS) or (r >= TOP_ROW and (c, r) in self.grid))
            if filled >= 3:
                ev.tspin = "full"
            elif filled == 2:
                ev.tspin = "mini"

        n = len(ev.rows)
        # 消行
        if n:
            for r in ev.rows:
                for c in range(COLS):
                    self.grid.pop((c, r), None)
            self._collapse(ev.rows)
            self.lines += n
            self.combo += 1
            ev.combo = self.combo
            if self.mode == "marathon":
                self.level = min(20, self.lines // 10 + 1)
        else:
            self.combo = 0
            self.perfect_chain = 0

        # 全清判定
        ev.perfect = (not self.grid) and n > 0
        if ev.perfect:
            self.perfect_chain += 1
        else:
            self.perfect_chain = 0

        ev.score, ev.points = self._score(ev, n)
        self.score += ev.score

        # B2B 状态更新
        is_b2b_eligible = n > 0 and (ev.tspin == "full" or n == 4)
        if is_b2b_eligible:
            ev.b2b = self.b2b
            self.b2b = True
        elif n > 0:
            self.b2b = False
        return ev

    def _collapse(self, rows: list[int]) -> None:
        """删除空行并让上方方块下落（每清一行，其上方方块 +1 行）"""
        if not rows:
            return
        new_grid: dict[tuple[int, int], str] = {}
        for (c, r), name in self.grid.items():
            drop = sum(1 for rr in rows if rr > r)
            new_grid[(c, r + drop)] = name
        self.grid = new_grid

    def _score(self, ev: ClearEvent, n: int) -> tuple[int, dict[str, int]]:
        """指南计分。返回 (总分, 明细)"""
        if ev.tspin == "full":
            val = {0: 400, 1: 800, 2: 1200, 3: 1600}[n]
        elif ev.tspin == "mini":
            val = {0: 100, 1: 200, 2: 400}.get(n, 0)
        else:
            val = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}[n]
        combo_bonus = 50 * (ev.combo - 1) if ev.combo >= 2 else 0
        total = val + combo_bonus
        b2b_bonus = 0
        if ev.b2b and (ev.tspin == "full" or n == 4):
            total = int(total * 1.5)
            b2b_bonus = total - val - combo_bonus
        perfect_bonus = 3500 if ev.perfect else 0
        total += perfect_bonus
        return total, {
            "lines": val if not ev.tspin else 0,
            "tspin": val if ev.tspin else 0,
            "combo": combo_bonus,
            "b2b": b2b_bonus,
            "perfect": perfect_bonus,
        }

    def check_marathon_clear(self) -> bool:
        return self.goal_met()

    def goal_met(self) -> bool:
        """当前模式的目标是否已达成（行数/分数型）"""
        from .constants import MODE_CFG
        cfg = MODE_CFG.get(self.mode)
        if cfg is None:
            return False
        if cfg["goal"] == "lines":
            return self.lines >= cfg["target"]
        if cfg["goal"] == "score":
            return self.score >= cfg["target"]
        return False

    # ------------------------------------------------------------ 暂存
    def do_hold(self, bag) -> bool:
        if self.hold_used or self.game_over or not self.piece:
            return False
        old = self.piece.name
        if self.hold is None:
            self.hold = old
            while len(self.next_queue) < 1:
                self.next_queue.append(bag.next())
            self.spawn(self.next_queue.pop(0))
        else:
            nxt = self.hold
            self.hold = old
            self.spawn(nxt)
        self.hold_used = True
        return True

    # ------------------------------------------------------------ 栈高告警
    def danger_level(self) -> float:
        """0~1：堆叠越接近顶部越危险"""
        worst = 0.0
        for r in range(TOP_ROW, 8):
            for c in range(COLS):
                if (c, r) in self.grid:
                    frac = 1.0 - (r - TOP_ROW) / (8 - TOP_ROW)
                    worst = max(worst, frac)
        return worst

    def stack_height(self) -> int:
        h = 0
        for r in range(ROWS):
            if any((c, r) in self.grid for c in range(COLS)):
                h = ROWS - r
        return h
