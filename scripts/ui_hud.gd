class_name GameHUD
extends CanvasLayer
## 对局 HUD：分数/行数/时间/速度/目标 + 下一块与暂存预览

var main = null
var _font: Font = null

var label_score: Label
var label_lines: Label
var label_time: Label
var label_pps: Label
var label_level: Label
var label_mode: Label
var label_target: Label
var label_combo: Label
var next_preview: PreviewBox
var hold_preview: PreviewBox
var panel: Panel


class PreviewBox extends Control:
	var cells: Array = []
	var color := Color(1, 1, 1)
	var cell_px := 18.0

	func _init(w: float = 100.0, h: float = 100.0) -> void:
		custom_minimum_size = Vector2(w, h)
		size = Vector2(w, h)
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func set_preview(c: Array, col: Color) -> void:
		cells = c
		color = col
		queue_redraw()

	func _draw() -> void:
		if cells.is_empty():
			return
		var min_x := 99
		var min_y := 99
		for cell in cells:
			min_x = mini(min_x, cell.x)
			min_y = mini(min_y, cell.y)
		var ox := (size.x - 4 * cell_px) * 0.5 + 2
		var oy := (size.y - 2 * cell_px) * 0.5 + 2
		for cell in cells:
			var x: float = ox + (cell.x - min_x) * cell_px
			var y: float = oy + (cell.y - min_y) * cell_px
			var rect := Rect2(x, y, cell_px - 2, cell_px - 2)
			draw_rect(rect, color, true)
			draw_rect(rect, color.lightened(0.45), false, 1.5)


func _init(m: Node, font: Font) -> void:
	main = m
	_font = font
	layer = 10
	_build()


func _build() -> void:
	panel = Panel.new()
	panel.anchor_left = 0.0
	panel.anchor_top = 0.0
	panel.anchor_right = 1.0
	panel.anchor_bottom = 1.0
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.02, 0.03, 0.09, 0.55)
	sb.set_corner_radius_all(0)
	panel.add_theme_stylebox_override("panel", sb)
	add_child(panel)

	var font_size := 22
	label_mode = _mk_label(Vector2(24, 18), 28, "竞速 40 行")
	label_score = _mk_label(Vector2(24, 60), 40, "0")
	label_lines = _mk_label(Vector2(24, 112), 24, "行数 0 / 40")
	label_time = _mk_label(Vector2(24, 150), 24, "0.00 秒")
	label_pps = _mk_label(Vector2(24, 188), 20, "PPS 0.00")
	label_level = _mk_label(Vector2(24, 220), 20, "等级 1")
	label_combo = _mk_label(Vector2(24, 252), 26, "")

	var panel_right := Panel.new()
	panel_right.position = Vector2(1280 - 210, 18)
	panel_right.size = Vector2(190, 250)
	panel_right.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var rb := StyleBoxFlat.new()
	rb.bg_color = Color(0.08, 0.10, 0.22, 0.75)
	rb.border_color = Color(0.4, 0.5, 1.0, 0.4)
	rb.set_border_width_all(1)
	rb.set_corner_radius_all(8)
	panel_right.add_theme_stylebox_override("panel", rb)
	add_child(panel_right)

	var t_hold := _mk_label(Vector2(1280 - 200, 30), 18, "暂存")
	var t_next := _mk_label(Vector2(1280 - 200, 140), 18, "下一个")
	hold_preview = PreviewBox.new(160, 100)
	hold_preview.position = Vector2(1280 - 195, 56)
	next_preview = PreviewBox.new(160, 100)
	next_preview.position = Vector2(1280 - 195, 168)
	add_child(hold_preview)
	add_child(next_preview)

	label_target = _mk_label(Vector2(1280 - 420, 762), 20, "目标：最快消 40 行")
	label_target.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT


func _mk_label(pos: Vector2, sz: int, text: String) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", _font)
	l.add_theme_font_size_override("font_size", sz)
	l.position = pos
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	l.add_theme_color_override("font_color", Color(0.92, 0.95, 1.0))
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.6))
	l.add_theme_constant_override("shadow_offset_x", 2)
	l.add_theme_constant_override("shadow_offset_y", 2)
	add_child(l)
	return l


func update_hud() -> void:
	if main == null or main.board == null:
		return
	var b = main.board
	label_score.text = str(b.score)
	var cfg: Dictionary = TetrisConstants.MODE_CFG.get(main.mode, {})
	var goal: String = cfg.get("goal", "lines")
	var target: int = cfg.get("target", 0)
	if goal == "lines":
		label_lines.text = "行数 %d / %d" % [b.lines, target]
	elif goal == "score":
		label_lines.text = "分数 %d / %d" % [b.score, target]
	elif goal == "time":
		label_lines.text = "剩余 %d 秒" % maxi(0, int(target - main.elapsed))
	else:
		label_lines.text = "行数 %d" % b.lines
	label_time.text = "%0.2f 秒" % main.elapsed
	var pps := 0.0
	if main.elapsed > 0:
		pps = b.pieces_placed / main.elapsed
	label_pps.text = "PPS %0.2f" % pps
	if main.mode == "marathon":
		label_level.text = "等级 %d" % b.level
		label_level.visible = true
	else:
		label_level.visible = false
	if b.combo >= 2:
		label_combo.text = "连击 x%d" % b.combo
		label_combo.visible = true
	else:
		label_combo.visible = false
	# 预览
	var next_names: Array = b.next_queue
	if next_names.size() > 0:
		var name: String = next_names[0]
		next_preview.set_preview(TetrisPieces.SPAWN_CELLS[name], TetrisConstants.PIECE_COLORS[name])
	if b.hold != "":
		hold_preview.set_preview(TetrisPieces.SPAWN_CELLS[b.hold], TetrisConstants.PIECE_COLORS[b.hold])
	else:
		hold_preview.set_preview([], Color.WHITE)
	label_target.text = TetrisConstants.MODE_DESC.get(main.mode, "")


func show_popup(text: String, color: Color = Color(1, 0.9, 0.4)) -> void:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", _font)
	l.add_theme_font_size_override("font_size", 34)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.8))
	l.add_theme_constant_override("shadow_offset_x", 3)
	l.add_theme_constant_override("shadow_offset_y", 3)
	l.position = Vector2(640 - 120, 360)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(l)
	var tw := create_tween()
	tw.tween_property(l, "position:y", 320.0, 1.0)
	tw.parallel().tween_property(l, "modulate:a", 0.0, 0.8).set_delay(0.7)
	tw.tween_callback(l.queue_free)


func set_visible_hud(v: bool) -> void:
	panel.visible = v
	for child in get_children():
		if child != panel:
			child.visible = v
