"""P23 tile pilot: full-resolution camera, padded crop, linear EXR and display PNG.
Run against a packed P22 blend, not against the original GLB.
"""
import argparse, json, sys, time, struct
from pathlib import Path
import bpy

p=argparse.ArgumentParser()
p.add_argument('--x',type=int,default=1)
p.add_argument('--y',type=int,default=2)
p.add_argument('--frame',type=int,default=150)
p.add_argument('--samples',type=int,default=1024)
p.add_argument('--seconds',type=int,default=900)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
assert 0<=a.x<4 and 0<=a.y<4 and 0<=a.frame<=299
assert 1<=a.samples<=1024 and 60<=a.seconds<=3600
sc=bpy.context.scene
assert sc.camera and sc.render.engine=='CYCLES'
W,H=3840,2160
pad=64
x0,y0=a.x*960,a.y*540
x1,y1=x0+960,y0+540
left,bottom=max(0,x0-pad),max(0,y0-pad)
right,top=min(W,x1+pad),min(H,y1+pad)
out=Path('project/tile_output').resolve()
out.mkdir(parents=True,exist_ok=True)
stem=f'frame_{a.frame:04d}_x{a.x}_y{a.y}'
sc.frame_set(a.frame)
sc.render.resolution_x=W
sc.render.resolution_y=H
sc.render.resolution_percentage=100
sc.render.use_border=True
sc.render.use_crop_to_border=True
sc.render.border_min_x=left/W
sc.render.border_max_x=right/W
sc.render.border_min_y=bottom/H
sc.render.border_max_y=top/H
# Apply the P22 scene lighting/materials without tile-local glare.
# Reapply the original compositor once to the joined scene-linear image.
sc.render.use_compositing=False
sc.render.use_sequencer=False
sc.cycles.device='CPU'
sc.cycles.samples=a.samples
sc.cycles.time_limit=float(a.seconds)
sc.cycles.use_adaptive_sampling=True
sc.cycles.adaptive_threshold=.008
sc.cycles.use_denoising=True
sc.render.image_settings.file_format='OPEN_EXR'
sc.render.image_settings.color_mode='RGB'
sc.render.image_settings.color_depth='16'
sc.render.image_settings.exr_codec='ZIP'
exr=out/(stem+'.exr')
png=out/(stem+'.png')
sc.render.filepath=str(exr)
qa=dict(frame=a.frame,tile=[a.x,a.y],grid=[4,4],full_resolution=[W,H],
        core_bounds_bottom_origin=[x0,y0,x1,y1],padded_bounds_bottom_origin=[left,bottom,right,top],
        expected_crop=[right-left,top-bottom],padding=pad,maximum_samples=a.samples,
        sampling_time_limit_seconds=a.seconds,engine=sc.render.engine,device=sc.cycles.device,
        compositor_applied=False,complete=False)
qpath=out/(stem+'.json')
def write():
    qpath.write_text(json.dumps(qa,indent=2))
write()
print('P23_TILE_START',json.dumps(qa),flush=True)
t=time.monotonic()
bpy.ops.render.render(write_still=True)
qa['elapsed_seconds']=time.monotonic()-t
assert exr.is_file() and exr.stat().st_size>0
sc.render.image_settings.file_format='PNG'
sc.render.image_settings.color_mode='RGB'
sc.render.image_settings.color_depth='16'
bpy.data.images['Render Result'].save_render(str(png),scene=sc)
with png.open('rb') as f: h=f.read(29)
assert h[:8]==bytes.fromhex('89504e470d0a1a0a')
size=list(struct.unpack('>II',h[16:24]))
# Blender border coordinates are floats; a one-pixel deviation is a failure for exact stitching.
assert size==qa['expected_crop'],(size,qa['expected_crop'])
assert h[24]==16 and h[25]==2
qa.update(actual_crop=size,exr_bytes=exr.stat().st_size,png_bytes=png.stat().st_size,complete=True)
write()
print('P23_TILE_COMPLETE',json.dumps(qa),flush=True)
