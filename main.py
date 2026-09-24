"""TETRIS 3D RUSH — 伪 3D 竞速俄罗斯方块 · 入口
用法：
    python main.py                正常启动
    python main.py --shot out.png 无窗口渲染一帧截图（测试用）
"""
from __future__ import annotations
import os
import sys


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

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption(TITLE)

    records_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "records.json")
    game = Game(screen, records_path)

    if headless:
        # 构造一张有内容的场地用于截图
        idx = sys.argv.index("--shot")
        out = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "shot.png"
        _fill_board_for_shot(game)
        game.draw()
        pygame.image.save(screen, out)
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
                game.on_key_down(event.key, event.mod)
            elif event.type == pygame.KEYUP:
                game.on_key_up(event.key)
            elif event.type == pygame.MOUSEMOTION:
                game.handle_hover(event.pos)
                game.drag_move(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (1, 3):
                    game.drag_start(event.pos)
                    game.handle_click(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                game.drag_end()
            elif event.type == pygame.WINDOWFOCUSLOST:
                if game.state == "playing":
                    game.state = "paused"

        game.update(dt)
        game.draw()
        pygame.display.flip()

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
