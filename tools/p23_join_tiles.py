"""Assemble 16 scene-linear Cycles EXR tiles. Run with Blender 5.0.1 Python.
Usage: blender -b P22.blend --python-exit-code 1 --python tools/p23_join_tiles.py -- --tiles TILE_DIR --out OUTPUT_DIR --frame 150
The original compositor is reused on the assembled linear image.
"""
import argparse, sys, json, struct
from pathlib import Path
import bpy
import numpy as np
p=argparse.ArgumentParser()
p.add_argument('--tiles',required=True,type=Path)
p.add_argument('--out',required=True,type=Path)
p.add_argument('--frame',type=int,default=150)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
W,H=3840,2160
canvas=np.zeros((H,W,4),dtype=np.float32)
covered=np.zeros((H,W),dtype=np.uint8)
records=[]
for y in range(4):
    for x in range(4):
        stem=f'frame_{a.frame:04d}_x{x}_y{y}'
        q=json.loads((a.tiles/(stem+'.json')).read_text())
        assert q['complete'] and q['frame']==a.frame and q['tile']==[x,y]
        assert q['full_resolution']==[W,H] and q['grid']==[4,4]
        assert q['engine']=='CYCLES' and not q['compositor_applied']
        assert q['maximum_samples']==1024
        x0,y0,x1,y1=q['core_bounds_bottom_origin']
        l,b,r,t=q['padded_bounds_bottom_origin']
        assert [x0,y0,x1,y1]==[x*960,y*540,(x+1)*960,(y+1)*540]
        assert 0<=l<=x0<x1<=r<=W and 0<=b<=y0<y1<=t<=H
        im=bpy.data.images.load(str((a.tiles/(stem+'.exr')).resolve()),check_existing=False)
        assert im.is_float and list(im.size)==[r-l,t-b]
        # Blender image pixels and render border both use bottom-left origin.
        pix=np.empty((t-b)*(r-l)*4,dtype=np.float32)
        im.pixels.foreach_get(pix)
        crop=pix.reshape(t-b,r-l,4)[y0-b:y1-b,x0-l:x1-l]
        assert np.isfinite(crop).all()
        assert not covered[y0:y1,x0:x1].any()
        canvas[y0:y1,x0:x1]=crop
        covered[y0:y1,x0:x1]=1
        records.append(q)
        bpy.data.images.remove(im)
assert covered.all()
a.out.mkdir(parents=True,exist_ok=True)
sc=bpy.context.scene
sc.frame_set(a.frame)
im=bpy.data.images.new('P23_JoinedLinear',width=W,height=H,alpha=True,float_buffer=True)
im.colorspace_settings.name='Linear Rec.709'
im.pixels.foreach_set(canvas.ravel())
im.update()
sc.render.image_settings.file_format='OPEN_EXR'
sc.render.image_settings.color_mode='RGB'
sc.render.image_settings.color_depth='16'
linear=a.out/'P23_joined_linear.exr'
im.save_render(str(linear.resolve()),scene=sc)
# Switch Render Layers image output to the assembled image on a copy of the
# existing P22 compositor. This preserves its glare and color settings.
tree=sc.compositing_node_group
assert tree is not None
tree=tree.copy()
sc.compositing_node_group=tree
rls=[n for n in tree.nodes if n.bl_idname=='CompositorNodeRLayers']
assert len(rls)==1
rl=rls[0]
links=[(lk.to_socket,lk.from_socket.name) for lk in tree.links if lk.from_node==rl]
assert links and all(name=='Image' for _,name in links)
node=tree.nodes.new('CompositorNodeImage')
node.image=im
for target,_ in links: tree.links.new(node.outputs['Image'],target)
tree.nodes.remove(rl)
# A tiny empty render provides the compositor execution trigger; the image
# node supplies the full-resolution domain. Use a separate scene to avoid
# tracing the original 4K geometry again.
dummy=bpy.data.scenes.new('P23_CompositorOnly')
dummy.render.engine='CYCLES'
dummy.cycles.samples=1
cam=bpy.data.cameras.new('P23_DummyCamera')
obj=bpy.data.objects.new('P23_DummyCamera',cam)
dummy.collection.objects.link(obj)
dummy.camera=obj
dummy.compositing_node_group=tree
dummy.render.use_compositing=True
dummy.render.resolution_x=W
dummy.render.resolution_y=H
dummy.render.resolution_percentage=100
dummy.render.image_settings.file_format='PNG'
dummy.render.image_settings.color_mode='RGB'
dummy.render.image_settings.color_depth='16'
dummy.view_settings.view_transform=sc.view_settings.view_transform
dummy.view_settings.look=sc.view_settings.look
dummy.view_settings.exposure=sc.view_settings.exposure
dummy.view_settings.gamma=sc.view_settings.gamma
png=a.out/'P23_final_4k.png'
dummy.render.filepath=str(png.resolve())
bpy.ops.render.render(scene=dummy.name,write_still=True)
with png.open('rb') as f: h=f.read(29)
assert h[:8]==bytes.fromhex('89504e470d0a1a0a')
assert struct.unpack('>II',h[16:24])==(W,H)
assert h[24]==16 and h[25]==2
(a.out/'join_qa.json').write_text(json.dumps(dict(complete=True,frame=a.frame,tiles=16,
resolution=[W,H],coverage_pixels=int(covered.sum()),compositor='P22 copied original',
png_bytes=png.stat().st_size,linear_exr_bytes=linear.stat().st_size,
max_samples=1024,samples_are_maximum=True),indent=2))
print('P23_JOIN_COMPLETE',flush=True)
