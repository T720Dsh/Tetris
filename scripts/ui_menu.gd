class_name GameMenu
extends CanvasLayer
## 主菜单 / 设置面板 / 结算面板

var main = null
var _font: Font = null
var menu_root: Control
var settings_root: Control
var over_root: Control
var _mode_buttons: Array[Button] = []
var _skin_buttons: Array[Button] = []
var _bg_buttons: Array[Button] = []
var _speed_buttons: Array[Button] = []
var _toggle_labels: Dictionary = {}
var _rebind_labels: Dictionary = {}

const BG_BTN_COLORS := {
	"default": Color(0.12, 0.18, 0.45), "nebula": Color(0.25, 0.10, 0.45),
	"city": Color(0.08, 0.10, 0.25), "aurora": Color(0.05, 0.28, 0.32),
	"grid": Color(0.08, 0.15, 0.30), "custom": Color(0.20, 0.12, 0.10),
}


func _init(m: Node, font: Font) -> void:
	main = m
	_font = font
	layer = 20
	_build_menu()
	_build_settings()
	_build_over()
	show_menu()


# ------------------------------------------------------------ 组件工厂
func _mk_label(pos: Vector2, sz: int, text: String, parent: Control, color: Color = Color(0.92, 0.95, 1.0)) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", _font)
	l.add_theme_font_size_override("font_size", sz)
	l.position = pos
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	l.add_theme_color_override("font_color", color)
	parent.add_child(l)
	return l


func _mk_button(pos: Vector2, size: Vector2, text: String, parent: Control, font_size := 18) -> Button:
	var b := Button.new()
	b.text = text
	b.position = pos
	b.size = size
	b.add_theme_font_override("font", _font)
	b.add_theme_font_size_override("font_size", font_size)
	b.add_theme_color_override("font_hover_color", Color(0.2, 0.6, 1.0))
	b.add_theme_color_override("font_pressed_color", Color(1.0, 0.9, 0.5))
	b.add_theme_color_override("font_focus_color", Color(0.9, 0.95, 1.0))
	b.add_theme_color_override("font_color", Color(0.85, 0.9, 1.0))
	var nb := StyleBoxFlat.new()
	nb.bg_color = Color(0.10, 0.13, 0.28)
	nb.border_color = Color(0.35, 0.45, 0.9, 0.6)
	nb.set_border_width_all(1)
	nb.set_corner_radius_all(6)
	b.add_theme_stylebox_override("normal", nb)
	var hb := StyleBoxFlat.new()
	hb.bg_color = Color(0.16, 0.22, 0.42)
	hb.border_color = Color(0.6, 0.7, 1.0)
	hb.set_border_width_all(1)
	hb.set_corner_radius_all(6)
	b.add_theme_stylebox_override("hover", hb)
	var pb := StyleBoxFlat.new()
	pb.bg_color = Color(0.22, 0.30, 0.55)
	pb.border_color = Color(1.0, 0.9, 0.5)
	pb.set_border_width_all(1)
	pb.set_corner_radius_all(6)
	b.add_theme_stylebox_override("pressed", pb)
	b.add_theme_stylebox_override("focus", hb)
	parent.add_child(b)
	return b


func _mk_panel(pos: Vector2, size: Vector2, parent: Control, alpha := 0.8) -> Panel:
	var p := Panel.new()
	p.position = pos
	p.size = size
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.04, 0.06, 0.14, alpha)
	sb.border_color = Color(0.3, 0.4, 0.85, 0.5)
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(10)
	p.add_theme_stylebox_override("panel", sb)
	parent.add_child(p)
	return p


# ------------------------------------------------------------ 主菜单
func _build_menu() -> void:
	menu_root = Control.new()
	add_child(menu_root)

	var panel := _mk_panel(Vector2(70, 40), Vector2(520, 742), menu_root)
	_mk_label(Vector2(95, 62), 42, "TETRIS 3D RUSH", menu_root)
	_mk_label(Vector2(98, 116), 18, "现代竞速方块 · 伪 3D 立体场地 · 360° 自由视角", menu_root, Color(0.6, 0.7, 0.95))

	var y := 156
	for mode in TetrisConstants.MODES:
		var cfg: Dictionary = TetrisConstants.MODE_CFG[mode]
		var name: String = TetrisConstants.MODE_NAME[mode]
		var rec: String = "纪录 " + Settings.record_text(mode)
		var b := _mk_button(Vector2(95, y), Vector2(470, 56), "", menu_root)
		b.text = "%s\n%s" % [name, rec]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.add_theme_constant_override("outline_size", 0)
		b.pressed.connect(main.start_game.bind(mode))
		_mode_buttons.append(b)
		y += 60

	var hint := _mk_label(Vector2(95, y + 10), 14, "", menu_root, Color(0.55, 0.62, 0.85))
	hint.text = "操作：←→ 移动 · ↑ 旋转 · ↓ 软降 · 空格 硬降 · C 暂存 · Q/E 视角\n鼠标拖拽旋转 · ESC 暂停 · R 重开 · V 复位视角 · F 正面视角"
	hint.size = Vector2(470, 52)
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART

	var set_btn := _mk_button(Vector2(95, y + 64), Vector2(230, 44), "设置", menu_root)
	set_btn.pressed.connect(_open_settings)
	var quit_btn := _mk_button(Vector2(335, y + 64), Vector2(230, 44), "退出", menu_root)
	quit_btn.pressed.connect(func(): main.quit_game())


