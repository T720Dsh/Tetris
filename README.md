# TETRIS 3D RUSH — 现代竞速俄罗斯方块（UE5）

一个以 **竞速** 为核心的现代俄罗斯方块游戏：伪 3D 立体场地、360° 自由视角、多模式、多材质、自定义背景。由 **Unreal Engine 5.8 (C++)** 从零实现，不依赖 Techmino 代码，UI 完全独立设计。

> 玩法规则参考经典竞速方块（7-bag 随机、SRS 踢墙、Hold、Ghost），但场地是 3D 的，视角可以自由旋转——在 3D 里玩俄罗斯方块，别有一番乐趣。

---

## 🎮 下载 Windows 版

点右侧 **Releases**（或下面的链接）下载 Windows 版本压缩包，解压后双击 `Tetris3D.exe` 即可游玩，无需安装、无需联网。

- **最新版下载**：https://github.com/T720Dsh/Tetris/releases/latest
- 直接下载 zip：`https://github.com/T720Dsh/Tetris/releases/download/v3.0.0/Tetris3DRush-win64.zip`

> 系统要求：Windows 10/11 64 位，独立显卡优先（集成显卡也可运行）。

---

## ✨ 特性

| 类别 | 内容 |
|---|---|
| 竞速模式 | 7 种：竞速20行 / 竞速40行 / 马拉松 / 限时2分钟 / 限时5分钟 / 冲刺40行 / 极速死亡 |
| 3D 场地 | 立体方块堆叠场地，下落/消除全部在 3D 空间呈现 |
| 360° 视角 | 鼠标拖拽自由旋转视角、滚轮缩放、Q/E 左右转、V 复位、F 正面视角 |
| 方块材质 | 6 套皮肤：经典 / 糖果 / 霓虹 / 冰晶 / 金属 / 像素 |
| 背景主题 | 5+ 主题：深空 / 都市 / 极光 / 网格 / 海洋，还支持**自定义上传背景图** |
| 键位重绑 | 设置菜单内可重新绑定全部操作键位 |
| 音效 | 运行时合成的复古合成器音效（可开关） |
| 数据 | 每种模式独立最高分记录（本地存档） |

## 🕹️ 操作

| 按键 | 功能 |
|---|---|
| ← → | 左右移动 |
| ↑ | 顺时针旋转 |
| ↓ | 软降 |
| 空格 | 硬降 |
| C | 暂存（Hold） |
| 鼠标拖拽 | 旋转 3D 视角 |
| 滚轮 | 缩放视角 |
| Q / E | 视角左右旋转 |
| V | 视角复位 |
| F | 回到正面视角 |
| ESC | 暂停 |
| R | 重开 |
| 设置菜单 | 可重绑所有键位 |

---

## 🛠️ 从源码构建

需要 **Unreal Engine 5.8**（含 C++ 工具链）与 Visual Studio Build Tools（含 C++ 桌面开发）。

```bat
:: 1. 生成项目文件（右键 Tetris3D.uproject → Generate Visual Studio project files）
:: 2. 编译 Game target：
D:\Epic\UE_5.8\Engine\Build\BatchFiles\Build.bat Tetris3D Win64 Development -Project=D:\UE_Tetris3D\Tetris3D.uproject

:: 3. 打包（Cook + BuildCookRun）：
D:\Epic\UE_5.8\Engine\Build\BatchFiles\RunUAT.bat BuildCookRun -project=D:\UE_Tetris3D\Tetris3D.uproject -noP4 -platform=Win64 -clientconfig=Development -build -stage -pak -archive -archivedirectory=<输出目录>
```

## 📁 项目结构

```
Source/Tetris3D/
├─ TetrisTypes.h        # 模式/皮肤/主题枚举、7-bag、SRS 踢墙、重力表
├─ TetrisCore.h/.cpp    # 纯逻辑：方块、旋转、踢墙、消行、暂存、胜负判定
├─ TetrisGameMode.h/.cpp# 游戏状态机、设置/记录持久化（settings.ini / records.ini）
├─ TetrisBoardActor.h/.cpp # 程序化 3D 网格、轨道相机、输入、音效、背景
├─ TetrisHUD.h/.cpp     # Canvas 全 UI（中文）
└─ Tetris3D.Target.cs / Tetris3DEditor.Target.cs
```

## 📜 版本历史

- **v3.0.0**（当前）— UE5 完全重做：3D 场地渲染、360° 视角、6 皮肤、5 主题 + 自定义背景、7 竞速模式、键位重绑、合成音效。
- v2.0.0 — Godot 原型版（已归档）。
