class_name Background3D
extends Node3D
## 背景系统：程序化天空渐变 + 主题装饰 + 自定义图片背景

var theme := "default"
var custom_texture: Texture2D = null

var _env: Environment
var _sky: Sky
var _world_env: WorldEnvironment
var _deco: Node3D
var _stars: Array[Node3D] = []
var _grid_wall: MeshInstance3D


func _init() -> void:
	_world_env = WorldEnvironment.new()
	_env = Environment.new()
	_sky = Sky.new()
	_env.background_mode = Environment.BG_SKY
	_env.sky = _sky
	_env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	_env.ambient_light_energy = 0.7
	_env.ambient_light_color = Color(0.5, 0.6, 1.0)
	_env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	_env.fog_enabled = true
	_env.fog_density = 0.02
	_env.fog_sky_affect = 0.6
	_world_env.environment = _env
	add_child(_world_env)
	apply_theme("default")


func apply_theme(t: String) -> void:
	theme = t
	var cfg: Dictionary = TetrisConstants.BG_THEMES_CFG.get(t, TetrisConstants.BG_THEMES_CFG["default"])
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = cfg["sky_top"]
	sky_mat.sky_horizon_color = (cfg["sky_top"] + cfg["sky_bottom"]) * 0.5
	sky_mat.ground_horizon_color = (cfg["sky_top"] + cfg["sky_bottom"]) * 0.4
	sky_mat.ground_bottom_color = cfg["sky_bottom"] * 0.7
	_sky.sky_material = sky_mat
	_env.fog_light_color = cfg["fog"]
	_build_deco(cfg["deco"])


func _build_deco(kind: String) -> void:
	if _deco != null:
		_deco.queue_free()
	_deco = Node3D.new()
	add_child(_deco)

	if kind == "default" or kind == "grid":
		_add_grid_wall()
	if kind == "nebula":
		_add_grid_wall()
		_add_stars(90)
	if kind == "city":
		_add_city_blocks()
		_add_grid_wall()
	if kind == "aurora":
		_add_grid_wall()
		_add_stars(120)


func _add_grid_wall() -> void:
	if _grid_wall != null:
		_grid_wall.queue_free()
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_LINES)
	for li in range(-150, 151, 4):
		st.add_vertex(Vector3(li, 0, 0))
		st.add_vertex(Vector3(li, 60, 0))
	for lj in range(0, 61, 4):
		st.add_vertex(Vector3(-150, lj, 0))
		st.add_vertex(Vector3(150, lj, 0))
	var wall_mesh := st.commit()
	var mi := MeshInstance3D.new()
	mi.mesh = wall_mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.3, 0.5, 1.0, 0.06)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mi.material_override = mat
	mi.position = Vector3(0.0, 30.0, -80.0)
	_deco.add_child(mi)
	_grid_wall = mi


func _add_stars(count: int) -> void:
	for i in range(count):
		var bm := SphereMesh.new()
		bm.radius = 0.15
		bm.height = 0.3
		var mi := MeshInstance3D.new()
		mi.mesh = bm
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.9, 0.95, 1.0)
		mat.emission_enabled = true
		mat.emission = Color(0.8, 0.9, 1.0, 1.0)
		mat.emission_energy_multiplier = 2.0
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mi.material_override = mat
		mi.position = Vector3(
			randf_range(-120.0, 120.0),
			randf_range(25.0, 80.0),
			randf_range(-150.0, 30.0))
		_deco.add_child(mi)
		_stars.append(mi)


func _add_city_blocks() -> void:
	for i in range(70):
		var bh := randf_range(4.0, 28.0)
		var box := BoxMesh.new()
		box.size = Vector3(randf_range(6.0, 14.0), bh, randf_range(6.0, 14.0))
		var mi := MeshInstance3D.new()
		mi.mesh = box
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.05, 0.08, 0.18)
		mat.roughness = 0.9
		mi.material_override = mat
		# 建筑围绕场地中心 (0,10.5,0) 分布
		var angle := randf() * TAU
		var rad := randf_range(60.0, 140.0)
		mi.position = Vector3(cos(angle) * rad, 10.5 + bh * 0.5, sin(angle) * rad)
		_deco.add_child(mi)
		# 窗户光点
		for w in range(5):
			var wm := BoxMesh.new()
			wm.size = Vector3(0.5, 0.5, 0.5)
			var wi := MeshInstance3D.new()
			wi.mesh = wm
			var wmat := StandardMaterial3D.new()
			wmat.albedo_color = Color(0.4, 0.5, 0.7)
			wmat.emission_enabled = true
			wmat.emission = Color(0.5, 0.6, 0.9)
			wmat.emission_energy_multiplier = 1.5
			wmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
			wi.material_override = wmat
			wi.position = mi.position + Vector3(
				randf_range(-4.0, 4.0), randf_range(-bh * 0.35, bh * 0.35), randf_range(-4.0, 4.0))
			_deco.add_child(wi)


func set_custom_texture(tex: Texture2D) -> void:
	custom_texture = tex
	if tex == null:
		return
	# 自定义背景：作为天空球全景图（360° 任意视角可见）
	var pan := PanoramaSkyMaterial.new()
	pan.panorama_texture = tex
	_sky.sky_material = pan
	_env.fog_color = Color(0.02, 0.02, 0.03)
	if _deco != null:
		_deco.queue_free()
		_deco = null


func clear_custom_texture() -> void:
	custom_texture = null
	apply_theme(theme)
