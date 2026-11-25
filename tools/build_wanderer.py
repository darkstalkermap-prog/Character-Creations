"""Assemble Giantborn's Wanderer into portable exports and an editable Blender scene.
Run with Blender 5.3's Python (bpy), numpy and Pillow installed.
"""
from pathlib import Path
import sys, json, math, os
import bpy
from mathutils import Vector
from PIL import Image
import numpy as np
import shutil

ROOT=Path(__file__).resolve().parents[1]
CHAR=ROOT/'characters/giantborn-wanderer'
ASSET=CHAR/'source/assets/giant'
TEX=CHAR/'textures'
BAKE=CHAR/'textures/bake'
for p in [TEX,CHAR/'exports',CHAR/'authoring',CHAR/'previews']: p.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.render.fps=60

def imported(path):
    old=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return set(bpy.data.objects)-old

objects=imported(ASSET/'giant.glb')
rig=next(o for o in objects if o.type=='ARMATURE')
for o in list(objects):
    if o.type=='MESH' and (o.name=='ShadowProxy' or o.name=='Icosphere'):
        bpy.data.objects.remove(o,do_unlink=True)
parts=['Hair_long_back','Beard_full','Garment_braies_core','Garment_braies_limbs','Garment_belt']
for part in parts:
    new=imported(ASSET/'parts'/f'{part}.glb')
    armatures=[o for o in new if o.type=='ARMATURE']
    for o in new:
        if o.type=='MESH' and o.name.startswith(part):
            world=o.matrix_world.copy();o.parent=rig;o.matrix_world=world
            for m in o.modifiers:
                if m.type=='ARMATURE':m.object=rig
        elif o.type!='ARMATURE':
            bpy.data.objects.remove(o,do_unlink=True)
    for o in armatures:bpy.data.objects.remove(o,do_unlink=True)
new=imported(ASSET/'giant_clips.glb')
actions=list(bpy.data.actions)
for a in actions:a.use_fake_user=True
for o in new:bpy.data.objects.remove(o,do_unlink=True)
rig.animation_data_create()
for a in actions:
    track=rig.animation_data.nla_tracks.new();track.name=a.name
    strip=track.strips.new(a.name,0,a);track.mute=True
rig.animation_data.action=bpy.data.actions['idle']
rig.animation_data.action_slot=bpy.data.actions['idle'].slots[0]

