# -*- coding: utf-8 -*-
"""生成材质/背景展示截图"""
import os
import sys
import math

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

pygame.init()
screen = pygame.display.set_mode((1280, 800))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tetris_game.game import Game
import main as M

g = Game(screen, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_shot_records.json"))

# 素材：方块材质（对局画面）
for skin in ("crystal", "metal", "pixel", "candy", "aurora"):
    g.new_game("sprint40")
    g.countdown = 0.0
    g.state = "playing"
    g.renderer.set_skin(skin)
    M._fill_board_for_shot(g)
    g.update(0.4)
    g.draw()
    pygame.image.save(screen, "shot_skin_%s.png" % skin)
    print("saved shot_skin_%s.png" % skin)

# 背景主题（菜单画面）
g.state = "menu"
g.settings["skin"] = "neon"
for theme in ("nebula", "city", "aurora", "grid"):
    g.settings["bg_theme"] = theme
    g.bg_time = 12.0
    g.draw()
    pygame.image.save(screen, "shot_bg_%s.png" % theme)
    print("saved shot_bg_%s.png" % theme)

# 自定义背景图（生成一张示例图并上传）
demo = pygame.Surface((1600, 1000))
demo.fill((20, 30, 60))
for x in range(0, 1600, 80):
    pygame.draw.line(demo, (90, 160, 255, 90), (x, 0), (x + 300, 1000), 2)
    pygame.draw.line(demo, (255, 120, 180, 60), (x + 40, 0), (x + 340, 1000), 1)
pygame.draw.circle(demo, (255, 220, 120), (1300, 220), 90)
demo = demo.convert()
bg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo_bg.jpg")
pygame.image.save(demo, bg_path)
g.settings["bg_theme"] = "custom"
g.settings["custom_bg"] = bg_path
g.renderer.load_custom_bg(bg_path)
g.new_game("sprint40")
g.countdown = 0.0
g.state = "playing"
M._fill_board_for_shot(g)
g.update(0.4)
g.draw()
pygame.image.save(screen, "shot_custom_bg.png")
print("saved shot_custom_bg.png")
print("demo_bg ->", bg_path)
pygame.quit()
