extends Node3D
## A standalone character lab. Add catalogue entries to characters.json.

var player: CharacterBody3D
var visual: Node3D
var anim: AnimationPlayer
var camera: Camera3D
var yaw := 0.0
var pitch := -0.25
var distance := 9.0
var orbiting := false
var catalogue: Array = []
var current: Dictionary = {}
var status: Label
var clip_picker: OptionButton
var manual_clip := false
var elapsed := 0.0
var qa := false
var capture := false
var qa_jumped := false
var qa_moved := false
var qa_landed := false
var qa_start := Vector3.ZERO
var failures: Array[String] = []

func _ready() -> void:
	qa = "--qa" in OS.get_cmdline_user_args()
	capture = "--capture" in OS.get_cmdline_user_args()
	_build_arena()
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://characters.json"))
	if not parsed is Dictionary or not parsed.has("characters"):
		push_error("Invalid character catalogue")
		get_tree().quit(1)
		return
	catalogue = parsed.characters
	_build_ui()
	_load_character(0)
	qa_start = player.position

func material(color: Color, metal := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 0.72
	m.metallic = metal
	return m

func block(label_text: String, pos: Vector3, size: Vector3, color: Color, rotation_z := 0.0) -> void:
	var body := StaticBody3D.new()
	body.name = label_text
	add_child(body)
	body.position = pos
	body.rotation.z = rotation_z
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	mesh.mesh = box
	mesh.material_override = material(color)
	body.add_child(mesh)
	var col := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	col.shape = shape
	body.add_child(col)

func sign_label(text: String, pos: Vector3, size := 42) -> void:
	var label := Label3D.new()
	label.text = text
	label.font_size = size
	label.pixel_size = 0.012
	label.modulate = Color("a9c7d8")
	label.position = pos
	add_child(label)

func _build_arena() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color("172333")
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color("b6cbd9")
	env.environment.ambient_light_energy = 0.4
	env.environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48,-35,0)
	sun.light_color = Color("fff0d8")
	sun.light_energy = 0.85
	sun.shadow_enabled = true
	add_child(sun)
	block("Ground", Vector3(0,-0.25,0),Vector3(60,0.5,60),Color("303d4b"))
	for i in range(-6,7):
		block("GridX%d" % i,Vector3(i*5,0.002,0),Vector3(0.025,0.005,60),Color("53616c"))
		block("GridZ%d" % i,Vector3(0,0.003,i*5),Vector3(60,0.005,0.025),Color("53616c"))
	block("NorthWall",Vector3(0,1,-30),Vector3(60,2,0.4),Color("435365"))
	block("SouthWall",Vector3(0,1,30),Vector3(60,2,0.4),Color("435365"))
	block("EastWall",Vector3(30,1,0),Vector3(0.4,2,60),Color("435365"))
	block("WestWall",Vector3(-30,1,0),Vector3(0.4,2,60),Color("435365"))
	block("Ramp",Vector3(-10,1.3,-9),Vector3(10,0.45,5),Color("5a737c"),0.26)
	for i in range(6):
		block("Step%d" % i,Vector3(7+i*1.2,0.15*(i+1),-10),Vector3(1.2,0.3*(i+1),4),Color("657786"))
	for i in range(3):
		block("JumpBlock%d" % i,Vector3(-5+i*4,0.35+i*0.25,-18),Vector3(2.2,0.7+i*0.5,2.2),Color("8c785b"))
	# 1.8 m human reference, plus a 6 m clearance frame.
	block("HumanScale",Vector3(7,0.9,1),Vector3(0.5,1.8,0.3),Color("bca57a"))
	block("HeightPostL",Vector3(-4,3,4),Vector3(0.12,6,0.12),Color("5b8794"))
	block("HeightPostR",Vector3(4,3,4),Vector3(0.12,6,0.12),Color("5b8794"))
	block("HeightCrossbar",Vector3(0,6,4),Vector3(8.1,0.12,0.12),Color("5b8794"))
	sign_label("RAMP / SLOPE",Vector3(-10,4,-12))
	sign_label("STEPS / JUMP",Vector3(10,4,-13))
	sign_label("1.8 m",Vector3(7,2.3,1),32)
	sign_label("CHARACTER CREATIONS",Vector3(0,6,-28),80)
	camera = Camera3D.new()
	camera.fov = 48
	add_child(camera)

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var panel := PanelContainer.new()
	panel.position = Vector2(24,24)
	panel.custom_minimum_size = Vector2(340,0)
	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color=Color(0.055,0.075,0.1,0.97)
	panel.add_theme_stylebox_override("panel",panel_style)
	layer.add_child(panel)
	var margin := MarginContainer.new()
	for edge in ["left","right","top","bottom"]:margin.add_theme_constant_override("margin_"+edge,16)
	panel.add_child(margin)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation",10)
	margin.add_child(box)
	var title := Label.new()
	title.text = "CHARACTER CREATIONS\nMovement & animation lab"
	title.add_theme_font_size_override("font_size",22)
	box.add_child(title)
	var picker := OptionButton.new()
	for item in catalogue:picker.add_item(item.name)
	picker.item_selected.connect(_load_character)
	box.add_child(picker)
	var controls := Label.new()
	controls.text = "WASD · move    Shift · run\nSpace · jump    R · reset\nHold right mouse · orbit\nMouse wheel · zoom    Esc · release"
	box.add_child(controls)
	clip_picker = OptionButton.new()
	box.add_child(clip_picker)
	clip_picker.item_selected.connect(func(i: int):
		manual_clip = i > 0
		if manual_clip and anim:anim.play(clip_picker.get_item_text(i),0.18))
	var reset := Button.new()
	reset.text = "Reset position & movement"
	reset.pressed.connect(reset_player)
	box.add_child(reset)
	var speed_label := Label.new()
	speed_label.text = "Animation playback speed"
	box.add_child(speed_label)
	var speed := HSlider.new()
	speed.min_value = 0.1
	speed.max_value = 2
	speed.step = 0.05
	speed.value = 1
	speed.value_changed.connect(func(v: float):
		if anim:anim.speed_scale=v)
	box.add_child(speed)
	status = Label.new()
	box.add_child(status)

