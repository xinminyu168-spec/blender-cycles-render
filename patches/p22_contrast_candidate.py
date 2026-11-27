"""P22 candidate A: independent art-direction variant; run AFTER the Blender 5 glare patch.
Does not edit GLB, textures, camera, animation, or original archive.
Usage: python patches/p22_contrast_candidate.py project/21_build_render.py
"""
from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text(encoding="utf-8")
marker="# P12 final quality and deliverables. Reconstruction settings, not source video values."
if s.count(marker)!=1: raise RuntimeError("Unexpected P21 builder")
if "P22_CONTRAST_CANDIDATE" in s: raise RuntimeError("P22 already applied")
block=r'''
# P22_CONTRAST_CANDIDATE: proposed settings, to be checked against P21 rendered frames.
# Preserve low lateral haze; reduce global wash and upper haze.
p22_changes={}
def p22_set(socket, value, label):
    p22_changes[label]={"before":float(socket.default_value),"after":float(value)}
    socket.default_value=value
fog_mat=bpy.data.materials['P09_Fog']
fog_node=next(n for n in fog_mat.node_tree.nodes if n.type=='PRINCIPLED_VOLUME')
p22_set(fog_node.inputs['Density'],.0035,'global_fog_density')
upper=bpy.data.materials['P16_Upper energy haze_Volume']
volume_node=next(n for n in upper.node_tree.nodes if n.type=='PRINCIPLED_VOLUME')
density_node=volume_node.inputs['Density'].links[0].from_node
p22_set(density_node.inputs[1],.003,'upper_haze_peak_density')
# The visible background should not reflect scene lights: use its existing texture
# with a pure emission surface rather than a lit Principled BSDF.
bgmat=bpy.data.materials['P09_Background_Manual']
bnt=bgmat.node_tree
btex=next(n for n in bnt.nodes if n.type=='TEX_IMAGE')
bout=next(n for n in bnt.nodes if n.type=='OUTPUT_MATERIAL')
bem=bnt.nodes.new('ShaderNodeEmission')
bem.label='P22 independent star background'
bem.inputs['Strength'].default_value=1.0
bnt.links.new(btex.outputs['Color'],bem.inputs['Color'])
bnt.links.new(bem.outputs['Emission'],bout.inputs['Surface'])
# Reduce HDR ambient fill and road coat without removing physical reflections.
p22_set(sc.world.node_tree.nodes.get('Background').inputs['Strength'],.32,'hdr_strength')
rp=next(n for n in bpy.data.materials['P08_Road_Reflective'].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
p22_set(rp.inputs['Coat Weight'],.25,'road_coat_weight')
# Modest energy increase; preserve original texture and alpha/transmission.
for mn in ('P08_outer_Energy','P08_middle_Energy'):
    bp=next(n for n in bpy.data.materials[mn].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    ep=bp.inputs['Emission Strength']
    if not ep.is_linked:
        p22_set(ep,float(ep.default_value)*1.30,mn+'_emission')
    else:
        old=ep.links[0].from_socket
        m=bp.id_data.nodes.new('ShaderNodeMath');m.operation='MULTIPLY';m.inputs[1].default_value=1.30
        bp.id_data.links.new(old,m.inputs[0]);bp.id_data.links.new(m.outputs[0],ep)
        p22_changes[mn+'_emission']={'multiplier':1.30}
print('P22_ART_DIRECTION',json.dumps(p22_changes),flush=True)
(D/'p22_changes.json').write_text(json.dumps(p22_changes,indent=2),encoding='utf-8')
'''
out=s.replace(marker,block+"\n"+marker)
compile(out,str(p),'exec')
p.write_text(out,encoding="utf-8")
print("P22 contrast candidate injected; runtime QA still required")
