extends SceneTree
## 逻辑自测：移动/旋转/消行/计分/胜负（无 UI，headless 可跑）

var passed := 0
var failed := 0

func _init() -> void:
	_check("bag 7 不重复", _test_bag())
	_check("出生可落", _test_spawn())
	_check("左右移动", _test_move())
	_check("旋转", _test_rotate())
	_check("硬降到底", _test_hard_drop())
	_check("锁定占格", _test_lock())
	_check("消行计分", _test_clear())
	_check("T 旋判定", _test_tspin())
	_check("暂存切换", _test_hold())
	_check("game over", _test_over())
	print("RESULT pass=", passed, " fail=", failed)
	quit(1 if failed > 0 else 0)


func _check(name: String, ok: bool) -> void:
	if ok:
		passed += 1
		print("PASS ", name)
	else:
		failed += 1
		print("FAIL ", name)


func _mkboard(mode: String) -> TetrisBoard:
	var b := TetrisBoard.new(mode)
	var bag := TetrisPieces.Bag7.new(12345)
	b.bag = bag
	return b


func _test_bag() -> bool:
	var bag := TetrisPieces.Bag7.new(42)
	var seen: Dictionary = {}
	for i in range(7):
		seen[bag.next()] = true
	return seen.size() == 7


func _test_spawn() -> bool:
	var b := _mkboard("sprint40")
	b.spawn()
	return not b.piece.is_empty() and b.piece.y < 0


func _test_move() -> bool:
	var b := _mkboard("sprint40")
	b.spawn()
	var y0: int = b.piece.y
	if not b.try_move(-1, 0):
		return false
	if b.piece.y != y0:
		return false
	if not b.try_move(1, 0):
		return false
	return true


func _test_rotate() -> bool:
	var b := _mkboard("sprint40")
	b.spawn()
	var r0: int = b.piece.rot
	return b.try_rotate(1) and b.piece.rot != r0


func _test_hard_drop() -> bool:
	var b := _mkboard("sprint40")
	b.spawn()
	var d := b.drop_distance()
	return d > 0 and b.hard_drop() == d


func _test_lock() -> bool:
	var b := _mkboard("sprint40")
	b.spawn()
	b.hard_drop()
	b.lock()
	return b.grid.size() == 4 and b.pieces_placed == 1


func _test_clear() -> bool:
	var b := _mkboard("sprint40")
	b.spawn()
	b.hard_drop()
	b.lock()
	# 构造：行 18 已有 6 格，I 横放补满 10 格 → 触发消行
	b.grid = {}
	for c in range(4, 10):
		b.grid[Vector2i(c, 18)] = "J"
	b.lines = 0
	b.piece = {"name": "I", "x": 0, "y": 17, "rot": 0, "rotated": false, "grounded": true}
	b.lock()
	if b.lines != 1:
		return false
	if b.score <= 0:
		return false
	var ev: Dictionary = b.last_event
	if not ev.has("rows"):
		return false
	return (ev["rows"] as Array).size() == 1


func _test_tspin() -> bool:
	var b := _mkboard("sprint40")
	# 构造 T 旋环境：四个角有块
	for corner in [Vector2i(3, 18), Vector2i(5, 18), Vector2i(3, 20), Vector2i(5, 20)]:
		b.grid[corner] = "J"
	b.piece = {"name": "T", "x": 4, "y": 18, "rot": 0, "rotated": true, "grounded": true}
	b.lock()
	var ev: Dictionary = b.last_event
	return ev.has("tspin") and ev["tspin"] != null


func _test_hold() -> bool:
	var b := _mkboard("sprint40")
	b.spawn()
	var first: String = b.piece.name
	if not b.do_hold():
		return false
	return b.hold == first and not b.piece.is_empty() and b.piece.name != first


func _test_over() -> bool:
	var b := _mkboard("sprint40")
	b.spawn()
	b.hard_drop()
	b.lock()
	# 顶部溢出触发 game over：填满顶部两行
	for c in range(10):
		b.grid[Vector2i(c, 0)] = "T"
		b.grid[Vector2i(c, 1)] = "T"
	b.piece = {"name": "I", "x": 3, "y": -2, "rot": 0, "rotated": false, "grounded": false}
	var over := b.lock()
	return over or b.game_over