func _load_character(index: int) -> void:
	if player:
		remove_child(player)
		player.queue_free()
	current = catalogue[index]
	player = CharacterBody3D.new()
	player.floor_snap_length = 0.35
	add_child(player)
	var collision := CollisionShape3D.new()
	var shape := CapsuleShape3D.new()
	shape.height = float(current.height)
	shape.radius = float(current.height)*0.135
	collision.shape = shape
	collision.position.y = float(current.height)/2
	player.add_child(collision)
	var packed := load(str(current.model)) as PackedScene
	if not packed:
		push_error("Character model could not be loaded: "+str(current.model))
		get_tree().quit(1)
		return
	visual = packed.instantiate()
	player.add_child(visual)
	anim = visual.find_child("AnimationPlayer",true,false) as AnimationPlayer
	clip_picker.clear()
	clip_picker.add_item("Automatic locomotion")
	if anim:
		for clip in anim.get_animation_list():
			if clip == "RESET":continue
			clip_picker.add_item(clip)
			if clip.get_file() in ["idle","walk","run","sprint"]:anim.get_animation(clip).loop_mode=Animation.LOOP_LINEAR
	else:failures.append("Missing AnimationPlayer")
	reset_player()

func reset_player() -> void:
	if not player:return
	player.position=Vector3(0,0.15,0)
	player.velocity=Vector3.ZERO
	manual_clip=false
	clip_picker.select(0)
	yaw=0
	pitch=-0.25
	distance=9

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_RIGHT:
			orbiting=event.pressed
			Input.mouse_mode=Input.MOUSE_MODE_CAPTURED if orbiting else Input.MOUSE_MODE_VISIBLE
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:distance=maxf(2.2,distance-0.5)
		if event.button_index == MOUSE_BUTTON_WHEEL_DOWN:distance=minf(18,distance+0.5)
	if event is InputEventMouseMotion and orbiting:
		yaw -= event.relative.x*0.004
		pitch=clampf(pitch-event.relative.y*0.004,-1.1,0.6)
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode==KEY_ESCAPE:
			orbiting=false
			Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
		if event.keycode==KEY_R:reset_player()
		if event.keycode==KEY_SPACE and player.is_on_floor():player.velocity.y=7.5

func play_clip(short_name: String) -> void:
	if not anim:return
	for clip in anim.get_animation_list():
		if clip.get_file()==short_name and anim.current_animation!=clip:
			anim.play(clip,0.18)
			return

func _physics_process(delta: float) -> void:
	if not player:return
	elapsed += delta
	var move := Vector2(float(Input.is_physical_key_pressed(KEY_D))-float(Input.is_physical_key_pressed(KEY_A)),float(Input.is_physical_key_pressed(KEY_S))-float(Input.is_physical_key_pressed(KEY_W)))
	if qa:
		move=Vector2(0,-1) if elapsed>0.5 and elapsed<2 else Vector2.ZERO
		if elapsed>1 and not qa_jumped and player.is_on_floor():
			player.velocity.y=7.5
			qa_jumped=true
		if player.position.distance_to(qa_start)>2:qa_moved=true
		if qa_jumped and elapsed>2 and player.is_on_floor():qa_landed=true
	var direction := Vector3(move.x,0,move.y).rotated(Vector3.UP,yaw).normalized()
	var speed := float(current.run_speed if Input.is_physical_key_pressed(KEY_SHIFT) else current.speed)
	if manual_clip:direction=Vector3.ZERO
	player.velocity.x=move_toward(player.velocity.x,direction.x*speed,delta*18)
	player.velocity.z=move_toward(player.velocity.z,direction.z*speed,delta*18)
	if not player.is_on_floor():player.velocity.y-=20*delta
	player.move_and_slide()
	if direction.length()>0.1:
		visual.rotation.y=lerp_angle(visual.rotation.y,atan2(direction.x,direction.z),1-exp(-delta*12))
	if not manual_clip:
		play_clip("airborne" if not player.is_on_floor() else "run" if direction.length()>0.1 and speed>5 else "walk" if direction.length()>0.1 else "idle")
	var target := player.position+Vector3(0,float(current.height)*0.63,0)
	var offset := Vector3(0,0,distance).rotated(Vector3.RIGHT,pitch).rotated(Vector3.UP,yaw)
	camera.position=target+offset
	camera.look_at(target)
	status.text="Height %.2f m · %.1f m/s\n%s · %s" % [float(current.height),Vector2(player.velocity.x,player.velocity.z).length(),"Grounded" if player.is_on_floor() else "Airborne",anim.current_animation if anim else "No animations"]
	if player.position.y < -10:reset_player()
	if qa and elapsed>4:
		if not qa_moved:failures.append("Movement failed")
		if not qa_jumped or not qa_landed:failures.append("Jump/landing failed")
		if anim and anim.get_animation_list().size()<28:failures.append("Missing animation clips")
		print("CHARACTER_LAB_QA ",JSON.stringify({"failures":failures,"moved":qa_moved,"jumped":qa_jumped,"landed":qa_landed,"clips":anim.get_animation_list().size() if anim else 0}))
		get_tree().quit(0 if failures.is_empty() else 1)
	if capture and elapsed>2:
		capture=false
		_capture.call_deferred()

func _capture() -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("res://arena-preview.png")
	get_tree().quit()
