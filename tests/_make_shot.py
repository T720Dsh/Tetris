"""生成最终展示截图：随机游玩数秒 + 注入消行粒子，展示伪 3D 与特效"""
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
from tetris_game.constants import PIECE_COLORS
from tetris_game.renderer import make_particles_for_clear
from tests.test_smoke import ai_best_move

screen = pygame.display.set_mode((1280, 800))
g = Game(screen, os.path.join(os.path.dirname(__file__), "_shot_records.json"))
g.rng = random.Random(20260924)
g.new_game("sprint40")
g.update(4.0)

# 贪心 AI 摆放 38 块，保持版面整洁（输入硬降走真实链路）
for i in range(38):
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

if g.state == "playing":
    # 注入一波消行粒子与弹窗，展示特效
    rng = random.Random(5)
    for r in (18, 19):
        g.flash_rows.append((r, 0.2))
        g.particles += make_particles_for_clear(g.renderer,
                                                [(c, r) for c in range(10)],
                                                PIECE_COLORS["T"], rng, burst=10)
    g.rings.append({"x": g.renderer.to_screen(5, 18.5)[0], "y": g.renderer.to_screen(5, 18.5)[1],
                    "r": 10, "t": 0.0, "dur": 0.4, "color": PIECE_COLORS["I"]})
    g.popups.append({"text": "TETRIS! +800", "color": (0, 230, 118),
                     "x": g.renderer.to_screen(7, 18)[0], "y": g.renderer.to_screen(7, 18)[1],
                     "t": 0.0, "dur": 0.9})
    g.shake = 10
    g.combo_banner = 1.0

g.draw()
pygame.image.save(screen, os.path.join(os.path.dirname(__file__), "screenshot.png"))
print("saved screenshot.png  state:", g.state, "lines:", g.board.lines)
pygame.quit()
