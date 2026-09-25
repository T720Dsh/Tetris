extends Node
## 主控：组装场景、状态机、输入（DAS/ARR）、更新渲染、设置应用

var state := "menu"          # menu / countdown / playing / paused / over
var mode := "sprint40"
var board: TetrisBoard = null
var bag: TetrisPieces.Bag7 = null
var rng := RandomNumberGenerator.new()

var board3d: Board3D
var camera: CameraRig
var bg: Background3D
var hud: GameHUD
var menu: GameMenu
var font: Font

var elapsed := 0.0
var countdown := 0.0
var game_started := false   # 结算区分完成/失败
var finished := false

# 输入状态
var das_acc := 0.0
var arr_acc := 0.0
var soft_acc := 0.0
var last_move_dir := 0

# 重绑
var rebind_action := ""
var rebind_button: Button = null

# 音效
var sfx: Dictionary = {}
var audio_player: AudioStreamPlayer
var music_bus := "Master"


func _ready() -> void:
	font = SystemFont.new()
	font.font_names = PackedStringArray(["Microsoft YaHei", "微软雅黑", "Segoe UI", "sans-serif"])

	bg = Background3D.new()
	add_child(bg)
	board3d = Board3D.new()
	add_child(board3d)
	camera = CameraRig.new()
	add_child(camera)
	_setup_lights()
	_setup_audio()

	hud = GameHUD.new(self, font)
	add_child(hud)
	menu = GameMenu.new(self, font)
	add_child(menu)

	apply_settings()
	to_menu()
	rng.randomize()

	var autoplay := OS.get_environment("TETRIS_AUTO_PLAY")
	if autoplay != "":
		_autoplay(autoplay.to_float())

	var shot := OS.get_environment("TETRIS_SHOT")
	if shot != "":
		_auto_shot(shot)

	var shot2 := OS.get_environment("TETRIS_SHOT2")
	if shot2 != "":
		var auto_mode: String = OS.get_environment("TETRIS_AUTO_MODE")
		start_game(auto_mode if auto_mode != "" else "sprint40")
		for i in range(14):
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var img2 := get_viewport().get_texture().get_image()
		img2.save_png(shot2)
		print("SHOT_SAVED ", shot2)


# 调试：自动对局冒烟（模拟键盘输入，验证输入链路）
func _autoplay(seconds: float) -> void:
	start_game("sprint40")
	var steps := int(seconds * 60.0)
	for i in range(steps):
		await get_tree().process_frame
		if i == 82:
			board.try_rotate(1)
		elif i == 88:
			board.try_move(-1, 0)
		elif i == 92:
			board.try_move(1, 0)
		elif i == 96:
			board.hard_drop()
			board.lock()
			_on_lock_event(board.last_event)
		elif i == 108:
			board.do_hold()
		elif i == 118:
			board.try_rotate(-1)
			board.try_move(-1, 0)
			_render()
		if i % 30 == 0:
			print("AUTOPLAY frame ", i, " pieces=", board.pieces_placed if board != null else -1,
				" lines=", board.lines if board != null else -1)
	print("AUTOPLAY DONE pieces=", board.pieces_placed if board != null else -1,
		" lines=", board.lines if board != null else -1)
	to_menu()


func _auto_shot(path: String) -> void:
	for i in range(6):
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(path)
	print("SHOT_SAVED ", path)


func _setup_lights() -> void:
	var dir := DirectionalLight3D.new()
	dir.rotation_degrees = Vector3(-55, -35, 0)
	dir.light_energy = 1.4
	dir.light_color = Color(0.9, 0.95, 1.0)
	dir.shadow_enabled = false
	add_child(dir)
	var omni := OmniLight3D.new()
	omni.position = Vector3(0, 14, -14)
	omni.light_energy = 1.0
	omni.light_color = Color(0.5, 0.6, 1.0)
	omni.omni_range = 40.0
	add_child(omni)