# ------------------------------------------------------------ 设置
func _build_settings() -> void:
	settings_root = Control.new()
	settings_root.visible = false
	add_child(settings_root)
	var panel := _mk_panel(Vector2(80, 40), Vector2(1120, 720), settings_root)

	_mk_label(Vector2(110, 60), 32, "设置", settings_root)

	# 皮肤
	_mk_label(Vector2(110, 112), 20, "方块材质", settings_root, Color(0.6, 0.7, 0.95))
	var x := 110
	for skin in TetrisConstants.SKIN_ORDER:
		var cfg: Dictionary = TetrisConstants.SKINS[skin]
		var b := _mk_button(Vector2(x, 140), Vector2(120, 40), cfg["name"], settings_root, 16)
		b.pressed.connect(main.set_skin.bind(skin))
		_skin_buttons.append(b)
		x += 128
	_update_skin_marks()

	# 背景
	_mk_label(Vector2(110, 202), 20, "背景主题", settings_root, Color(0.6, 0.7, 0.95))
	x = 110
	for theme in TetrisConstants.BG_THEMES:
		var b := _mk_button(Vector2(x, 230), Vector2(120, 40), TetrisConstants.BG_THEME_NAME[theme], settings_root, 16)
		b.pressed.connect(main.set_bg_theme.bind(theme))
		_bg_buttons.append(b)
		x += 128
	_update_bg_marks()

	# 自定义背景
	var up_btn := _mk_button(Vector2(110, 282), Vector2(260, 42), "上传自定义背景图…", settings_root, 16)
	up_btn.pressed.connect(main.upload_custom_bg)
	var clear_btn := _mk_button(Vector2(380, 282), Vector2(200, 42), "清除自定义背景", settings_root, 16)
	clear_btn.pressed.connect(main.clear_custom_bg)

	# 重力速度
	_mk_label(Vector2(110, 350), 20, "重力速度", settings_root, Color(0.6, 0.7, 0.95))
	x = 110
	for key in TetrisConstants.GRAVITY_SPEEDS:
		var b := _mk_button(Vector2(x, 378), Vector2(100, 40), TetrisConstants.GRAVITY_NAMES[key], settings_root, 16)
		b.pressed.connect(main.set_gravity_speed.bind(key))
		_speed_buttons.append(b)
		x += 108
	_update_speed_marks()

	# 开关
	_toggle_labels["ghost"] = _mk_toggle(Vector2(110, 440), "幽灵块", settings_root, main.toggle_ghost)
	_toggle_labels["sound"] = _mk_toggle(Vector2(390, 440), "音效", settings_root, main.toggle_sound)
	_toggle_labels["fullscreen"] = _mk_toggle(Vector2(670, 440), "全屏", settings_root, main.toggle_fullscreen)
	_update_toggle_marks()

	# 键位重绑
	_mk_label(Vector2(110, 500), 20, "键位重绑（点击后按下新按键）", settings_root, Color(0.6, 0.7, 0.95))
	var kx := 110
	var ky := 530
	for action in TetrisConstants.KEYBIND_LABELS:
		var b := _mk_button(Vector2(kx, ky), Vector2(180, 34), "", settings_root, 15)
		b.pressed.connect(main.begin_rebind.bind(action, b))
		_rebind_labels[action] = b
		kx += 188
		if kx > 1050:
			kx = 110
			ky += 42
	_update_rebind_labels()

	# 返回
	var back := _mk_button(Vector2(110, 700), Vector2(200, 44), "返回主菜单", settings_root)
	back.pressed.connect(_back_to_menu)


func _mk_toggle(pos: Vector2, text: String, parent: Control, cb: Callable) -> Button:
	var b := _mk_button(pos, Vector2(160, 40), "", parent, 16)
	b.pressed.connect(cb)
	return b


