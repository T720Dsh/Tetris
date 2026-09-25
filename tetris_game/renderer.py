"""伪 3D 等距渲染器：方块挤出、幽灵、平台、粒子、光效、震屏、背景"""
from __future__ import annotations
import colorsys
import math
import random

import pygame
import pygame.gfxdraw

from .constants import (COLS, ROWS, CELL, CUBE_H,
                        BOARD_CX, BOARD_CY, PIECE_COLORS, GHOST_ALPHA,
                        GRID_ALPHA, BG_TOP, BG_BOT, ACCENT, ACCENT2,
                        SKINS)

TOP_ROW = -2  # 与 board.TOP_ROW 一致


def _shade(c: tuple[int, int, int], f: float) -> tuple[int, int, int]:
    return (max(0, min(255, int(c[0] * f))),
            max(0, min(255, int(c[1] * f))),
            max(0, min(255, int(c[2] * f))))


def _sat(c: tuple[int, int, int], f: float) -> tuple[int, int, int]:
    """按系数调整饱和度（0=灰，1=原色，>1=更艳）"""
    h, s, v = colorsys.rgb_to_hsv(c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)
    s = max(0.0, min(1.0, s * f))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def skin_face_colors(color: tuple[int, int, int], skin: dict) -> tuple:
    """按皮肤计算 顶/东/南/描边 四色（饱和度先应用，再乘明暗系数）"""
    base = _sat(color, skin["saturation"])
    return (_shade(base, skin["top"]), _shade(base, skin["east"]),
            _shade(base, skin["south"]), _shade(base, skin["edge"]))


def draw_top_pattern(surf: pygame.Surface, pts: list[tuple[float, float]],
                     skin: dict, color: tuple[int, int, int], x0: float, y0: float,
                     x2: float, y2: float, top_y0: float, top_y2: float) -> None:
    """顶面装饰图案（按皮肤），pts 为顶面四角 [A_top, B_top, C_top, D_top]"""
    pat = skin.get("pattern")
    if not pat:
        return
    w = x2 - x0
    hgt = y2 - y0
    cx = (x0 + x2) / 2.0
    cy = (top_y0 + top_y2) / 2.0
    if pat == "crystal":
        # 中心菱形高光
        hl = (255, 255, 255, 90)
        tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(tmp, hl, [(cx, cy - hgt * 0.16), (cx + w * 0.10, cy),
                                      (cx, cy + hgt * 0.16), (cx - w * 0.10, cy)])
        surf.blit(tmp, (0, 0))
    elif pat == "metal":
        # 拉丝亮线
        tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        for k in (-0.06, 0.06):
            yy = cy + hgt * k
            pygame.draw.line(tmp, (255, 255, 255, 46),
                             (x0 + w * 0.12, yy), (x2 - w * 0.12, yy), 1)
        surf.blit(tmp, (0, 0))
    elif pat == "pixel":
        # 像素噪点（顶面画小方块点阵）
        tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        c_hi = _shade(color, 1.35)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                if (i * j) != 0:
                    continue
                px = cx + i * w * 0.11
                py = cy + j * hgt * 0.11
                pygame.draw.rect(tmp, (*c_hi, 130), (px - 2, py - 2, 4, 4))
        surf.blit(tmp, (0, 0))
    elif pat == "candy":
        # 左上高光圆点
        tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        hx, hy = x0 + w * 0.28, top_y0 + hgt * 0.26
        pygame.draw.circle(tmp, (255, 255, 255, 70), (int(hx), int(hy)), 4)
        surf.blit(tmp, (0, 0))


def iso(c: float, r: float, h: float = 0.0) -> tuple[float, float]:
    """棋盘坐标 -> 屏幕坐标（固定默认视角，HOLD/NEXT 预览等用）。h 为高度（格）。"""
    sx = (c - r) * CELL
    sy = (c + r) * CELL / 2.0 - h * CUBE_H
    return sx, sy