# ------------------------------------------------------------ 音频
func _setup_audio() -> void:
	audio_player = AudioStreamPlayer.new()
	add_child(audio_player)
	sfx["move"] = _make_tone([660.0], 0.045, 0.25)
	sfx["rotate"] = _make_tone([740.0, 880.0], 0.06, 0.3)
	sfx["drop"] = _make_tone([220.0], 0.09, 0.4)
	sfx["lock"] = _make_tone([330.0, 294.0], 0.08, 0.35)
	sfx["clear"] = _make_tone([523.0, 659.0, 784.0, 1047.0], 0.22, 0.4)
	sfx["combo"] = _make_tone([659.0, 880.0], 0.14, 0.4)
	sfx["hold"] = _make_tone([440.0, 392.0], 0.08, 0.3)
	sfx["over"] = _make_tone([196.0, 147.0, 98.0], 0.5, 0.45)
	sfx["win"] = _make_tone([523.0, 659.0, 784.0, 1047.0, 1319.0], 0.6, 0.4)


func _make_tone(freqs: Array, dur: float, vol: float) -> AudioStreamWAV:
	var rate := 22050
	var frames := int(dur * rate)
	var data := PackedByteArray()
	data.resize(frames * 2)
	for i in range(frames):
		var t := float(i) / rate
		var env := exp(-3.0 * t / maxf(dur, 0.001)) * vol
		var sample := 0.0
		for j in range(freqs.size()):
			var f: float = freqs[j]
			sample += sin(TAU * f * t) * (1.0 / (j + 1))
		sample = sample / freqs.size()
		var v := int(clampf(sample * env, -1.0, 1.0) * 32000.0)
		data[i * 2] = v & 0xFF
		data[i * 2 + 1] = (v >> 8) & 0xFF
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = rate
	wav.stereo = false
	wav.data = data
	return wav


func play_sfx(name: String) -> void:
	if not Settings.settings.get("sound", true):
		return
	if sfx.has(name):
		audio_player.stream = sfx[name]
		audio_player.volume_db = linear_to_db(Settings.settings.get("volume", 0.7))
		audio_player.play()


# ------------------------------------------------------------ 状态流程
func to_menu() -> void:
	state = "menu"
	board = null
	elapsed = 0.0
	countdown = 0.0
	board3d.rebuild_from([], [], [])
	menu.show_menu()
	hud.set_visible_hud(false)
	camera.auto_rotate = true


func start_game(p_mode: String) -> void:
	mode = p_mode
	board = TetrisBoard.new(mode)
	bag = TetrisPieces.Bag7.new(rng.randi())
	board.bag = bag
	rng.randomize()
	var seed_rng := RandomNumberGenerator.new()
	seed_rng.seed = rng.randi()
	board.seed_garbage(TetrisConstants.MODE_CFG[mode].get("garbage", 0), seed_rng)
	board.spawn()
	board.refill_next()

	state = "countdown"
	countdown = 1.2
	elapsed = 0.0
	game_started = false
	finished = false
	das_acc = 0.0
	arr_acc = 0.0
	soft_acc = 0.0
	last_move_dir = 0
	menu.set_ui_visible(false, false, false)
	hud.set_visible_hud(true)
	hud.update_hud()
	camera.auto_rotate = false
	_render()


func restart() -> void:
	start_game(mode)


func quit_game() -> void:
	get_tree().quit()


func toggle_pause() -> void:
	if state == "playing":
		state = "paused"
	elif state == "paused":
		state = "playing"


func finish_game(win: bool) -> void:
	if finished:
		return
	finished = true
	state = "over"
	finished_win = win
	var is_record := false
	var cfg: Dictionary = TetrisConstants.MODE_CFG.get(mode, {})
	if win and not cfg.is_empty():
		var kind: String = cfg["record"]
		var val := elapsed if kind == "time" else float(board.score)
		is_record = Settings.submit_record(mode, val)
		play_sfx("win")
	else:
		play_sfx("over")
	menu.show_over({"board": board, "elapsed": elapsed, "is_record": is_record})


