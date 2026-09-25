extends Node
## 设置与纪录持久化（user://settings.json / records.json）

const SETTINGS_PATH := "user://settings.json"
const RECORDS_PATH := "user://records.json"

var settings: Dictionary = {}
var records: Dictionary = {}


func _ready() -> void:
	load_all()


func defaults() -> Dictionary:
	return {
		"das": TetrisConstants.DAS,
		"arr": TetrisConstants.ARR,
		"ghost": true,
		"sound": true,
		"volume": 0.7,
		"skin": "luminous",
		"bg_theme": "default",
		"custom_bg": "",
		"fullscreen": false,
		"gravity_speed": "very_slow",
		"view_sensitivity": 0.25,
		"keybinds": {},
		"settings_version": 4,
	}


func load_all() -> void:
	settings = defaults()
	var f := FileAccess.open(SETTINGS_PATH, FileAccess.READ)
	if f != null:
		var data: Variant = JSON.parse_string(f.get_as_text())
		if data is Dictionary:
			for k in data:
				settings[k] = data[k]
	# keybinds 合并默认
	var kb: Dictionary = settings["keybinds"]
	for k in TetrisConstants.DEFAULT_KEYBINDS:
		if not kb.has(k):
			kb[k] = TetrisConstants.DEFAULT_KEYBINDS[k]
	settings["keybinds"] = kb
	free_file_handle(f)

	var r := FileAccess.open(RECORDS_PATH, FileAccess.READ)
	if r != null:
		var rdata: Variant = JSON.parse_string(r.get_as_text())
		if rdata is Dictionary:
			records = rdata
	free_file_handle(r)


func save_all() -> void:
	var f := FileAccess.open(SETTINGS_PATH, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(settings, "  "))
		f.close()
	var r := FileAccess.open(RECORDS_PATH, FileAccess.WRITE)
	if r != null:
		r.store_string(JSON.stringify(records, "  "))
		r.close()


func save_settings() -> void:
	var f := FileAccess.open(SETTINGS_PATH, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(settings, "  "))
		f.close()


func save_records() -> void:
	var r := FileAccess.open(RECORDS_PATH, FileAccess.WRITE)
	if r != null:
		r.store_string(JSON.stringify(records, "  "))
		r.close()


# ------------------------------------------------------------ 纪录
func submit_record(mode: String, value: float) -> bool:
	"""提交成绩。time 越小越好；score/survive 越大越好。返回是否新纪录。"""
	var cfg: Dictionary = TetrisConstants.MODE_CFG.get(mode, {})
	if cfg.is_empty():
		return false
	var kind: String = cfg["record"]
	var old: float = records.get(mode, 0.0)
	var is_record := false
	if kind == "time":
		is_record = old <= 0.0 or value < old
		if is_record:
			records[mode] = value
	else:
		is_record = value > old
		if is_record:
			records[mode] = value
	if is_record:
		save_records()
	return is_record


func record_text(mode: String) -> String:
	var cfg: Dictionary = TetrisConstants.MODE_CFG.get(mode, {})
	if cfg.is_empty() or not records.has(mode):
		return "--"
	var kind: String = cfg["record"]
	var v: float = records[mode]
	if kind == "time":
		return "%d.%02d 秒" % [int(v), int(round(fmod(v, 1.0) * 100))]
	return str(int(v))


func free_file_handle(f: FileAccess) -> void:
	# FileAccess 局部变量引用会自动释放；显式 null 以防文件占用
	f = null
