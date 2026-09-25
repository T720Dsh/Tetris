"""UI：字体、面板、按钮、HUD、菜单绘制"""
from __future__ import annotations
import os

import pygame

from .constants import (WIN_W, WIN_H, TEXT_MAIN, TEXT_DIM, ACCENT, ACCENT2,
                        PANEL_FILL, PANEL_BORDER, DANGER, GOOD, MODE_NAME,
                        MODE_DESC)

FONT_REGULAR_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]
FONT_BOLD_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
]


class Fonts:
    def __init__(self):
        self.regular = next((p for p in FONT_REGULAR_CANDIDATES if os.path.exists(p)), None)
        self.bold = next((p for p in FONT_BOLD_CANDIDATES if os.path.exists(p)), self.regular)
        self._cache: dict[tuple[str, int], pygame.font.Font] = {}

    def get(self, size: int, bold: bool = False) -> pygame.font.Font:
        family = self.bold if bold else self.regular
        key = (f"{family}|{bold}", size)
        if key not in self._cache:
            if family:
                f = pygame.font.Font(family, size)
            else:
                f = pygame.font.Font(None, size)
                f.set_bold(bold)
            self._cache[key] = f
        return self._cache[key]


# ---------------------------------------------------------------- 基础绘制
def panel(surf: pygame.Surface, rect: pygame.Rect, fill=PANEL_FILL,
          border=PANEL_BORDER, radius: int = 14) -> None:
    # Local surface keeps the many HUD/preview cards cheap enough for 60 fps.
    tmp = pygame.Surface((rect.width, rect.height + 9), pygame.SRCALPHA)
    local = pygame.Rect(0, 0, rect.width, rect.height)
    shadow = local.move(0, 7)
    pygame.draw.rect(tmp, (0, 0, 8, 85), shadow, border_radius=radius + 2)
    pygame.draw.rect(tmp, fill, local, border_radius=radius)
    pygame.draw.rect(tmp, border, local, width=1, border_radius=radius)
    inner = local.inflate(-4, -4)
    pygame.draw.rect(tmp, (255, 255, 255, 14), inner, width=1, border_radius=max(2, radius - 2))
    surf.blit(tmp, rect.topleft)


def text(surf: pygame.Surface, fonts: Fonts, s: str, size: int, pos: tuple[int, int],
         color=TEXT_MAIN, anchor: str = "topleft", bold: bool = False,
         shadow: bool = False, alpha: int = 255) -> pygame.Rect:
    f = fonts.get(size, bold)
    img = f.render(s, True, color)
    if alpha < 255:
        img.set_alpha(alpha)
    r = img.get_rect()
    setattr(r, anchor, pos)
    if shadow:
        sh = f.render(s, True, (0, 0, 0))
        surf.blit(sh, (r.x + 2, r.y + 2))
    surf.blit(img, r)
    return r