func _update_skin_marks() -> void:
	for i in range(_skin_buttons.size()):
		_skin_buttons[i].text = TetrisConstants.SKINS[TetrisConstants.SKIN_ORDER[i]]["name"] + \
			(" ✓" if Settings.settings["skin"] == TetrisConstants.SKIN_ORDER[i] else "")


func _update_bg_marks() -> void:
	for i in range(_bg_buttons.size()):
		_bg_buttons[i].text = TetrisConstants.BG_THEME_NAME[TetrisConstants.BG_THEMES[i]] + \
			(" ✓" if Settings.settings["bg_theme"] == TetrisConstants.BG_THEMES[i] else "")


func _update_speed_marks() -> void:
	var keys: Array = TetrisConstants.GRAVITY_SPEEDS.keys()
	keys.sort()
	for i in range(_speed_buttons.size()):
		_speed_buttons[i].text = TetrisConstants.GRAVITY_NAMES[keys[i]] + \
			(" ✓" if Settings.settings["gravity_speed"] == keys[i] else "")


func _update_toggle_marks() -> void:
	for key in _toggle_labels:
		var b: Button = _toggle_labels[key]
		b.text = "%s：%s" % [key.capitalize(), "开" if Settings.settings[key] else "关"]


func _update_rebind_labels() -> void:
	for action in _rebind_labels:
		var b: Button = _rebind_labels[action]
		var key: int = Settings.settings["keybinds"].get(action, TetrisConstants.DEFAULT_KEYBINDS[action])
		b.text = "%s  [%s]" % [TetrisConstants.KEYBIND_LABELS[action], _key_name(key)]


static func _key_name(key: int) -> String:
	match key:
		KEY_LEFT: return "←"
		KEY_RIGHT: return "→"
		KEY_UP: return "↑"
		KEY_DOWN: return "↓"
		KEY_SPACE: return "空格"
		KEY_ESCAPE: return "ESC"
		_: return OS.get_keycode_string(key)


func refresh_marks() -> void:
	_update_skin_marks()
	_update_bg_marks()
	_update_speed_marks()
	_update_toggle_marks()
	_update_rebind_labels()


func _open_settings() -> void:
	menu_root.visible = false
	settings_root.visible = true
	refresh_marks()


func _back_to_menu() -> void:
	settings_root.visible = false
	menu_root.visible = true


# ------------------------------------------------------------ 结算
func _build_over() -> void:
	over_root = Control.new()
	over_root.visible = false
	add_child(over_root)
	_mk_panel(Vector2(390, 180), Vector2(500, 440), over_root, 0.92)
	_mk_label(Vector2(420, 210), 40, "结算", over_root)
	var lines := [
		"得分：%d",
		"消行：%d",
		"用时：%0.2f 秒",
		"方块数：%d",
	]
	var y := 280
	for i in range(lines.size()):
		var l := _mk_label(Vector2(420, y), 24, lines[i], over_root)
		l.name = "over_line_%d" % i
		y += 40
	var record_l := _mk_label(Vector2(420, y + 8), 24, "", over_root, Color(1.0, 0.85, 0.3))
	record_l.name = "over_record"
	record_l.visible = false

	var again := _mk_button(Vector2(420, y + 60), Vector2(220, 44), "再来一次", over_root)
	again.pressed.connect(main.restart)
	var menu_btn := _mk_button(Vector2(650, y + 60), Vector2(220, 44), "返回主菜单", over_root)
	menu_btn.pressed.connect(main.to_menu)


func show_over(result: Dictionary) -> void:
	over_root.visible = true
	var b = result["board"]
	var lines := [
		"得分：%d" % b.score,
		"消行：%d" % b.lines,
		"用时：%0.2f 秒" % result["elapsed"],
		"方块数：%d" % b.pieces_placed,
	]
	for i in range(lines.size()):
		over_root.get_node("over_line_%d" % i).text = lines[i]
	var rl: Label = over_root.get_node("over_record")
	rl.visible = result.get("is_record", false)
	if rl.visible:
		var cfg: Dictionary = TetrisConstants.MODE_CFG.get(main.mode, {})
		var kind: String = cfg.get("record", "time")
		if kind == "time":
			rl.text = "★ 新纪录：%0.2f 秒 ★" % result["elapsed"]
		else:
			rl.text = "★ 新纪录：%d 分 ★" % b.score


func show_menu() -> void:
	menu_root.visible = true
	settings_root.visible = false
	over_root.visible = false


func set_ui_visible(menu: bool, settings: bool, over: bool) -> void:
	menu_root.visible = menu
	settings_root.visible = settings
	over_root.visible = over
