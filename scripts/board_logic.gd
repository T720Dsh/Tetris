class_name TetrisBoard
extends RefCounted
## 场地逻辑：网格、碰撞、消行、锁定、T-spin、指南计分（移植自 board.py）

const FULL_H := TetrisConstants.ROWS + TetrisConstants.HIDDEN_TOP
const TOP_ROW := -TetrisConstants.HIDDEN_TOP

var mode := "sprint40"
var bag: TetrisPieces.Bag7 = null
var grid: Dictionary = {}          # Vector2i -> name
var piece: Dictionary = {}         # {name, x, y, rot, rotated, grounded}
var hold := ""
var hold_used := false
var next_queue: Array[String] = []
var garbage_seed := 0

var score := 0
var lines := 0
var level := 1
var pieces_placed := 0
var combo := 0
var b2b := false
var perfect_chain := 0

var lock_timer := 0.0
var lock_resets := 0
var gravity_acc := 0.0
var drop_frac := 0.0
var gravity_scale_override := 1.0
var clock := 0.0
var game_over := false
var marathon_clear := false
var last_event: Dictionary = {}

const CLEAR_ROWS_SCORE := {1: 100, 2: 300, 3: 500, 4: 800}
const TSPIN_FULL_SCORE := {0: 400, 1: 800, 2: 1200, 3: 1600}
const TSPIN_MINI_SCORE := {0: 100, 1: 200, 2: 400}


func _init(p_mode: String = "sprint40") -> void:
	mode = p_mode


func _piece_key() -> String:
	if piece.is_empty():
		return ""
	return piece.name


func piece_cells() -> Array:
	if piece.is_empty():
		return []
	var out: Array = []
	for c in TetrisPieces.cells_for(piece.name, piece.rot):
		out.append(Vector2i(piece.x + c.x, piece.y + c.y))
	return out


# ------------------------------------------------------------ 重力
func gravity_per_frame(dt: float) -> float:
	var s := 0.8
	if mode == "marathon":
		s = pow(0.8 - (level - 1) * 0.007, level - 1)
		s = maxf(s, 0.015)
		return dt / s * gravity_scale_override
	elif mode == "endless":
		var lv := 1 + int(clock / 20.0)
		s = pow(0.8 - (lv - 1) * 0.007, lv - 1)
		s = maxf(s, 0.015)
		return dt / s * gravity_scale_override
	return TetrisConstants.BASE_GRAVITY_CPS * dt * gravity_scale_override


# ------------------------------------------------------------ 垃圾行
func seed_garbage(rows: int, rng: RandomNumberGenerator) -> void:
	if rows <= 0:
		return
	for r in range(TetrisConstants.ROWS - rows, TetrisConstants.ROWS):
		var cols: Array[int] = []
		for c in range(TetrisConstants.COLS):
			cols.append(c)
		for i in range(cols.size() - 1, 0, -1):
			var j := rng.randi_range(0, i)
			var t := cols[i]
			cols[i] = cols[j]
			cols[j] = t
		var holes_count := 2 if rng.randf() < 0.5 else 1
		var names := ["J", "L", "S", "Z", "O", "T"]
		for c in range(TetrisConstants.COLS):
			if c in cols.slice(0, holes_count):
				continue  # 洞列不填
			grid[Vector2i(c, r)] = names[rng.randi_range(0, names.size() - 1)]


# ------------------------------------------------------------ 碰撞
func collides(name: String, x: int, y: int, rot: int) -> bool:
	for c in TetrisPieces.cells_for(name, rot):
		var gx: int = x + c.x
		var gy: int = y + c.y
		if gx < 0 or gx >= TetrisConstants.COLS or gy >= TetrisConstants.ROWS:
			return true
		if gy >= TOP_ROW and grid.has(Vector2i(gx, gy)):
			return true
	return false


# ------------------------------------------------------------ 出块
func spawn(name: String = "") -> bool:
	if name == "":
		if next_queue.is_empty() and bag != null:
			while next_queue.size() < 5:
				next_queue.append(bag.next())
		name = next_queue.pop_front()
	var x := 3
	var y := -2 if name == "I" else -1
	if collides(name, x, y, 0):
		game_over = true
		return false
	piece = {"name": name, "x": x, "y": y, "rot": 0, "rotated": false, "grounded": false}
	lock_timer = 0.0
	lock_resets = 0
	gravity_acc = 0.0
	drop_frac = 0.0
	return true