var finished_win := false


# ------------------------------------------------------------ 设置应用
func apply_settings() -> void:
	board3d.apply_skin(Settings.settings.get("skin", "luminous"))
	var t: String = Settings.settings.get("bg_theme", "default")
	if t == "custom":
		var path: String = Settings.settings.get("custom_bg", "")
		if path != "" and FileAccess.file_exists(path):
			var img := Image.load_from_file(path)
			if img != null:
				var tex := ImageTexture.create_from_image(img)
				bg.apply_theme("default")
				bg.set_custom_texture(tex)
			else:
				Settings.settings["bg_theme"] = "default"
				bg.apply_theme("default")
		else:
			bg.apply_theme("default")
	else:
		bg.clear_custom_texture()
		bg.apply_theme(t)
	# 重力
	var gs: String = Settings.settings.get("gravity_speed", "very_slow")
	if board != null:
		board.gravity_scale_override = TetrisConstants.GRAVITY_SPEEDS.get(gs, 0.15)
	# 全屏
	var fs: bool = Settings.settings.get("fullscreen", false)
	var is_fs: bool = DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN
	if fs != is_fs:
		if fs:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
		else:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	apply_keybinds()
	if menu != null:
		menu.refresh_marks()
	if hud != null:
		hud.update_hud()


func apply_keybinds() -> void:
	for action in TetrisConstants.DEFAULT_KEYBINDS:
		var key: int = Settings.settings["keybinds"].get(action, TetrisConstants.DEFAULT_KEYBINDS[action])
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		InputMap.action_erase_events(action)
		var ev := InputEventKey.new()
		ev.physical_keycode = key
		InputMap.action_add_event(action, ev)


func set_skin(skin_name: String) -> void:
	Settings.settings["skin"] = skin_name
	board3d.apply_skin(skin_name)
	Settings.save_settings()
	menu.refresh_marks()


func set_bg_theme(t: String) -> void:
	Settings.settings["bg_theme"] = t
	bg.clear_custom_texture()
	bg.apply_theme(t)
	Settings.save_settings()
	menu.refresh_marks()


func set_gravity_speed(key: String) -> void:
	Settings.settings["gravity_speed"] = key
	if board != null:
		board.gravity_scale_override = TetrisConstants.GRAVITY_SPEEDS.get(key, 0.15)
	Settings.save_settings()
	menu.refresh_marks()


func toggle_ghost() -> void:
	Settings.settings["ghost"] = not Settings.settings.get("ghost", true)
	Settings.save_settings()
	menu.refresh_marks()


func toggle_sound() -> void:
	Settings.settings["sound"] = not Settings.settings.get("sound", true)
	Settings.save_settings()
	menu.refresh_marks()


func toggle_fullscreen() -> void:
	var fs: bool = not Settings.settings.get("fullscreen", false)
	Settings.settings["fullscreen"] = fs
	if fs:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	else:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	Settings.save_settings()
	menu.refresh_marks()


func upload_custom_bg() -> void:
	var fd := FileDialog.new()
	fd.title = "选择背景图片"
	fd.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	fd.access = FileDialog.ACCESS_FILESYSTEM
	fd.filters = PackedStringArray(["*.png ; PNG 图片", "*.jpg ; JPG 图片", "*.jpeg ; JPEG 图片", "*.bmp ; BMP 图片"])
	fd.size = Vector2i(800, 560)
	add_child(fd)
	fd.file_selected.connect(func(path: String):
		Settings.settings["custom_bg"] = path
		Settings.settings["bg_theme"] = "custom"
		var img := Image.load_from_file(path)
		if img != null:
			var tex := ImageTexture.create_from_image(img)
			bg.apply_theme("default")
			bg.set_custom_texture(tex)
		Settings.save_settings()
		menu.refresh_marks())
	fd.popup_centered()


