class_name Board3D
extends Node3D
## 伪 3D 场地渲染：程序化 ArrayMesh 合并方块 + 皮肤材质 + 幽灵 + 活动块

const CELL := 1.0

var skin := "luminous"
var _mat: ShaderMaterial = null
var _mat_ghost: ShaderMaterial = null
var _fixed_mesh: MeshInstance3D
var _ghost_mesh: MeshInstance3D
var _active_mesh: MeshInstance3D
var _floor_mesh: MeshInstance3D
var _grid_floor: MeshInstance3D
var _edge_mesh: MeshInstance3D

# 最近一次要渲染的几何数据（由 main 注入）
var fixed_cells: Array = []        # [Vector3 pos, Color color, float light]
var ghost_cells: Array = []
var active_cells: Array = []


func _init() -> void:
	_make_materials()
	_fixed_mesh = MeshInstance3D.new()
	_fixed_mesh.name = "FixedMesh"
	_fixed_mesh.mesh = ArrayMesh.new()
	add_child(_fixed_mesh)
	_ghost_mesh = MeshInstance3D.new()
	_ghost_mesh.name = "GhostMesh"
	_ghost_mesh.mesh = ArrayMesh.new()
	add_child(_ghost_mesh)
	_active_mesh = MeshInstance3D.new()
	_active_mesh.name = "ActiveMesh"
	_active_mesh.mesh = ArrayMesh.new()
	add_child(_active_mesh)
	_build_floor()


func _make_materials() -> void:
	_mat = ShaderMaterial.new()
	_mat.shader = _make_shader()
	_mat.set_shader_parameter("glow_strength", 0.55)
	_mat.set_shader_parameter("metallic", 0.08)
	_mat.set_shader_parameter("roughness", 0.35)
	_mat_ghost = ShaderMaterial.new()
	_mat_ghost.shader = _make_shader()
	_mat_ghost.set_shader_parameter("glow_strength", 0.25)
	_mat_ghost.set_shader_parameter("ghost_mode", true)


static func _make_shader() -> Shader:
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

uniform float glow_strength : hint_range(0.0, 2.0) = 0.5;
uniform float metallic : hint_range(0.0, 1.0) = 0.05;
uniform float roughness : hint_range(0.0, 1.0) = 0.35;
uniform bool ghost_mode = false;

varying float v_light;
varying float v_height;

void vertex() {
	vec3 n = normalize(NORMAL);
	float up = max(dot(n, vec3(0.0, 1.0, 0.0)), 0.0);
	float side = max(dot(n, vec3(1.0, 0.0, 0.0)), 0.0) + max(dot(n, vec3(0.0, 0.0, 1.0)), 0.0);
	v_light = clamp(0.30 + 0.55 * up + 0.10 * side, 0.0, 1.0);
	v_height = (MODEL_MATRIX * vec4(VERTEX, 1.0)).y;
}