func refill_next() -> void:
	if bag == null:
		return
	while next_queue.size() < 5:
		next_queue.append(bag.next())


# ------------------------------------------------------------ 移动 / 旋转
func try_move(dx: int, dy: int) -> bool:
	if piece.is_empty() or game_over:
		return false
	if not collides(piece.name, piece.x + dx, piece.y + dy, piece.rot):
		piece.x += dx
		piece.y += dy
		piece.grounded = _hits_ground()
		return true
	return false


func try_rotate(direction: int) -> bool:
	if piece.is_empty() or game_over:
		return false
	var p := piece
	var new_rot: int = (p.rot + direction) % 4
	if direction == 2:
		for kick in _kicks(p.name, p.rot, (p.rot + 1) % 4):
			var mid_rot: int = (p.rot + 1) % 4
			if collides(p.name, p.x + kick.x, p.y + kick.y, mid_rot):
				continue
			for kick2 in _kicks(p.name, mid_rot, new_rot):
				if not collides(p.name, p.x + kick.x + kick2.x, p.y + kick.y + kick2.y, new_rot):
					p.x += kick.x + kick2.x
					p.y += kick.y + kick2.y
					p.rot = new_rot
					p.rotated = true
					p.grounded = _hits_ground()
					piece = p
					return true
		return false
	for kick in _kicks(p.name, p.rot, new_rot):
		if not collides(p.name, p.x + kick.x, p.y + kick.y, new_rot):
			p.x += kick.x
			p.y += kick.y
			p.rot = new_rot
			p.rotated = true
			p.grounded = _hits_ground()
			piece = p
			return true
	return false


func _kicks(name: String, frm: int, to: int) -> Array:
	var table: Dictionary = TetrisPieces.kicks_for(name)
	return table.get("%d-%d" % [frm, to], [Vector2i(0, 0)])


func _hits_ground() -> bool:
	if piece.is_empty():
		return false
	return collides(piece.name, piece.x, piece.y + 1, piece.rot)


func drop_distance() -> int:
	if piece.is_empty():
		return 0
	var d := 0
	while not collides(piece.name, piece.x, piece.y + d + 1, piece.rot):
		d += 1
	return d


func hard_drop() -> int:
	if piece.is_empty() or game_over:
		return 0
	var d := drop_distance()
	piece.y += d
	score += 2 * d
	drop_frac = 0.0
	return d


func soft_drop_step() -> bool:
	if piece.is_empty() or game_over:
		return false
	if try_move(0, 1):
		score += 1
		lock_timer = 0.0
		lock_resets = 0
		drop_frac = 0.0
		return true
	return false


# ------------------------------------------------------------ 更新（重力 + 锁定）
func update(dt: float) -> void:
	clock += dt
	if piece.is_empty() or game_over:
		return
	var g := gravity_per_frame(dt)
	if g >= 1.0:
		if not piece.grounded:
			piece.y += drop_distance()
			piece.grounded = true
		drop_frac = 0.0
	else:
		gravity_acc += g
		while gravity_acc >= 1.0:
			if not try_move(0, 1):
				break
			gravity_acc -= 1.0
		drop_frac = gravity_acc
	if piece.grounded:
		lock_timer += dt
		drop_frac = 0.0
		if lock_timer >= TetrisConstants.LOCK_DELAY:
			lock()
	else:
		lock_timer = 0.0


func reset_lock() -> void:
	if lock_resets < TetrisConstants.LOCK_MAX_RESET:
		lock_timer = 0.0
		lock_resets += 1


# ------------------------------------------------------------ 锁定与结算
func lock() -> Dictionary:
	if piece.is_empty():
		return {}
	var p := piece
	for c in piece_cells():
		if c.y < TOP_ROW:
			game_over = true
			return {}
		grid[c] = p.name
	var ev := _resolve(p)
	ev["piece_y"] = p.y
	pieces_placed += 1
	piece = {}
	hold_used = false
	last_event = ev
	return ev