class Renderer:
    def __init__(self):
        self.yaw = 0.0      # 视角方位角（弧度）：0 = 默认右上等距，可 360° 旋转
        self.pitch = 0.0    # 相对 30° 默认仰角：>0 俯视，<0 接近地平视角
        self.zoom = 1.0
        self.viewport = pygame.Rect(286, 88, 766, 584)
        self._glow_cache: dict[str, pygame.Surface] = {}
        self.surf_off = (0.0, 0.0)   # 绘制到子表面时的坐标偏移
        self.current_skin: dict = SKINS["neon"]
        self.custom_bg: pygame.Surface | None = None
        self._update_center()

    def set_viewport(self, rect: pygame.Rect) -> None:
        self.viewport = pygame.Rect(rect)
        self._update_center()

    def set_skin(self, name: str) -> None:
        self.current_skin = SKINS.get(name, SKINS["neon"])

    def load_custom_bg(self, path: str) -> bool:
        """加载用户背景图并 cover 缩放为窗口尺寸（失败返回 False）"""
        try:
            img = pygame.image.load(path).convert()
        except Exception:
            try:
                img = pygame.image.load(path)
            except Exception:
                return False
        tw, th = 1280, 800
        iw, ih = img.get_size()
        scale = max(tw / iw, th / ih)
        nw, nh = int(iw * scale) + 1, int(ih * scale) + 1
        img = pygame.transform.smoothscale(img, (nw, nh))
        x = (nw - tw) // 2
        y = (nh - th) // 2
        self.custom_bg = img.subsurface((x, y, tw, th)).copy()
        return True

    def _project_raw(self, c: float, r: float, h: float = 0.0) -> tuple[float, float]:
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        u, v = c - r, c + r
        up = u * cy - v * sy
        vp = u * sy + v * cy
        ground_y, height_y = self._camera_factors()
        return up * CELL, vp * CELL * ground_y - h * CUBE_H * height_y

    def _update_center(self) -> None:
        """Fit the complete raised playfield inside the scene at every angle."""
        e = 0.85
        corners = [(-e, TOP_ROW - e), (COLS + e, TOP_ROW - e),
                   (COLS + e, ROWS + e), (-e, ROWS + e)]
        pts = [self._project_raw(c, r, h) for c, r in corners for h in (0.0, 1.15)]
        min_x = min(x for x, _ in pts)
        max_x = max(x for x, _ in pts)
        min_y = min(y for _, y in pts)
        max_y = max(y for _, y in pts)
        # Leave room for the platform thickness, antialias fringe and shake.
        avail_w = max(1.0, self.viewport.width - 42.0)
        avail_h = max(1.0, self.viewport.height - 54.0)
        span_w = max(1.0, max_x - min_x)
        span_h = max(1.0, max_y - min_y + 18.0)
        self.zoom = max(0.55, min(1.0, avail_w / span_w, avail_h / span_h))
        self.ox = self.viewport.centerx - (min_x + max_x) * 0.5 * self.zoom
        self.oy = self.viewport.centery - (min_y + max_y + 18.0) * 0.5 * self.zoom

    def _camera_factors(self) -> tuple[float, float]:
        """Return ground-depth and cube-height projection factors.

        The old formula multiplied both by cos(pitch), so dragging toward a
        front/top view flattened the entire scene. A real elevation model makes
        the board approach a readable classic front view while cube height fades
        naturally as the camera moves overhead.
        """
        elevation = math.radians(30.0) + self.pitch
        ground_y = math.sin(elevation)
        height_y = math.cos(elevation) / math.cos(math.radians(30.0))
        return ground_y, height_y

    def set_view(self, yaw: float, pitch: float) -> None:
        self.yaw = (yaw + math.pi) % math.tau - math.pi
        self.pitch = max(math.radians(-25), min(math.radians(55), pitch))
        self._update_center()

    def set_front_view(self) -> None:
        """Classic readable front view: columns horizontal, rows vertical."""
        self.set_view(-math.pi / 4.0, math.radians(55))

    def set_surface_offset(self, dx: float, dy: float) -> None:
        self.surf_off = (dx, dy)

    def to_screen(self, c: float, r: float, h: float = 0.0) -> tuple[float, float]:
        sx, sy = self._project_raw(c, r, h)
        return (self.ox + sx * self.zoom - self.surf_off[0],
                self.oy + sy * self.zoom - self.surf_off[1])

    def playfield_bounds(self) -> pygame.Rect:
        """Projected raised platform bounds, useful for tests and diagnostics."""
        e = 0.85
        points = [self.to_screen(c, r, h)
                  for c, r in ((-e, TOP_ROW - e), (COLS + e, TOP_ROW - e),
                               (COLS + e, ROWS + e), (-e, ROWS + e))
                  for h in (0.0, 1.15)]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return pygame.Rect(math.floor(min(xs)), math.floor(min(ys)),
                           math.ceil(max(xs) - min(xs)), math.ceil(max(ys) - min(ys) + 18))

    def sort_key(self, c: float, r: float) -> tuple[float, float]:
        """画家算法深度键：v' 大的靠前（后画），同深度按屏幕 x 排序"""
        u, v = c - r, c + r
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        vp = u * sy + v * cy
        up = u * cy - v * sy
        return vp, -up

    # ------------------------------------------------------------ 基础图形
    def _poly(self, surf: pygame.Surface, pts: list[tuple[float, float]],
              color: tuple[int, int, int], alpha: int = 255) -> None:
        """Filled polygon with a one-pixel coverage fringe on diagonal edges."""
        if alpha < 255:
            left = math.floor(min(x for x, _ in pts)) - 1
            top = math.floor(min(y for _, y in pts)) - 1
            right = math.ceil(max(x for x, _ in pts)) + 2
            bottom = math.ceil(max(y for _, y in pts)) + 2
            tmp = pygame.Surface((max(1, right - left), max(1, bottom - top)), pygame.SRCALPHA)
            local = [(int(x - left), int(y - top)) for x, y in pts]
            pygame.gfxdraw.filled_polygon(tmp, local, (*color, alpha))
            pygame.gfxdraw.aapolygon(tmp, local, (*color, alpha))
            surf.blit(tmp, (left, top))
        else:
            local = [(int(round(x)), int(round(y))) for x, y in pts]
            pygame.gfxdraw.filled_polygon(surf, local, color)
            pygame.gfxdraw.aapolygon(surf, local, color)

    def draw_cube(self, surf: pygame.Surface, c: float, r: float,
                  color: tuple[int, int, int], alpha: int = 255,
                  glow: bool = False, z: float = 0.0) -> None:
        """画一个 (c,r) 位置的 1x1x1 方块，外观由 current_skin 决定。z：额外高度偏移（格）"""
        skin = self.current_skin
        if alpha == 255:
            alpha = int(skin["alpha"])
        x0, y0 = self.to_screen(c, r, z)
        x1, y1 = self.to_screen(c + 1, r, z)
        x2, y2 = self.to_screen(c + 1, r + 1, z)
        x3, y3 = self.to_screen(c, r + 1, z)
        _, top_y0 = self.to_screen(c, r, z + 1)
        _, top_y1 = self.to_screen(c + 1, r, z + 1)
        _, top_y2 = self.to_screen(c + 1, r + 1, z + 1)
        _, top_y3 = self.to_screen(c, r + 1, z + 1)

        col_top, col_east, col_south, col_edge = skin_face_colors(color, skin)
        # Light comes from the upper-left of the camera.  Let side brightness react
        # to yaw so rotating the board does not leave the cubes looking painted on.
        east_light = 0.82 + 0.18 * max(0.0, math.cos(self.yaw + 0.55))
        south_light = 0.78 + 0.22 * max(0.0, math.sin(self.yaw + 0.90))
        col_east = _shade(col_east, east_light)
        col_south = _shade(col_south, south_light)
        top_pts = [(x0, top_y0), (x1, top_y1), (x2, top_y2), (x3, top_y3)]

        # Contact occlusion gives depth without a screen-space halo that would
        # bleach this cube or spill across neighbouring blocks.
        self._poly(surf, [(x0, y0 + 2), (x1, y1 + 2),
                          (x2, y2 + 3), (x3, y3 + 3)], (0, 0, 8), 42)

        # 东面（c+1 棱）与南面（r+1 棱）的覆盖顺序随视角方位角翻转：
        # 视角转到背面时，原本的"南面"移到左边，需先画
        east_first = math.cos(self.yaw) >= 0
        if east_first:
            # 东面（右侧，x=c+1 棱）：B -> C -> C_top -> B_top
            self._poly(surf, [(x1, y1), (x2, y2), (x2, top_y2), (x1, top_y1)],
                       col_east, alpha)
            # 南面（左侧，y=r+1 棱）：C -> D -> D_top -> C_top
            self._poly(surf, [(x2, y2), (x3, y3), (x3, top_y3), (x2, top_y2)],
                       col_south, alpha)
        else:
            self._poly(surf, [(x2, y2), (x3, y3), (x3, top_y3), (x2, top_y2)],
                       col_south, alpha)
            self._poly(surf, [(x1, y1), (x2, y2), (x2, top_y2), (x1, top_y1)],
                       col_east, alpha)
        # 顶面（最亮）：A_top -> B_top -> C_top -> D_top
        self._poly(surf, top_pts, col_top, alpha)
        # Small inset bevel: enough to catch light while preserving a clean tile.
        cx = sum(pt[0] for pt in top_pts) / 4
        cy_top = sum(pt[1] for pt in top_pts) / 4
        inset = [(x + (cx - x) * 0.10, y + (cy_top - y) * 0.10) for x, y in top_pts]
        self._poly(surf, inset, _shade(col_top, 1.06), max(0, alpha - 18))
        # Narrow reflected-light strip gives the tile a coated surface without
        # washing neighbouring pieces in a large bloom.
        a0, a1 = top_pts[0], top_pts[1]
        b0 = (a0[0] + (cx - a0[0]) * 0.20, a0[1] + (cy_top - a0[1]) * 0.20)
        b1 = (a1[0] + (cx - a1[0]) * 0.20, a1[1] + (cy_top - a1[1]) * 0.20)
        self._poly(surf, [a0, a1, b1, b0], (255, 255, 255),
                   30 if glow else 17)
        draw_top_pattern(surf, top_pts, skin, color, x0, y0, x2, y2, top_y0, top_y2)

        ew = skin.get("edge_w", 1)
        if alpha >= 220 and ew >= 1:
            # 细描边增加锐利感
            for a, b in [(top_pts[0], top_pts[1]), (top_pts[1], top_pts[2]),
                         (top_pts[2], top_pts[3]), (top_pts[3], top_pts[0]),
                         ((x1, y1), (x1, top_y1)), ((x2, y2), (x2, top_y2)),
                         ((x3, y3), (x3, top_y3))]:
                pygame.draw.aaline(surf, col_edge, a, b)
            # One-pixel specular edge separates adjacent cubes without a halo.
            highlight = (255, 255, 255) if glow else _shade(col_top, 1.18)
            pygame.draw.aaline(surf, highlight, top_pts[0], top_pts[1])
            # A second, translucent inset rim reads as reflected light rather
            # than a flat white outline.
            if glow and skin.get("glow", False):
                inner = [(x + (cx - x) * 0.18, y + (cy_top - y) * 0.18)
                         for x, y in top_pts]
                pygame.draw.aalines(surf, _shade(col_top, 1.32), True, inner)

    def _glow(self, color: tuple[int, int, int]) -> pygame.Surface:
        key = str(color)
        if key not in self._glow_cache:
            size = 82
            g = pygame.Surface((size, size), pygame.SRCALPHA)
            for i in range(size // 2, 0, -1):
                a = int(24 * (1 - i / (size / 2)) ** 2)
                pygame.draw.circle(g, (*color, a), (size // 2, size // 2), i)
            self._glow_cache[key] = g
        return self._glow_cache[key]

    # ------------------------------------------------------------ 幽灵
    def draw_ghost(self, surf: pygame.Surface, cells: list[tuple[int, int]],
                   color: tuple[int, int, int]) -> None:
        for c, r in cells:
            x0, y0 = self.to_screen(c, r)
            x1, y1 = self.to_screen(c + 1, r)
            x2, y2 = self.to_screen(c + 1, r + 1)
            x3, y3 = self.to_screen(c, r + 1)
            _, top_y0 = self.to_screen(c, r, 1)
            _, top_y1 = self.to_screen(c + 1, r, 1)
            _, top_y2 = self.to_screen(c + 1, r + 1, 1)
            _, top_y3 = self.to_screen(c, r + 1, 1)
            col = (*color, GHOST_ALPHA)
            tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            self._poly(tmp, [(x0, top_y0), (x1, top_y1), (x2, top_y2), (x3, top_y3)], color, GHOST_ALPHA)
            edge = (*color, GHOST_ALPHA + 60)
            for a, b in [((x0, top_y0), (x1, top_y1)), ((x1, top_y1), (x2, top_y2)),
                         ((x2, top_y2), (x3, top_y3)), ((x0, top_y0), (x3, top_y3)),
                         ((x1, top_y1), (x1, y1)), ((x2, top_y2), (x2, y2)),
                         ((x3, top_y3), (x3, y3))]:
                pygame.draw.aaline(tmp, edge, a, b)
            surf.blit(tmp, (0, 0))

    # ------------------------------------------------------------ 平台与地面
    def draw_stage_light(self, surf: pygame.Surface, t: float, energy: float = 0.0) -> None:
        """Low-frequency stage lighting tied to play, kept behind the matrix."""
        cx, cy = self.to_screen(COLS * 0.5, (ROWS + TOP_ROW) * 0.5)
        tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pulse = 0.86 + 0.14 * math.sin(t * 1.35)
        for rx, ry, a in ((330, 240, 5), (260, 185, 8), (190, 132, 11)):
            rect = pygame.Rect(0, 0, int(rx * 2 * pulse), int(ry * 2 * pulse))
            rect.center = (round(cx), round(cy + 8))
            pygame.draw.ellipse(tmp, (60, 102, 255, a + int(energy * 12)), rect)
        sway = 34 * math.sin(t * 0.28)
        beam = [(cx - 62 + sway, -30), (cx + 66 + sway, -30),
                (cx + 245, surf.get_height() + 30), (cx - 250, surf.get_height() + 30)]
        pygame.draw.polygon(tmp, (50, 92, 235, 5 + int(energy * 8)), beam)
        surf.blit(tmp, (0, 0), special_flags=pygame.BLEND_ADD)

    def draw_floor(self, surf: pygame.Surface) -> None:
        """场地下方的环境阴影；网格只由平台绘制，避免双层重影。"""
        x0, y0 = self.to_screen(0, TOP_ROW)
        x1, y1 = self.to_screen(COLS, TOP_ROW)
        x2, y2 = self.to_screen(COLS, ROWS)
        x3, y3 = self.to_screen(0, ROWS)
        tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        poly = [(x0, y0 + 18), (x1, y1 + 18), (x2, y2 + 26), (x3, y3 + 26)]
        for spread in range(28, 2, -4):
            center_x = sum(p[0] for p in poly) / 4
            center_y = sum(p[1] for p in poly) / 4
            factor = 1.0 + spread / 240.0
            expanded = [(center_x + (x - center_x) * factor,
                         center_y + (y - center_y) * factor) for x, y in poly]
            pygame.draw.polygon(tmp, (0, 0, 12, 3), expanded)
        surf.blit(tmp, (0, 0))

    def draw_platform(self, surf: pygame.Surface) -> None:
        """悬浮平台：半透明厚板 + 顶面网格"""
        x0, y0 = self.to_screen(0, TOP_ROW)
        x1, y1 = self.to_screen(COLS, TOP_ROW)
        x2, y2 = self.to_screen(COLS, ROWS)
        x3, y3 = self.to_screen(0, ROWS)
        # 加一圈外扩
        e = 0.6
        x0, y0 = self.to_screen(-e, TOP_ROW - e)
        x1, y1 = self.to_screen(COLS + e, TOP_ROW - e)
        x2, y2 = self.to_screen(COLS + e, ROWS + e)
        x3, y3 = self.to_screen(-e, ROWS + e)
        _, height_y = self._camera_factors()
        side = max(3, int(16 * height_y * self.zoom))

        tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        # 侧面（南、东）
        pygame.draw.polygon(tmp, (30, 40, 90, 200),
                            [(x1, y1), (x2, y2), (x2, y2 + side), (x1, y1 + side)])
        pygame.draw.polygon(tmp, (40, 52, 110, 200),
                            [(x2, y2), (x3, y3), (x3, y3 + side), (x2, y2 + side)])
        # 顶面
        pygame.draw.polygon(tmp, (46, 60, 128, 170),
                            [(x0, y0), (x1, y1), (x2, y2), (x3, y3)])
        # 顶面网格
        for c in range(COLS + 1):
            a = self.to_screen(c, TOP_ROW - e)
            b = self.to_screen(c, ROWS + e)
            pygame.draw.aaline(tmp, (150, 180, 255, GRID_ALPHA + 24), a, b)
        for r in range(TOP_ROW - 1, ROWS + 1):
            a = self.to_screen(-e, r)
            b = self.to_screen(COLS + e, r)
            pygame.draw.aaline(tmp, (150, 180, 255, GRID_ALPHA + 24), a, b)
        # 边框高光
        pygame.draw.aalines(tmp, (190, 212, 255, 105), True,
                            [(x0, y0), (x1, y1), (x2, y2), (x3, y3)])
        surf.blit(tmp, (0, 0))

    # ------------------------------------------------------------ 粒子
    def draw_particles(self, surf: pygame.Surface, particles: list) -> None:
        for p in particles:
            a = max(0, min(255, int(255 * p["life"] / p["t0"])))
            size = max(2, int(p["size"] * (0.6 + 0.4 * p["life"] / p["t0"])))
            col = p["color"]
            tmp = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (*col, a), (size + 2, size + 2), size)
            surf.blit(tmp, (p["x"] - size - 2, p["y"] - size - 2),
                      special_flags=pygame.BLEND_ADD)

    def draw_ring(self, surf: pygame.Surface, cx: float, cy: float,
                  radius: float, alpha: int, color: tuple[int, int, int]) -> None:
        tmp = pygame.Surface((int(radius * 2) + 8, int(radius * 2) + 8), pygame.SRCALPHA)
        pygame.draw.circle(tmp, (*color, alpha), (int(radius) + 4, int(radius) + 4),
                           int(radius), 2)
        surf.blit(tmp, (cx - radius - 4, cy - radius - 4), special_flags=pygame.BLEND_ADD)

    def piece_shadow(self, surf: pygame.Surface, c: float, r: float, w: int, h: int) -> None:
        """活动方块在落点处的软阴影"""
        cx, cy = self.to_screen(c + w / 2, r + h / 2)
        tmp = pygame.Surface((112, 46), pygame.SRCALPHA)
        for pad, alpha in ((2, 10), (7, 14), (12, 18)):
            pygame.draw.ellipse(tmp, (0, 0, 8, alpha),
                                (pad, pad // 2, 112 - pad * 2, 40 - pad))
        surf.blit(tmp, (cx - 56, cy + CUBE_H * self.zoom * 0.45 - 23))


def make_particles_for_clear(renderer: Renderer, cells: list[tuple[int, int]],
                             color: tuple[int, int, int], rng: random.Random,
                             burst: int = 8) -> list[dict]:
    pts = []
    for c, r in cells:
        cx, cy = renderer.to_screen(c + 0.5, r + 0.5)
        for _ in range(burst):
            ang = rng.uniform(0, math.tau)
            spd = rng.uniform(1.5, 7.0)
            pts.append({
                "x": cx + rng.uniform(-8, 8),
                "y": cy + rng.uniform(-10, 4),
                "vx": math.cos(ang) * spd,
                "vy": math.sin(ang) * spd - 2.0,
                "life": rng.uniform(0.45, 0.95),
                "t0": 0.9,
                "size": rng.uniform(2, 5),
                "color": color,
            })
    return pts


def update_particles(particles: list, dt: float) -> None:
    for p in particles:
        p["life"] -= dt
        p["x"] += p["vx"] * 60 * dt
        p["y"] += p["vy"] * 60 * dt
        p["vy"] += 0.12 * 60 * dt
    particles[:] = [p for p in particles if p["life"] > 0]


# ---------------------------------------------------------------- 背景主题
_W, _H = 1280, 800


def _bg_base(surf: pygame.Surface, top: tuple, bot: tuple) -> None:
    """垂直渐变基座（整块覆盖，防残影）"""
    for y in range(0, _H, 4):
        t = y / _H
        c = (int(top[0] + (bot[0] - top[0]) * t),
             int(top[1] + (bot[1] - top[1]) * t),
             int(top[2] + (bot[2] - top[2]) * t))
        pygame.draw.rect(surf, c, (0, y, _W, 4))


def _bg_blit(surf: pygame.Surface, s: pygame.Surface, x: int, y: int) -> None:
    surf.blit(s, (x, y))


def _stars(surf: pygame.Surface, rng: random.Random, n: int, a_max: int = 150,
           y_span: tuple[int, int] = (0, 500)) -> None:
    tmp = pygame.Surface((_W, _H), pygame.SRCALPHA)
    for _ in range(n):
        x = rng.uniform(0, _W)
        y = rng.uniform(*y_span)
        a = rng.randint(30, a_max)
        r = rng.choice((1, 1, 2))
        pygame.draw.circle(tmp, (255, 255, 255, a), (int(x), int(y)), r)
    surf.blit(tmp, (0, 0))


def _nebula_blob(surf: pygame.Surface, cx: float, cy: float, r: float,
                 color: tuple[int, int, int], a: int) -> None:
    tmp = pygame.Surface((int(r * 2) + 4, int(r * 2) + 4), pygame.SRCALPHA)
    for i in range(int(r), 0, -1):
        alpha = int(a * (1 - i / r) ** 2)
        pygame.draw.circle(tmp, (*color, alpha), (int(r) + 2, int(r) + 2), i)
    surf.blit(tmp, (int(cx - r), int(cy - r)))


def draw_bg_theme(surf: pygame.Surface, theme: str, t: float,
                  custom_bg: pygame.Surface | None = None, rng: random.Random | None = None) -> None:
    """按主题绘制全屏背景。t：动画时间（秒）；custom_bg：自定义图片表面"""
    rng = rng or random.Random(7)
    if theme == "custom" and custom_bg is not None:
        surf.blit(custom_bg, (0, 0))
        tmp = pygame.Surface((_W, _H), pygame.SRCALPHA)
        pygame.draw.rect(tmp, (4, 6, 16, 130), (0, 0, _W, _H))
        surf.blit(tmp, (0, 0))
        return
    if theme == "nebula":
        _bg_base(surf, (22, 12, 58), (6, 6, 22))
        _nebula_blob(surf, 250 + 30 * math.sin(t * 0.2), 180, 240, (120, 40, 220), 40)
        _nebula_blob(surf, 1020 + 24 * math.sin(t * 0.15 + 2), 220, 280, (30, 60, 200), 42)
        _nebula_blob(surf, 640, 90, 180, (200, 60, 120), 26)
        _stars(surf, rng, 130)
        return
    if theme == "city":
        _bg_base(surf, (10, 14, 44), (4, 5, 18))
        _stars(surf, rng, 70, a_max=90, y_span=(0, 320))
        # 城市剪影：两排建筑 + 霓虹窗点
        tmp = pygame.Surface((_W, _H), pygame.SRCALPHA)
        r2 = random.Random(11)
        horizon = 560
        for row in range(2):
            base_y = horizon + row * 90
            x = -20
            while x < _W:
                w = r2.randint(50, 120)
                h = r2.randint(60, 150) if row == 0 else r2.randint(110, 210)
                col = (12, 16, 40, 235) if row == 0 else (6, 8, 26, 235)
                pygame.draw.rect(tmp, col, (x, base_y - h, w, h + 20))
                for wx in range(x + 8, x + w - 8, 16):
                    for wy in range(base_y - h + 8, base_y - 6, 18):
                        if r2.random() < 0.30:
                            pygame.draw.rect(tmp, (255, 200, 80, 150), (wx, wy, 5, 7))
                x += w + r2.randint(6, 24)
        surf.blit(tmp, (0, 0))
        return
    if theme == "aurora":
        _bg_base(surf, (8, 16, 40), (4, 6, 20))
        _stars(surf, rng, 110, a_max=120)
        tmp = pygame.Surface((_W, _H), pygame.SRCALPHA)
        for k, (col, base_y, amp) in enumerate([
                ((60, 255, 160, 26), 120, 46), ((120, 120, 255, 22), 180, 62),
                ((255, 120, 200, 16), 60, 40)]):
            pts = []
            for x in range(-40, _W + 40, 40):
                y = base_y + amp * math.sin((x + k * 120) * 0.012 + t * 0.6 + k)
                pts.append((x, y))
            for i in range(len(pts) - 1):
                x1, y1 = pts[i]
                x2, y2 = pts[i + 1]
                pygame.draw.line(tmp, col, (x1, y1), (x2, y2), 8)
        surf.blit(tmp, (0, 0), special_flags=pygame.BLEND_ADD)
        return
    if theme == "grid":
        _bg_base(surf, (8, 10, 30), (4, 5, 16))
        tmp = pygame.Surface((_W, _H), pygame.SRCALPHA)
        cx, cy = _W // 2, 420
        for i in range(12):
            r = 90 + i * 55
            a = max(0, int(70 * (1 - i / 12)))
            pygame.draw.ellipse(tmp, (0, 180, 255, a), (cx - r, cy - r * 0.4, r * 2, r * 0.8), 1)
        for y in range(0, 8):
            yy = cy + y * 60
            a = max(0, int(60 * (1 - y / 8)))
            pygame.draw.line(tmp, (90, 130, 255, a), (0, yy), (_W, yy), 1)
        surf.blit(tmp, (0, 0))
        _stars(surf, rng, 60, a_max=80)
        return
    # default：深蓝霓虹（由 game.draw_background 绘制渐变与尘埃）