func clear_custom_bg() -> void:
	Settings.settings["custom_bg"] = ""
	Settings.settings["bg_theme"] = "default"
	bg.clear_custom_texture()
	bg.apply_theme("default")
	Settings.save_settings()
	menu.refresh_marks()


func begin_rebind(action: String, btn: Button) -> void:
	rebind_action = action
	rebind_button = btn
	btn.text = "按下新按键…"


func _finish_rebind(event: InputEventKey) -> void:
	if rebind_action == "":
		return
	var key := event.physical_keycode
	if key == KEY_ESCAPE:
		rebind_action = ""
		rebind_button = null
		menu.refresh_marks()
		return
	Settings.settings["keybinds"][rebind_action] = key
	Settings.save_settings()
	apply_keybinds()
	rebind_action = ""
	rebind_button = null
	menu.refresh_marks()


# ------------------------------------------------------------ 输入
func _unhandled_input(event: InputEvent) -> void:
	if rebind_action != "" and event is InputEventKey and event.pressed:
		_finish_rebind(event)
		get_viewport().set_input_as_handled()
		return

	if event is InputEventMouseButton:
		camera.handle_mouse_button(event)
		if state == "playing" and event.button_index == MOUSE_BUTTON_LEFT:
			get_viewport().set_input_as_handled()
		return
	if event is InputEventMouseMotion:
		camera.handle_mouse_motion(event)
		return

	if state != "playing":
		return
	# 游戏按键统一在 _process 查询 Input 状态（见 _handle_just_pressed）


func _try_rotate(dir: int) -> void:
	if board.try_rotate(dir):
		play_sfx("rotate")
		if board.piece.grounded:
			board.reset_lock()
		_render()


# ------------------------------------------------------------ 更新
func _process(delta: float) -> void:
	if state == "countdown":
		countdown -= delta
		if countdown <= 0.0:
			state = "playing"
			game_started = true
			board.update(maxf(delta, 0.001))
		return
	if state == "playing":
		elapsed += delta
		_handle_just_pressed()
		_handle_move_input(delta)
		_handle_soft_drop(delta)
		var before := board.pieces_placed
		board.update(delta)
		if board.pieces_placed != before and not board.game_over:
			_on_lock_event(board.last_event)
		_check_end()
		_render()
		hud.update_hud()
	elif state == "paused":
		pass


func _handle_just_pressed() -> void:
	if Input.is_action_just_pressed("rotate_cw"):
		_try_rotate(1)
	elif Input.is_action_just_pressed("rotate_ccw"):
		_try_rotate(-1)
	elif Input.is_action_just_pressed("rotate_180"):
		_try_rotate(2)
	elif Input.is_action_just_pressed("hard_drop"):
		if board.hard_drop() > 0:
			play_sfx("drop")
		board.lock()
		play_sfx("lock")
		_on_lock_event(board.last_event)
	elif Input.is_action_just_pressed("hold"):
		if board.do_hold():
			play_sfx("hold")
			_render()
	elif Input.is_action_just_pressed("pause"):
		toggle_pause()
	elif Input.is_action_just_pressed("restart"):
		restart()
	elif Input.is_action_just_pressed("view_left"):
		camera.rotate_by(-0.6)
	elif Input.is_action_just_pressed("view_right"):
		camera.rotate_by(0.6)
	elif Input.is_action_just_pressed("view_reset"):
		camera.reset_view()
	elif Input.is_action_just_pressed("view_front"):
		camera.front_view()


func _handle_move_input(delta: float) -> void:
	var dir := 0
	if Input.is_action_pressed("move_left"):
		dir = -1
	elif Input.is_action_pressed("move_right"):
		dir = 1
	if dir != last_move_dir:
		last_move_dir = dir
		das_acc = 0.0
		arr_acc = 0.0
		if dir != 0:
			if board.try_move(dir, 0):
				play_sfx("move")
			_render()
	if dir != 0:
		das_acc += delta
		if das_acc >= TetrisConstants.DAS:
			arr_acc += delta
			while arr_acc >= TetrisConstants.ARR:
				if board.try_move(dir, 0):
					_render()
				arr_acc -= TetrisConstants.ARR