func _resolve(p: Dictionary) -> Dictionary:
	var ev := {"rows": [], "tspin": null, "b2b": false, "combo": 0, "perfect": false, "score": 0, "points": {}}
	var rows: Array[int] = []
	for r in range(TetrisConstants.ROWS):
		var full := true
		for c in range(TetrisConstants.COLS):
			if not grid.has(Vector2i(c, r)):
				full = false
				break
		if full:
			rows.append(r)
	ev["rows"] = rows

	if p.name == "T" and p.rotated:
		var filled := 0
		for corner in TetrisPieces.t_spin_corners(p.x, p.y):
			if corner.x < 0 or corner.x >= TetrisConstants.COLS or corner.y >= TetrisConstants.ROWS:
				filled += 1
			elif corner.y >= TOP_ROW and grid.has(corner):
				filled += 1
		if filled >= 3:
			ev["tspin"] = "full"
		elif filled == 2:
			ev["tspin"] = "mini"

	var n := rows.size()
	if n > 0:
		for r in rows:
			for c in range(TetrisConstants.COLS):
				grid.erase(Vector2i(c, r))
		_collapse(rows)
		lines += n
		combo += 1
		ev["combo"] = combo
		if mode == "marathon":
			level = mini(20, lines / 10 + 1)
	else:
		combo = 0
		perfect_chain = 0

	ev["perfect"] = (grid.is_empty() and n > 0)
	if ev["perfect"]:
		perfect_chain += 1
	else:
		perfect_chain = 0

	var scored := _score(ev, n)
	ev["score"] = scored[0]
	ev["points"] = scored[1]
	score += ev["score"]

	var is_b2b_eligible: bool = n > 0 and (ev["tspin"] == "full" or n == 4)
	if is_b2b_eligible:
		ev["b2b"] = b2b
		b2b = true
	elif n > 0:
		b2b = false
	return ev


func _collapse(rows: Array) -> void:
	if rows.is_empty():
		return
	var new_grid: Dictionary = {}
	for key in grid:
		var name: String = grid[key]
		var drop := 0
		for rr in rows:
			if rr > key.y:
				drop += 1
		new_grid[Vector2i(key.x, key.y + drop)] = name
	grid = new_grid


func _score(ev: Dictionary, n: int) -> Array:
	var val := 0
	if ev["tspin"] == "full":
		val = TSPIN_FULL_SCORE.get(n, 0)
	elif ev["tspin"] == "mini":
		val = TSPIN_MINI_SCORE.get(n, 0)
	else:
		val = CLEAR_ROWS_SCORE.get(n, 0)
	var combo_bonus := 50 * (combo - 1) if combo >= 2 else 0
	var total := val + combo_bonus
	var b2b_bonus := 0
	if ev["b2b"] and (ev["tspin"] == "full" or n == 4):
		total = int(total * 1.5)
		b2b_bonus = total - val - combo_bonus
	var perfect_bonus := 3500 if ev["perfect"] else 0
	total += perfect_bonus
	var points := {
		"lines": val if ev["tspin"] == null else 0,
		"tspin": val if ev["tspin"] != null else 0,
		"combo": combo_bonus,
		"b2b": b2b_bonus,
		"perfect": perfect_bonus,
	}
	return [total, points]


func goal_met() -> bool:
	var cfg: Dictionary = TetrisConstants.MODE_CFG.get(mode, {})
	if cfg.is_empty():
		return false
	if cfg["goal"] == "lines":
		return lines >= cfg["target"]
	if cfg["goal"] == "score":
		return score >= cfg["target"]
	return false


# ------------------------------------------------------------ 暂存
func do_hold() -> bool:
	if hold_used or game_over or piece.is_empty():
		return false
	var old: String = piece.name
	if hold == "":
		hold = old
		if bag != null:
			while next_queue.size() < 1:
				next_queue.append(bag.next())
		if not spawn():
			return false
	else:
		var nxt: String = hold
		hold = old
		if not spawn(nxt):
			return false
	hold_used = true
	return true


# ------------------------------------------------------------ 栈高
func danger_level() -> float:
	var worst := 0.0
	for r in range(TOP_ROW, 8):
		for c in range(TetrisConstants.COLS):
			if grid.has(Vector2i(c, r)):
				var frac := 1.0 - float(r - TOP_ROW) / float(8 - TOP_ROW)
				worst = maxf(worst, frac)
	return worst


func stack_height() -> int:
	var h := 0
	for r in range(TetrisConstants.ROWS):
		for c in range(TetrisConstants.COLS):
			if grid.has(Vector2i(c, r)):
				h = TetrisConstants.ROWS - r
				break
	return h
