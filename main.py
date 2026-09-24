"""TETRIS 3D RUSH — 伪 3D 竞速俄罗斯方块 · 入口
用法：
    python main.py                正常启动
    python main.py --shot out.png 无窗口渲染一帧截图（测试用）
"""
from __future__ import annotations
import os
import sys


class DisplayManager:
    """Keep the game on a fixed logical canvas while the OS window can resize."""

    def __init__(self, pygame, width: int, height: int, headless: bool = False):
        self.pygame = pygame
        self.logical_size = (width, height)
        self.headless = headless
        self.fullscreen = False
        self.windowed_size = (width, height)
        flags = 0 if headless else pygame.RESIZABLE
        self.window = pygame.display.set_mode(self.logical_size, flags)
        self.canvas = self.window if headless else pygame.Surface(self.logical_size)

    def toggle_fullscreen(self, enabled: bool | None = None) -> bool:
        if self.headless:
            return False
        target = (not self.fullscreen) if enabled is None else bool(enabled)
        if target == self.fullscreen:
            return self.fullscreen
        if target:
            self.windowed_size = self.window.get_size()
            self.window = self.pygame.display.set_mode((0, 0), self.pygame.FULLSCREEN)
        else:
            self.window = self.pygame.display.set_mode(self.windowed_size, self.pygame.RESIZABLE)
        self.fullscreen = target
        return self.fullscreen

    def to_logical(self, pos: tuple[int, int]) -> tuple[int, int]:
        if self.headless:
            return pos
        ww, wh = self.window.get_size()
        lw, lh = self.logical_size
        scale = min(ww / lw, wh / lh)
        ox = (ww - lw * scale) / 2
        oy = (wh - lh * scale) / 2
        return (int((pos[0] - ox) / scale), int((pos[1] - oy) / scale))

    def present(self) -> None:
        if self.headless:
            self.pygame.display.flip()
            return
        ww, wh = self.window.get_size()
        lw, lh = self.logical_size
        scale = min(ww / lw, wh / lh)
        size = (max(1, round(lw * scale)), max(1, round(lh * scale)))
        frame = (self.canvas if size == self.logical_size
                 else self.pygame.transform.smoothscale(self.canvas, size))
        self.window.fill((3, 5, 14))
        self.window.blit(frame, ((ww - size[0]) // 2, (wh - size[1]) // 2))
        self.pygame.display.flip()


def main() -> int:
    import pygame

    headless = "--shot" in sys.argv
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    pygame.init()
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except Exception:
        pass

    from tetris_game.constants import WIN_W, WIN_H, TITLE
    from tetris_game.game import Game

    display = DisplayManager(pygame, WIN_W, WIN_H, headless)
    pygame.display.set_caption(TITLE)

    records_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "records.json")
    game = Game(display.canvas, records_path, fullscreen_toggle=display.toggle_fullscreen)
    if not headless and game.settings.get("fullscreen"):
        game.set_fullscreen_state(display.toggle_fullscreen(True))

    if headless:
        # 构造一张有内容的场地用于截图
        idx = sys.argv.index("--shot")
        out = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "shot.png"
        _fill_board_for_shot(game)
        game.draw()
        pygame.image.save(display.canvas, out)
        print("saved:", out)
        pygame.quit()
        return 0

    clock = pygame.time.Clock()
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                fullscreen_shortcut = (event.key == pygame.K_F11 or
                                       (event.key == pygame.K_RETURN and
                                        event.mod & pygame.KMOD_ALT))
                if fullscreen_shortcut:
                    game.set_fullscreen_state(display.toggle_fullscreen())
                elif event.key == pygame.K_ESCAPE and display.fullscreen:
                    game.set_fullscreen_state(display.toggle_fullscreen(False))
                else:
                    game.on_key_down(event.key, event.mod)
            elif event.type == pygame.KEYUP:
                game.on_key_up(event.key)
            elif event.type == pygame.MOUSEMOTION:
                pos = display.to_logical(event.pos)
                game.handle_hover(pos)
                game.drag_move(pos)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (1, 3):
                    pos = display.to_logical(event.pos)
                    game.drag_start(pos)
                    game.handle_click(pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                game.drag_end()
            elif event.type == pygame.WINDOWFOCUSLOST:
                if game.state == "playing":
                    game.state = "paused"

        game.update(dt)
        game.draw()
        display.present()

    pygame.quit()
    return 0


def _fill_board_for_shot(game) -> None:
    """截图辅助：直接进入对局并堆一些方块，展示伪 3D 效果"""
    from tetris_game.constants import COLS
    game.new_game("sprint40")
    game.state = "playing"
    b = game.board
    if b is None:
        return
    layout = [
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
        "...ZZ.....",
        "..SSZZ....",
        "..SSZJ....",
        ".LLIIJJ...",
        ".LLIIJJO..",
        ".OOIIJJOO.",
        "OTTOIILLOO",
        "TTTOIISSLL",
        ".TTOOIILLL",
    ]
    names = {"Z": "Z", "S": "S", "J": "J", "L": "L", "I": "I", "O": "O", "T": "T"}
    for r, line in enumerate(layout):
        for c, ch in enumerate(line):
            if ch in names:
                b.grid[(c, r)] = names[ch]
    # 模拟一个正在下落的 T 块
    from tetris_game.board import Piece
    b.piece = Piece("T", 4, 9, 0)
    b.piece.rotated = True
    b.next_queue = ["I", "O", "S", "Z", "J"]


if __name__ == "__main__":
    sys.exit(main())
