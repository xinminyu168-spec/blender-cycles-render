from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text(encoding="utf-8")
old="gl=tree.nodes.new('CompositorNodeGlare');gl.glare_type='FOG_GLOW';gl.quality='HIGH';gl.location=(-40,40)"
new="""gl=tree.nodes.new('CompositorNodeGlare')
gl.location=(-40,40)
# Blender 5 uses menu sockets, not the removed glare_type and quality RNA properties.
gl.inputs['Type'].default_value='Fog Glow'
if 'Quality' in gl.inputs:
    gl.inputs['Quality'].default_value='High'
print('P21.4 Glare sockets:', [(i.name, i.bl_idname) for i in gl.inputs], flush=True)
sc.render.use_compositing=True"""
if s.count(old)!=1: raise RuntimeError("Expected exactly one original glare declaration")
s=s.replace(old,new)
compile(s,str(p),'exec')
p.write_text(s,encoding="utf-8")
print("Blender 5 glare compatibility patch applied")
