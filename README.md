# TETRIS 3D RUSH — 现代竞速俄罗斯方块（UE5）

用 Unreal Engine 5（C++）实现的现代竞速俄罗斯方块。参考 Techmino 的玩法设计，但完全独立实现：UI 原创、3D 程序化场地、360° 自由视角。**不是 Techmino 的移植或克隆。**

> 引擎：UE 5.8（C++） · 平台：Windows · 纯 C++（无蓝图依赖，程序化网格渲染）

## 特性

- **伪 3D 立体场地**：方块以 3D 立体块渲染（程序化网格 + 顶点色），棋盘在空间中立体呈现
- **360° 自由视角**：鼠标拖拽旋转视角、滚轮缩放、`C` 一键复位、`V` 正面视角，全程可转
- **7 种竞速模式**：
  1. 竞速 40 行（Sprint 40L）
  2. 竞速 100 行（Sprint 100L）
  3. 马拉松（Marathon）
  4. 极速（1 秒重力）
  5. 超极速（0.5 秒重力）
  6. 大爆炸（开局中央实心块）
  7. 耐力赛（40 秒内看谁行数多）
- **6 套方块材质**（皮肤）：经典 / 霓虹 / 糖果 / 金属 / 幽灵 / 极光，各 8 色
- **5+ 种背景主题**：太空 / 赛博城市 / 极光 / 网格 / 深海 —— 且**支持上传自定义背景图**（`U` 键或设置里选择图片文件）
- **现代规则**：7-bag 随机、SRS 旋转系统、暂存（Hold）、软降/硬降、踢墙、T-spin 识别、连击
- **键位重绑**：设置菜单里可自由改键
- **音效**：程序化合成（无需外部音频文件）
- **设置与纪录持久化**：`settings.ini` / `records.ini`

## 下载

> **Windows 版打包 exe 见右侧 Releases（或下文 GitHub Release 直链）**，下载 zip 解压后运行 `Tetris3D.exe` 即可。

- 最新 Release：https://github.com/T720Dsh/Tetris/releases/latest

## 操作

| 动作 | 默认键 |
|------|--------|
| 左移 / 右移 | `←` `→` |
| 软降 | `↓` |
| 硬降 | `空格` |
| 旋转（左/右） | `Z` / `X`（可改键） |
| 180° 旋转 | `C`（视角复位）/ 180 旋转为 `A` |
| 暂存 | `Shift` |
| 视角拖拽 | 鼠标左键拖拽 |
| 缩放 | 滚轮 |
| 复位视角 | `C` |
| 正面视角 | `V` |
| 自定义背景 | `U` 选择图片 |
| 暂停 / 返回 | `Esc` |

## 从源码构建

1. 安装 **UE 5.8**（Epic Games Launcher）
2. 右键 `Tetris3D.uproject` → Generate Visual Studio project files（或直接用引擎 Build.bat）
3. 构建 Target：`Tetris3DEditor`（编辑器）/ `Tetris3D`（打包）
4. 打包：`RunUAT BuildCookRun -project=<路径>\Tetris3D.uproject -platform=Win64 -clientconfig=Development -cook -stage -pak -archive -archivedirectory=<输出目录>`

> 本项目未使用任何第三方付费资产；全部网格、材质、音效由代码程序化生成。

## 版本历史

- **v1.3+（UE5 重制版）**：改用 Unreal Engine 5 C++ 重写，3D 立体场地、360° 视角、6 皮肤、7 模式、自定义背景上传
- **v1.x（pygame 版）**：Python 原型（渲染不达要求，已弃）
- **v2.0.0（旧 Godot 版）**：早期 Web/Godot 版本（已由 UE5 版取代）

## 许可

个人学习/娱乐项目，欢迎 fork 与二创。