void fragment() {
	vec3 base = COLOR.rgb;
	if (ghost_mode) {
		float pulse = 0.5 + 0.5 * sin(TIME * 3.0 + v_height);
		ALBEDO = base * 0.35;
		ALPHA = 0.28 + 0.12 * pulse;
		EMISSION = base * 0.35;
		ROUGHNESS = 0.5;
	} else {
		vec3 col = base * (0.30 + 0.70 * v_light);
		ALBEDO = col;
		METALLIC = metallic;
		ROUGHNESS = roughness;
		EMISSION = base * glow_strength * v_light;
	}
}
"""
	return sh


func _build_floor() -> void:
	# 底座平台（棋盘底部）：y=0 平面，尺寸覆盖棋盘投影
	var base := BoxMesh.new()
	base.size = Vector3(11.0, 0.25, 2.4)
	var bm := MeshInstance3D.new()
	bm.mesh = base
	var bmat := StandardMaterial3D.new()
	bmat.albedo_color = Color(0.08, 0.12, 0.30)
	bmat.metallic = 0.6
	bmat.roughness = 0.4
	bmat.emission_enabled = true
	bmat.emission = Color(0.1, 0.2, 0.55)
	bmat.emission_energy_multiplier = 0.8
	bm.material_override = bmat
	bm.position = Vector3(0.0, -0.13, 0.0)
	add_child(bm)

	# 地面网格（围绕底座的发光网格线）
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_LINES)
	for li in range(-7, 8):
		st.add_vertex(Vector3(li, 0, -4))
		st.add_vertex(Vector3(li, 0, 4))
	for lj in range(-4, 5):
		st.add_vertex(Vector3(-7, 0, lj))
		st.add_vertex(Vector3(7, 0, lj))
	var grid_mesh := st.commit()
	var gm := MeshInstance3D.new()
	gm.mesh = grid_mesh
	var gmat := StandardMaterial3D.new()
	gmat.albedo_color = Color(0.3, 0.45, 1.0, 0.28)
	gmat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	gmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	gm.material_override = gmat
	gm.position = Vector3(0.0, 0.0, 0.0)
	_grid_floor = gm
	add_child(gm)

	# 四角光柱
	for corner in [Vector3(-5.0, 0.0, -0.6), Vector3(5.0, 0.0, -0.6),
			Vector3(-5.0, 0.0, 0.6), Vector3(5.0, 0.0, 0.6)]:
		var pillar := BoxMesh.new()
		pillar.size = Vector3(0.12, 22.0, 0.12)
		var pm := MeshInstance3D.new()
		pm.mesh = pillar
		var pmat := StandardMaterial3D.new()
		pmat.albedo_color = Color(0.7, 0.8, 1.0, 0.22)
		pmat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		pmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		pm.material_override = pmat
		pm.position = corner + Vector3(0.0, 10.5, 0.0)
		add_child(pm)

	# 棋盘面网格（竖直碑：10 宽 x 22 高，位于 z=0 平面）
	var bst := SurfaceTool.new()
	bst.begin(Mesh.PRIMITIVE_LINES)
	for lx in range(-5, 6):
		bst.add_vertex(Vector3(lx, 0.0, 0.05))
		bst.add_vertex(Vector3(lx, 22.0, 0.05))
	for ly in range(0, 23):
		bst.add_vertex(Vector3(-5.0, ly, 0.05))
		bst.add_vertex(Vector3(5.0, ly, 0.05))
	var board_grid := bst.commit()
	var bgi := MeshInstance3D.new()
	bgi.mesh = board_grid
	var bgm := StandardMaterial3D.new()
	bgm.albedo_color = Color(0.35, 0.5, 1.0, 0.20)
	bgm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	bgm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	bgi.material_override = bgm
	bgi.position = Vector3.ZERO
	add_child(bgi)


# 逻辑坐标 (col, row) -> 世界坐标（竖直碑：列→x，行→y，凸起→z）
func cell_world(col: int, row: int) -> Vector3:
	return Vector3((col - 5 + 0.5) * CELL, (21.0 - row) * CELL + 0.5 * CELL, 0.0)


# ------------------------------------------------------------ 网格构建
func _push_cube(verts: PackedVector3Array, normals: PackedVector3Array,
		cols: PackedColorArray, idx: PackedInt32Array,
		center: Vector3, size: float,
		c_top: Color, c_bottom: Color, c_nx: Color, c_px: Color, c_nz: Color, c_pz: Color) -> void:
	var h := size * 0.5
	var v: Array = []
	# 顶点偏移（每面 4 个）
	# 顶面 +Y
	v.append([Vector3(-h, h, -h), Vector3(h, h, -h), Vector3(h, h, h), Vector3(-h, h, h)])
	# 底面 -Y
	v.append([Vector3(-h, -h, h), Vector3(h, -h, h), Vector3(h, -h, -h), Vector3(-h, -h, -h)])
	# +X
	v.append([Vector3(h, -h, -h), Vector3(h, h, -h), Vector3(h, h, h), Vector3(h, -h, h)])
	# -X
	v.append([Vector3(-h, -h, h), Vector3(-h, h, h), Vector3(-h, h, -h), Vector3(-h, -h, -h)])
	# +Z
	v.append([Vector3(-h, -h, h), Vector3(h, -h, h), Vector3(h, h, h), Vector3(-h, h, h)])
	# -Z
	v.append([Vector3(h, -h, -h), Vector3(-h, -h, -h), Vector3(-h, h, -h), Vector3(h, h, -h)])
	var nrm: Array = [
		Vector3(0, 1, 0), Vector3(0, -1, 0), Vector3(1, 0, 0),
		Vector3(-1, 0, 0), Vector3(0, 0, 1), Vector3(0, 0, -1),
	]
	var face_colors := [c_top, c_bottom, c_px, c_nx, c_pz, c_nz]
	var base := verts.size()
	for f in range(6):
		for i in range(4):
			verts.append(center + v[f][i])
			normals.append(nrm[f])
			cols.append(face_colors[f])
		var a := base + f * 4
		idx.append(a)
		idx.append(a + 1)
		idx.append(a + 2)
		idx.append(a)
		idx.append(a + 2)
		idx.append(a + 3)


func rebuild_from(fixed: Array, ghost: Array, active: Array) -> void:
	rebuild_fixed(fixed)
	rebuild_ghost(ghost)
	rebuild_active(active)


func rebuild_fixed(cells: Array) -> void:
	fixed_cells = cells
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var cols := PackedColorArray()
	var idx := PackedInt32Array()
	for cell in cells:
		_push_cube(verts, normals, cols, idx, cell.pos, 0.92,
			cell.col_top, cell.col_bottom, cell.col_nz, cell.col_pz,
			cell.col_nz, cell.col_pz)
	_apply_mesh(_fixed_mesh, verts, normals, cols, idx, _mat)


func rebuild_ghost(cells: Array) -> void:
	ghost_cells = cells
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var cols := PackedColorArray()
	var idx := PackedInt32Array()
	for cell in cells:
		_push_cube(verts, normals, cols, idx, cell.pos, 0.90,
			cell.col_top, cell.col_top, cell.col_top, cell.col_top, cell.col_top, cell.col_top)
	_apply_mesh(_ghost_mesh, verts, normals, cols, idx, _mat_ghost)


func rebuild_active(cells: Array) -> void:
	active_cells = cells
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var cols := PackedColorArray()
	var idx := PackedInt32Array()
	for cell in cells:
		_push_cube(verts, normals, cols, idx, cell.pos, 0.94,
			cell.col_top, cell.col_bottom, cell.col_nz, cell.col_pz,
			cell.col_nz, cell.col_pz)
	_apply_mesh(_active_mesh, verts, normals, cols, idx, _mat)


func _apply_mesh(mi: MeshInstance3D, verts: PackedVector3Array, normals: PackedVector3Array,
		cols: PackedColorArray, idx: PackedInt32Array, mat: Material) -> void:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = cols
	arrays[Mesh.ARRAY_INDEX] = idx
	var m := ArrayMesh.new()
	if verts.size() > 0:
		m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mi.mesh = m
	mi.material_override = mat


# ------------------------------------------------------------ 皮肤
func apply_skin(skin_name: String) -> void:
	skin = skin_name
	var cfg: Dictionary = TetrisConstants.SKINS.get(skin_name, TetrisConstants.SKINS["luminous"])
	_mat.set_shader_parameter("glow_strength", cfg["glow"])
	_mat.set_shader_parameter("metallic", cfg["metal"])
	_mat.set_shader_parameter("roughness", cfg["rough"])


func skin_color(base: Color, factor: float) -> Color:
	var cfg: Dictionary = TetrisConstants.SKINS.get(skin, TetrisConstants.SKINS["luminous"])
	var sat: float = cfg["sat"]
	var g: float = base.v
	var gray := Color(g, g, g)
	return gray.lerp(base, sat) * factor
