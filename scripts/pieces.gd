class_name TetrisPieces
extends RefCounted
## 方块定义、旋转生成、7-bag 随机与 SRS 踢墙表（移植自 pieces.py）

# 出生形态（旋转 0），x 向右，y 向下
const SPAWN_CELLS := {
	"I": [Vector2i(0, 1), Vector2i(1, 1), Vector2i(2, 1), Vector2i(3, 1)],
	"J": [Vector2i(0, 0), Vector2i(0, 1), Vector2i(1, 1), Vector2i(2, 1)],
	"L": [Vector2i(2, 0), Vector2i(0, 1), Vector2i(1, 1), Vector2i(2, 1)],
	"S": [Vector2i(1, 0), Vector2i(2, 0), Vector2i(0, 1), Vector2i(1, 1)],
	"T": [Vector2i(1, 0), Vector2i(0, 1), Vector2i(1, 1), Vector2i(2, 1)],
	"Z": [Vector2i(0, 0), Vector2i(1, 0), Vector2i(1, 1), Vector2i(2, 1)],
	"O": [Vector2i(1, 0), Vector2i(2, 0), Vector2i(1, 1), Vector2i(2, 1)],
}
const PIECE_NAMES: Array[String] = ["I", "J", "L", "S", "T", "Z", "O"]

# ALL_CELLS[name][rot] -> Array[Vector2i]
static var _all_cells: Dictionary = {}

static func _rot_cw(cells: Array, n: int) -> Array:
	var out: Array = []
	for c in cells:
		out.append(Vector2i(n - 1 - c.y, c.x))
	return out

static func _rot_ccw(cells: Array, n: int) -> Array:
	var out: Array = []
	for c in cells:
		out.append(Vector2i(c.y, n - 1 - c.x))
	return out

static func _sorted(cells: Array) -> Array:
	cells = cells.duplicate()
	cells.sort_custom(func(a: Vector2i, b: Vector2i) -> bool:
		if a.y != b.y:
			return a.y < b.y
		return a.x < b.x)
	return cells

static func _build_states() -> void:
	for name in SPAWN_CELLS:
		var n := 4 if name == "I" else 3
		var s0: Array = _sorted(SPAWN_CELLS[name])
		if name == "O":
			_all_cells[name] = [s0, s0, s0, s0]
			continue
		var s1: Array = _sorted(_rot_cw(s0, n))
		var s2: Array = _sorted(_rot_cw(s1, n))
		var s3: Array = _sorted(_rot_ccw(s0, n))
		_all_cells[name] = [s0, s1, s2, s3]

static func cells_for(name: String, rot: int) -> Array:
	if _all_cells.is_empty():
		_build_states()
	return _all_cells[name][rot]

# ---------------- SRS 踢墙表
const KICKS_JLSTZ := {
	"0-1": [Vector2i(0, 0), Vector2i(-1, 0), Vector2i(-1, 1), Vector2i(0, -2), Vector2i(-1, -2)],
	"1-0": [Vector2i(0, 0), Vector2i(1, 0), Vector2i(1, -1), Vector2i(0, 2), Vector2i(1, 2)],
	"1-2": [Vector2i(0, 0), Vector2i(1, 0), Vector2i(1, -1), Vector2i(0, 2), Vector2i(1, 2)],
	"2-1": [Vector2i(0, 0), Vector2i(-1, 0), Vector2i(-1, 1), Vector2i(0, -2), Vector2i(-1, -2)],
	"2-3": [Vector2i(0, 0), Vector2i(1, 0), Vector2i(1, 1), Vector2i(0, -2), Vector2i(1, -2)],
	"3-2": [Vector2i(0, 0), Vector2i(-1, 0), Vector2i(-1, -1), Vector2i(0, 2), Vector2i(-1, 2)],
	"3-0": [Vector2i(0, 0), Vector2i(-1, 0), Vector2i(-1, -1), Vector2i(0, 2), Vector2i(-1, 2)],
	"0-3": [Vector2i(0, 0), Vector2i(1, 0), Vector2i(1, 1), Vector2i(0, -2), Vector2i(1, -2)],
}
const KICKS_I := {
	"0-1": [Vector2i(0, 0), Vector2i(-2, 0), Vector2i(1, 0), Vector2i(-2, -1), Vector2i(1, 2)],
	"1-0": [Vector2i(0, 0), Vector2i(2, 0), Vector2i(-1, 0), Vector2i(2, 1), Vector2i(-1, -2)],
	"1-2": [Vector2i(0, 0), Vector2i(-1, 0), Vector2i(2, 0), Vector2i(-1, 2), Vector2i(2, -1)],
	"2-1": [Vector2i(0, 0), Vector2i(1, 0), Vector2i(-2, 0), Vector2i(1, -2), Vector2i(-2, 1)],
	"2-3": [Vector2i(0, 0), Vector2i(2, 0), Vector2i(-1, 0), Vector2i(2, 1), Vector2i(-1, -2)],
	"3-2": [Vector2i(0, 0), Vector2i(-2, 0), Vector2i(1, 0), Vector2i(-2, -1), Vector2i(1, 2)],
	"3-0": [Vector2i(0, 0), Vector2i(1, 0), Vector2i(-2, 0), Vector2i(1, -2), Vector2i(-2, 1)],
	"0-3": [Vector2i(0, 0), Vector2i(-1, 0), Vector2i(2, 0), Vector2i(-1, 2), Vector2i(2, -1)],
}
const KICKS_O := {
	"0-1": [Vector2i(0, 0)], "1-0": [Vector2i(0, 0)], "1-2": [Vector2i(0, 0)],
	"2-1": [Vector2i(0, 0)], "2-3": [Vector2i(0, 0)], "3-2": [Vector2i(0, 0)],
	"3-0": [Vector2i(0, 0)], "0-3": [Vector2i(0, 0)],
}

static func kicks_for(name: String) -> Dictionary:
	if name == "I":
		return KICKS_I
	if name == "O":
		return KICKS_O
	return KICKS_JLSTZ

static func t_spin_corners(ox: int, oy: int) -> Array:
	return [Vector2i(ox - 1, oy - 1), Vector2i(ox + 3, oy - 1), Vector2i(ox - 1, oy + 3), Vector2i(ox + 3, oy + 3)]


# ---------------- 7-bag 生成器
class Bag7:
	var rng := RandomNumberGenerator.new()
	var _bag: Array[String] = []

	func _init(seed_value: int = 0) -> void:
		if seed_value != 0:
			rng.seed = seed_value

	func _refill() -> void:
		var bag: Array[String] = PIECE_NAMES.duplicate()
		# Fisher-Yates
		for i in range(bag.size() - 1, 0, -1):
			var j := rng.randi_range(0, i)
			var t := bag[i]
			bag[i] = bag[j]
			bag[j] = t
		_bag.append_array(bag)

	func next() -> String:
		if _bag.is_empty():
			_refill()
		return _bag.pop_front()

	func peek(n: int) -> Array[String]:
		while _bag.size() < n:
			_refill()
		return _bag.slice(0, n)
