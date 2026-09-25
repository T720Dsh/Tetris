class_name CameraRig
extends Node3D
## 360° 自由轨道相机：鼠标拖拽旋转 / 滚轮缩放 / Q/E 旋转 / V 复位 / F 正面

var yaw := -0.65
var pitch := 0.55
var dist := TetrisConstants.VIEW_DIST_DEFAULT
var sensitivity := TetrisConstants.VIEW_SENSITIVITY_DEFAULT

var _target := Vector3(0.0, 10.5, 0.0)
var _camera: Camera3D

# 拖拽状态
var _dragging := false
var _last_mouse := Vector2.ZERO

# 自动旋转（无操作时缓慢转动）
var auto_rotate := true


func _init() -> void:
	_camera = Camera3D.new()
	_camera.fov = 60.0
	_camera.near = 0.2
	_camera.far = 400.0
	_camera.current = true
	add_child(_camera)
	update_view()


func update_view() -> void:
	var cp := Vector3(
		cos(pitch) * sin(yaw),
		sin(pitch),
		cos(pitch) * cos(yaw)
	)
	_camera.position = _target + cp * dist
	_camera.look_at_from_position(_camera.position, _target, Vector3.UP)


func handle_mouse_motion(event: InputEventMouseMotion) -> void:
	if _dragging:
		var dx := event.relative.x / 1000.0
		var dy := event.relative.y / 1000.0
		yaw -= dx * (2.2 * sensitivity * 100.0 / 800.0) * 1.0
		pitch -= dy * (2.2 * sensitivity * 100.0 / 800.0) * 1.0
		pitch = clampf(pitch, -0.15, 1.45)
		update_view()
		_break_auto()


func handle_mouse_button(event: InputEventMouseButton) -> void:
	if event.button_index == MOUSE_BUTTON_LEFT:
		_dragging = event.pressed
		if _dragging:
			_last_mouse = event.position
		_break_auto()
	elif event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
		dist = clampf(dist - 1.2, TetrisConstants.VIEW_DIST_MIN, TetrisConstants.VIEW_DIST_MAX)
		update_view()
		_break_auto()
	elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
		dist = clampf(dist + 1.2, TetrisConstants.VIEW_DIST_MIN, TetrisConstants.VIEW_DIST_MAX)
		update_view()
		_break_auto()


func rotate_by(angle: float) -> void:
	yaw += angle
	update_view()
	_break_auto()


func reset_view() -> void:
	yaw = -0.65
	pitch = 0.55
	dist = TetrisConstants.VIEW_DIST_DEFAULT
	update_view()
	_break_auto()


func front_view() -> void:
	yaw = 0.0
	pitch = 0.55
	update_view()
	_break_auto()


func _break_auto() -> void:
	auto_rotate = false


func _process(delta: float) -> void:
	if auto_rotate:
		yaw += delta * 0.08
		update_view()