func _handle_soft_drop(delta: float) -> void:
	if not Input.is_action_pressed("soft_drop"):
		soft_acc = 0.0
		return
	soft_acc += delta
	while soft_acc >= TetrisConstants.SOFT_DROP_SEC:
		if not board.soft_drop_step():
			break
		soft_acc -= TetrisConstants.SOFT_DROP_SEC
	if board.piece.grounded:
		board.reset_lock()


func _on_lock_event(ev: Dictionary) -> void:
	if ev.is_empty():
		return
	var rows: Array = ev.get("rows", [])
	if rows.size() > 0:
		play_sfx("combo" if ev.get("combo", 0) >= 2 else "clear")
		var label := "+%d" % ev.get("score", 0)
		if ev.get("tspin", null) != null:
			label = "T-SPIN %s +%d" % [ev["tspin"].capitalize(), ev.get("score", 0)]
		if ev.get("perfect", false):
			label += " 全清!"
		hud.show_popup(label, Color(1, 0.85, 0.4) if ev.get("combo", 0) < 3 else Color(1, 0.6, 0.3))
	_render()


func _check_end() -> void:
	if board.game_over:
		finish_game(false)
		return
	var cfg: Dictionary = TetrisConstants.MODE_CFG.get(mode, {})
	if cfg.is_empty():
		return
	var goal: String = cfg["goal"]
	if goal == "lines" or goal == "score":
		if board.goal_met():
			finish_game(true)
	elif goal == "time":
		if elapsed >= cfg["target"]:
			finish_game(true)


# ------------------------------------------------------------ 渲染
func _render() -> void:
	if board == null:
		board3d.rebuild_from([], [], [])
		return
	var cfg: Dictionary = TetrisConstants.SKINS.get(board3d.skin, TetrisConstants.SKINS["luminous"])
	var top_f: float = cfg["top"]
	var mid_f: float = cfg["mid"]
	var low_f: float = cfg["low"]

	var fixed: Array = []
	for key in board.grid:
		var name: String = board.grid[key]
		var base: Color = TetrisConstants.PIECE_COLORS[name]
		fixed.append({
			"pos": board3d.cell_world(key.x, key.y),
			"col_top": board3d.skin_color(base, top_f),
			"col_bottom": board3d.skin_color(base, low_f),
			"col_nz": board3d.skin_color(base, low_f),
			"col_pz": board3d.skin_color(base, mid_f),
		})

	var ghost: Array = []
	var active: Array = []
	if not board.piece.is_empty() and state in ["playing", "countdown"]:
		var p: Dictionary = board.piece
		var name: String = p.name
		var base: Color = TetrisConstants.PIECE_COLORS[name]
		# 活动块
		for c in TetrisPieces.cells_for(name, p.rot):
			var gx: int = p.x + c.x
			var gy: int = p.y + c.y
			if gy < -TetrisConstants.HIDDEN_TOP:
				continue
			active.append({
				"pos": board3d.cell_world(gx, gy),
				"col_top": board3d.skin_color(base, top_f),
				"col_bottom": board3d.skin_color(base, low_f),
				"col_nz": board3d.skin_color(base, low_f),
				"col_pz": board3d.skin_color(base, mid_f),
			})
		# 幽灵（仅设置开启且着地位置不同）
		if Settings.settings.get("ghost", true) and state == "playing":
			var d := board.drop_distance()
			if d > 0:
				for c in TetrisPieces.cells_for(name, p.rot):
					var gx2: int = p.x + c.x
					var gy2: int = p.y + c.y + d
					if gy2 < -TetrisConstants.HIDDEN_TOP:
						continue
					ghost.append({
						"pos": board3d.cell_world(gx2, gy2),
						"col_top": base,
						"col_bottom": base,
						"col_nz": base,
						"col_pz": base,
					})

	board3d.rebuild_from(fixed, ghost, active)
