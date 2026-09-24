"""生成新模式展示截图：主菜单 / 奶酪突击 / 限时 120 秒"""
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
from tetris_game.constants import PIECE_COLORS, ROWS
from tetris_game.renderer import make_particles_for_clear
from tests.test_smoke import ai_best_move

screen = pygame.display.set_mode((1280, 800))
outdir = os.path.dirname(os.path.abspath(__file__))


def play_ai(g, n):
    for _ in range(n):
        if g.state != "playing":
            break
        b = g.board
        move = ai_best_move(b)
        if move is None:
            break
        rot, x = move
        p = b.piece
        p.rot = rot
        p.x = x
        g.on_key_down(pygame.K_SPACE, 0)
        g.on_key_up(pygame.K_SPACE)
        for _ in range(3):
            g.update(1 / 60)


# 主菜单
g = Game(screen, os.path.join(outdir, "_shot_records.json"))
g.draw()
pygame.image.save(screen, os.path.join(outdir, "shot_menu.png"))
print("shot_menu.png")

# 奶酪突击：AI 玩 26 块后注入特效
g.rng = random.Random(20260924)
g.new_game("cheese40")
g.update(4.0)
play_ai(g, 26)
if g.state == "playing":
    rng = random.Random(5)
    for r in (18, 19):
        if any((c, r) in g.board.grid for c in range(10)):
            g.flash_rows.append((r, 0.2))
            g.particles += make_particles_for_clear(g.renderer,
                                                    [(c, r) for c in range(10)],
                                                    PIECE_COLORS["S"], rng, burst=8)
    g.shake = 8
g.draw()
pygame.image.save(screen, os.path.join(outdir, "shot_cheese.png"))
print("shot_cheese.png  state:", g.state, "lines:", g.board.lines)

# 限时 120 秒：AI 玩 18 块
g.rng = random.Random(7)
g.new_game("blitz120")
g.update(4.0)
play_ai(g, 18)
g.draw()
pygame.image.save(screen, os.path.join(outdir, "shot_blitz.png"))
print("shot_blitz.png  state:", g.state, "lines:", g.board.lines)
pygame.quit()