def mat(name,color,rough=.5,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m,p
def image_node(m,path,noncolor=False):
    im=bpy.data.images.load(str(path),check_existing=True)
    if noncolor: im.colorspace_settings.name='Non-Color'
    n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=im;return n

# The source's ORM blue channel is thickness, NOT metallic. Repack for standard PBR.
orm=np.array(Image.open(ASSET/'tex_hi/orm.png').convert('RGB'))
rough_source=np.array(Image.open(BAKE/'rough.png').convert('L')) if (BAKE/'rough.png').exists() else orm[:,:,1]
Image.fromarray(np.maximum(rough_source,145).astype('uint8')).save(TEX/'skin_roughness.png')
for name,src in [('skin_albedo.png',BAKE/'albedo.png'),('skin_normal.png',BAKE/'normal.png')]:
    shutil.copy2(src if src.exists() else ASSET/('tex/albedo.png' if 'albedo' in name else 'tex_hi/normal.png'),TEX/name)
base=Image.open(TEX/'skin_albedo.png').convert('RGB')
masks=np.asarray(Image.open(ASSET/'tex/masks.png').convert('RGBA').resize(base.size,Image.Resampling.BILINEAR)).astype(float)/255
tint=np.maximum.reduce([masks[:,:,0]*.42,masks[:,:,1]*.88,masks[:,:,2]*.8])[:,:,None]
col=np.asarray(base).astype(float)*(1-tint)+np.array([58,34,21])*tint
Image.fromarray(np.clip(col,0,255).astype('uint8')).save(TEX/'skin_albedo.png')
skin,p=mat('Wanderer | skin',(.55,.36,.27),.48)
al=image_node(skin,TEX/'skin_albedo.png');skin.node_tree.links.new(al.outputs['Color'],p.inputs['Base Color'])
p.inputs['Specular IOR Level'].default_value=.25
rough=image_node(skin,TEX/'skin_roughness.png',True);skin.node_tree.links.new(rough.outputs['Color'],p.inputs['Roughness'])
normal=image_node(skin,TEX/'skin_normal.png',True)
nm=skin.node_tree.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.8
skin.node_tree.links.new(normal.outputs['Color'],nm.inputs['Color']);skin.node_tree.links.new(nm.outputs['Normal'],p.inputs['Normal'])
p.inputs['Subsurface Weight'].default_value=.075;p.inputs['Subsurface Radius'].default_value=(1,.45,.22)
p.inputs['Subsurface Scale'].default_value=.018

# Bake the atlas's strand brightness into a conventional RGBA texture for portability.
atlas=np.array(Image.open(ASSET/'hair_atlas.png').convert('RGBA')).astype(float)/255
rgb=np.array([.29,.173,.102])[None,None,:]*(.6+.8*atlas[:,:,:1])
hair_rgba=np.concatenate([np.clip(rgb,0,1),atlas[:,:,3:4]],axis=2)
Image.fromarray((hair_rgba*255).astype('uint8')).save(TEX/'hair_basecolor.png')
hair,hp=mat('Wanderer | chestnut strands',(.08,.035,.015),.8)
hp.inputs['Specular IOR Level'].default_value=.08
hi=image_node(hair,TEX/'hair_basecolor.png');hair.node_tree.links.new(hi.outputs['Color'],hp.inputs['Base Color']);hair.node_tree.links.new(hi.outputs['Alpha'],hp.inputs['Alpha'])
hair.surface_render_method='DITHERED';hair.use_backface_culling=False
cloth,cp=mat('Wanderer | undyed linen',(.25,.21,.15),.85)
leather,lp=mat('Wanderer | worn leather',(.055,.027,.015),.62)
for m,p,tex in [(cloth,cp,'cloth_weave.png'),(leather,lp,'cloth_leather.png')]:
    n=image_node(m,ASSET/tex,True)
    bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.15;bump.inputs['Distance'].default_value=.001
    m.node_tree.links.new(n.outputs['Color'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])

# An iris texture on the source eyes' spherical UVs.
size=512;v,u=np.mgrid[0:size,0:size]/(size-1);r=v
iris=np.zeros((size,size,4),dtype=np.uint8);iris[:,:,:3]=[210,199,182];iris[:,:,3]=255
mask=r<.23;fib=(np.sin(u*2*math.pi*91+r*40)*.5+.5)
for k,c in enumerate([80,104,86]):iris[:,:,k]=np.where(mask,c+fib*30,iris[:,:,k])
iris[r<.09,:3]=8
Image.fromarray(iris).save(TEX/'eyes_basecolor.png')
eyes,ep=mat('Wanderer | grey green eyes',(.55,.6,.52),.17)
ei=image_node(eyes,TEX/'eyes_basecolor.png');eyes.node_tree.links.new(ei.outputs['Color'],ep.inputs['Base Color'])
ep.inputs['Coat Weight'].default_value=.4
for o in bpy.data.objects:
    if o.type!='MESH':continue
    material=skin if o.name.startswith('Body_') else eyes if o.name.startswith('Eyes') else hair if o.name.startswith(('Hair_','Beard_')) else leather if 'belt' in o.name else cloth
    o.data.materials.clear();o.data.materials.append(material)
    for poly in o.data.polygons:poly.use_smooth=True

character=[o for o in bpy.data.objects if o.type in ('MESH','ARMATURE')]
sc.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
for o in character:o.select_set(True)
bpy.context.view_layer.objects.active=rig
# No export of COLOR_0: it holds game masks, not display colours. Originals retain it.
bpy.ops.export_scene.gltf(filepath=str(CHAR/'exports/wanderer.glb'),export_format='GLB',use_selection=True,
    export_animations=True,export_animation_mode='ACTIONS',export_anim_single_armature=True,
    export_morph=True,export_all_vertex_colors=False,export_active_vertex_color_when_no_material=False,
    export_materials='EXPORT',export_extras=True)

# FBX for DCC/Unreal retargeting; textures also supplied separately.
bpy.ops.export_scene.fbx(filepath=str(CHAR/'exports/wanderer.fbx'),use_selection=True,
    object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=True,
    bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,
    path_mode='COPY',embed_textures=True,axis_forward='-Z',axis_up='Y')

# Authoring scene adds non-destructive skin microdetail; exports above use baked source normals.
noise=skin.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1150
noise.inputs['Detail'].default_value=2
bump=skin.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.00045
skin.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);skin.node_tree.links.new(nm.outputs['Normal'],bump.inputs['Normal'])
skin.node_tree.links.new(bump.outputs['Normal'],skin.node_tree.nodes.get('Principled BSDF').inputs['Normal'])
rig.animation_data.action=bpy.data.actions['idle'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];sc.frame_set(0)

