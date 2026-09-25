"""TETRIS 3D RUSH — 伪 3D 竞速俄罗斯方块 · 入口
用法：
    python main.py                正常启动
    python main.py --shot out.png 无窗口渲染一帧截图（测试用）
"""
from __future__ import annotations
import os
import shutil
import sys


class DisplayManager:
    """Keep the game on a fixed logical canvas while the OS window can resize."""

    def __init__(self, pygame, width: int, height: int, headless: bool = False):
        self.pygame = pygame
        self.logical_size = (width, height)
        self.headless = headless
        self.fullscreen = False
        self.windowed_size = (width, height)
        self.hardware_scaled = False
        if headless:
            self.window = pygame.display.set_mode(self.logical_size)
        else:
            try:
                self.window = pygame.display.set_mode(
                    self.logical_size, pygame.RESIZABLE | pygame.SCALED, vsync=1)
                self.hardware_scaled = True
            except pygame.error:
                self.window = pygame.display.set_mode(self.logical_size, pygame.RESIZABLE)
        self.canvas = self.window if headless else pygame.Surface(self.logical_size)

    def toggle_fullscreen(self, enabled: bool | None = None) -> bool:
        if self.headless:
            return False
        target = (not self.fullscreen) if enabled is None else bool(enabled)
        if target == self.fullscreen:
            return self.fullscreen
        if self.hardware_scaled:
            # SDL's scaled renderer preserves the logical 1280x800 surface,
            # performs the final resize on the GPU and maps mouse input back to
            # logical coordinates.  pygame documents this as its reliable
            # Windows fullscreen toggle path.
            try:
                result = self.pygame.display.toggle_fullscreen()
                if result == 0:
                    self.window = self.pygame.display.get_surface()
                    self.fullscreen = target
                    return self.fullscreen
            except pygame.error:
                pass
            try:
                flags = self.pygame.SCALED | (self.pygame.FULLSCREEN
                                               if target else self.pygame.RESIZABLE)
                self.window = self.pygame.display.set_mode(self.logical_size, flags, vsync=1)
                self.fullscreen = target
                return self.fullscreen
            except pygame.error:
                self.hardware_scaled = False
        if target:
            self.windowed_size = (self.pygame.display.get_window_size()
                                  if hasattr(self.pygame.display, "get_window_size")
                                  else self.window.get_size())
            self.window = self.pygame.display.set_mode((0, 0), self.pygame.FULLSCREEN)
        else:
            self.window = self.pygame.display.set_mode(self.windowed_size, self.pygame.RESIZABLE)
        self.fullscreen = target
        return self.fullscreen

    def to_logical(self, pos: tuple[int, int]) -> tuple[int, int]:
        if self.headless:
            return pos
        if self.hardware_scaled:
            return pos  # SCALED remaps mouse events for us.
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
        if self.hardware_scaled:
            self.window.blit(self.canvas, (0, 0))
            self.pygame.display.flip()
            return
        ww, wh = self.window.get_size()
        lw, lh = self.logical_size
        scale = min(ww / lw, wh / lh)
        size = (max(1, round(lw * scale)), max(1, round(lh * scale)))
        if size == self.logical_size:
            frame = self.canvas
        elif scale > 1.0:
            # A pure nearest-neighbour resize made diagonal playfield edges and
            # Chinese glyphs visibly stair-step at common non-integer fullscreen
            # scales (for example 1.35x on a 1080p 16:9 display).  Blend a
            # filtered enlargement with a light crisp pass: the former supplies
            # sub-pixel coverage, the latter prevents the whole UI looking soft.
            frame = self.pygame.transform.smoothscale(self.canvas, size)
            crisp = self.pygame.transform.scale(self.canvas, size)
            crisp.set_alpha(46)
            frame.blit(crisp, (0, 0))
        else:
            frame = self.pygame.transform.smoothscale(self.canvas, size)
        self.window.fill((3, 5, 14))
        self.window.blit(frame, ((ww - size[0]) // 2, (wh - size[1]) // 2))
        self.pygame.display.flip()


def main() -> int:
    headless = "--shot" in sys.argv
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    else:
        # Pygame's "photo" mode requests anisotropic filtering, which is useful
        # for photos but visibly softens small UI glyphs.  Linear GPU filtering
        # keeps non-integer fullscreen scaling smooth without that extra blur.
        os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "linear")

    import pygame

    pygame.init()
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except Exception:
        pass

    from tetris_game.constants import WIN_W, WIN_H, TITLE
    from tetris_game.game import Game

    display = DisplayManager(pygame, WIN_W, WIN_H, headless)
    pygame.display.set_caption(TITLE)

    if getattr(sys, "frozen", False):
        # Downloads and Program Files can be read-only or protected by Windows.
        # Keep mutable state in the per-user app-data directory and migrate the
        # older beside-the-exe files once so existing records/keybinds survive.
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        app_dir = os.path.join(os.environ.get("LOCALAPPDATA", exe_dir), "Tetris3DRush")
        os.makedirs(app_dir, exist_ok=True)
        for filename in ("records.json", "settings.json"):
            legacy = os.path.join(exe_dir, filename)
            current = os.path.join(app_dir, filename)
            if not os.path.exists(current) and os.path.isfile(legacy):
                try:
                    shutil.copy2(legacy, current)
                except OSError:
                    pass
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    records_path = os.path.join(app_dir, "records.json")
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
                capturing_key = (game.state == "keybinds" and
                                 game.binding_capture is not None)
                if capturing_key:
                    game.on_key_down(event.key, event.mod)
                elif fullscreen_shortcut:
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
                if event.button == 1:
                    pos = display.to_logical(event.pos)
                    game.drag_start(pos)
                    game.handle_click(pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                game.drag_end()
            elif event.type == pygame.WINDOWFOCUSLOST:
                game.drag_end()
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