def format_time(sec: float) -> str:
    ms = int(sec * 1000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{m}:{s:02d}.{ms:03d}"


# ---------------------------------------------------------------- 按钮
class Button:
    def __init__(self, rect: pygame.Rect, label: str, action: str,
                 sub: str | None = None, accent: bool = False):
        self.rect = rect
        self.label = label
        self.sub = sub
        self.action = action
        self.accent = accent
        self.hover = False

    def draw(self, surf: pygame.Surface, fonts: Fonts) -> None:
        fill = (36, 44, 88, 210) if self.accent else (26, 32, 66, 200)
        border = (ACCENT if self.accent else (120, 140, 255, 120))
        if self.hover:
            fill = (52, 62, 120, 230) if self.accent else (40, 48, 96, 220)
            border = (255, 255, 255, 200)
        panel(surf, self.rect, fill=fill, border=border, radius=12)
        if self.accent or self.hover:
            pygame.draw.rect(surf, ACCENT, (self.rect.x, self.rect.y + 10, 3,
                                            self.rect.height - 20), border_radius=2)
        y = self.rect.centery - (11 if self.sub else 0)
        text(surf, fonts, self.label, 20 if self.sub else 22, (self.rect.centerx, y),
             color=(255, 255, 255) if (self.hover or self.accent) else TEXT_MAIN,
             anchor="center")
        if self.sub:
            text(surf, fonts, self.sub, 13, (self.rect.centerx, y + 27),
                 color=TEXT_DIM, anchor="center", shadow=False)

    def hit(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


def draw_vignette(surf: pygame.Surface, strength: int, color=DANGER) -> None:
    """危险红色渐变（栈高告警）"""
    tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    w, h = surf.get_size()
    edge = 70
    for i in range(edge):
        a = int(strength * (1 - i / edge))
        pygame.draw.rect(tmp, (*color, a), (0, i, w, 1))
        pygame.draw.rect(tmp, (*color, a), (0, h - 1 - i, w, 1))
        pygame.draw.rect(tmp, (*color, a), (i, 0, 1, h))
        pygame.draw.rect(tmp, (*color, a), (w - 1 - i, 0, 1, h))
    surf.blit(tmp, (0, 0))


# ---------------------------------------------------------------- 小等距预览（暂存/下一块）
def draw_preview(surf: pygame.Surface, fonts: Fonts, title: str,
                  piece_name: str | None, center: tuple[int, int],
                  cell: int = 12, skin: dict | None = None,
                  box_size: tuple[int, int] = (180, 66)) -> None:
    """在方框内用迷你等距方块绘制预览（外观跟随当前方块皮肤）"""
    box = pygame.Rect(0, 0, *box_size)
    box.center = center
    panel(surf, box, fill=(12, 17, 38, 185), border=(105, 130, 220, 65), radius=10)
    content_center = [center[0], center[1]]
    if title:
        text(surf, fonts, title, 14, (center[0], box.top + 16),
             color=TEXT_DIM, anchor="center", shadow=False)
        content_center[1] += 10
    if not piece_name:
        return
    from .pieces import ALL_CELLS
    from .renderer import skin_face_colors
    from .constants import SKINS
    skin = skin or SKINS["neon"]
    color = PIECE_C(piece_name)
    cells = ALL_CELLS[piece_name][0]
    # 整体居中
    def project(c, r):
        return (c - r) * cell, (c + r) * cell * 0.5
    pts = [project(c, r) for c, r in cells]
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    ox = content_center[0] - cx
    oy = content_center[1] - cy + cell * 0.35

    for (c, r) in sorted(cells, key=lambda item: item[0] + item[1]):
        x0, y0 = ox + project(c, r)[0], oy + project(c, r)[1]
        x1, y1 = ox + project(c + 1, r)[0], oy + project(c + 1, r)[1]
        x2, y2 = ox + project(c + 1, r + 1)[0], oy + project(c + 1, r + 1)[1]
        x3, y3 = ox + project(c, r + 1)[0], oy + project(c, r + 1)[1]
        t = cell * 0.9
        col_top, col_east, col_south, col_edge = skin_face_colors(color, skin)
        pygame.draw.polygon(surf, col_east,
                            [(x1, y1), (x2, y2), (x2, y2 - t), (x1, y1 - t)])
        pygame.draw.polygon(surf, col_south,
                            [(x2, y2), (x3, y3), (x3, y3 - t), (x2, y2 - t)])
        pygame.draw.polygon(surf, col_top,
                            [(x0, y0 - t), (x1, y1 - t), (x2, y2 - t), (x3, y3 - t)])
        if skin.get("edge_w", 1) >= 1:
            ew = skin["edge_w"]
            pygame.draw.line(surf, col_edge, (x0, y0 - t), (x1, y1 - t), ew)
            pygame.draw.line(surf, col_edge, (x1, y1 - t), (x2, y2 - t), ew)
            pygame.draw.line(surf, col_edge, (x2, y2 - t), (x3, y3 - t), ew)
            pygame.draw.line(surf, col_edge, (x3, y3 - t), (x0, y0 - t), ew)
            pygame.draw.line(surf, col_edge, (x1, y1), (x1, y1 - t), ew)
            pygame.draw.line(surf, col_edge, (x2, y2), (x2, y2 - t), ew)
            pygame.draw.line(surf, col_edge, (x3, y3), (x3, y3 - t), ew)


def PIECE_C(name: str):
    from .constants import PIECE_COLORS
    return PIECE_COLORS[name]


def _shade(c, f):
    return (max(0, min(255, int(c[0] * f))),
            max(0, min(255, int(c[1] * f))),
            max(0, min(255, int(c[2] * f))))