# Unified quad body for smooth authoring/rendering. Preserve the game's original split meshes
# in the portable exports above. Rebuild from the exact same anatomical source and weights.
sys.path.insert(0,str(CHAR/'source/tools/giant/kit'))
import giant_body as gb
import mh_data as mh
if os.name=='nt':
    mh.MPFB_DIR='\\\\?\\'+str((CHAR/'source/tools/giant/mpfb2').resolve())
    mh.target_path=lambda rel:os.path.normpath(os.path.join(mh.MPFB_DIR,mh.target_rel(rel)))
from mathutils.kdtree import KDTree
bd=gb.BodyData()
body=gb.build_body_object(bd,'Wanderer_StudioBody',sc.collection,mh.load_weights(),gb.STAGE1_HEIGHT_M/bd.height)
gb.parent_keep(body,rig);gb.armature_modifier(body,rig,preserve_volume=False)
body.data.materials.append(skin)
originals=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('Body_')]
head=next(o for o in originals if o.name=='Body_Head')
if head.data.shape_keys:
    tree=KDTree(len(head.data.vertices))
    for v in head.data.vertices:tree.insert(head.matrix_world @ v.co,v.index)
    tree.balance()
    body.shape_key_add(name='Basis')
    for key in list(head.data.shape_keys.key_blocks)[1:]:
        target=body.shape_key_add(name=key.name)
        for v in body.data.vertices:
            _,index,dist=tree.find(body.matrix_world @ v.co)
            if dist<0.0001:
                delta=key.data[index].co-head.data.vertices[index].co
                target.data[v.index].co += head.matrix_world.to_3x3() @ delta
sub=body.modifiers.new('Studio surface refinement','SUBSURF');sub.levels=1;sub.render_levels=2
for o in originals:o.hide_render=True;o.hide_set(True)
for o in bpy.data.objects:
    if o.type=='MESH' and o.data.shape_keys:
        for key in o.data.shape_keys.key_blocks:key.value=0

def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
floor,f=mat('Studio | charcoal',(.025,.033,.043),.8)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.015));bpy.context.object.name='Studio floor';bpy.context.object.data.materials.append(floor)
for name,loc,power,color,size in [('Key',(-4,-5,6),1500,(1,.86,.73),4),('Fill',(4,-2,4),900,(.66,.79,1),3),('Rim',(1,3,5),1800,(.8,.9,1),3)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=loc;aim(o,(0,0,2))
d=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',d);sc.collection.objects.link(cam);sc.camera=cam
cam.location=(5,-9,3.5);aim(cam,(0,0,1.9));d.type='ORTHO';d.ortho_scale=4.6
sc.world=bpy.data.worlds.new('Studio World');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.07,.085,.11,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.35
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.render.threads_mode='FIXED';sc.render.threads=8
sc.render.resolution_x=1000;sc.render.resolution_y=1200;sc.render.resolution_percentage=100
sc.view_settings.view_transform='AgX';sc.render.image_settings.file_format='PNG'
sc.frame_start=0;sc.frame_end=120
for im in bpy.data.images:
    if im.source=='FILE':im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(CHAR/'authoring/wanderer.blend'))
sc.render.filepath=str(CHAR/'previews/wanderer.png');bpy.ops.render.render(write_still=True)
cam.location=(1.5,-6,3.55);aim(cam,(0,0,3.25));d.ortho_scale=1.2
sc.render.resolution_x=1000;sc.render.resolution_y=1000
sc.render.filepath=str(CHAR/'previews/portrait.png');bpy.ops.render.render(write_still=True)
print('BUILD COMPLETE',flush=True)
