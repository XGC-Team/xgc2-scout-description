#!/usr/bin/env python3
"""Build reduced Scout visual meshes from the retained upstream assets (Blender 4.5)."""
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

PKG = Path(__file__).resolve().parents[1]
OUT = PKG / 'meshes' / 'visual'
NS = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
SOURCES = {'body': ('scout_mini_base_link2.dae', .06), 'wheel': ('wheel.dae', .07),
           'payload': ('box_link.STL', .10)}
bpy.ops.wm.read_factory_settings(use_empty=True)
OUT.mkdir(parents=True, exist_ok=True)
report = {'source_assets': {}, 'parts': {}, 'units': 'metres'}
materials = {}

def material(rgb):
    rgb = tuple(round(float(v), 7) for v in rgb[:3])
    key = 'scout_' + ''.join(f'{round(v*255):02x}' for v in rgb)
    if key not in materials:
        m = bpy.data.materials.new(key)
        m.diffuse_color = (*(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb), 1)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = m.diffuse_color
        bsdf.inputs['Roughness'].default_value = .65
        bsdf.inputs['Specular IOR Level'].default_value = .15
        materials[key] = (m, rgb)
    return materials[key][0]

def source_parts(path):
    if path.suffix.lower() == '.stl':
        dtype = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3,3)), ('attribute', '<u2')])
        tri = np.fromfile(path, dtype, offset=84)['vertices'].astype(float)
        # Preserve each disconnected CAD component instead of allowing a global
        # collapse budget to erase small struts, fasteners or sensor outlines.
        _, inverse = np.unique(np.round(tri.reshape(-1,3),7),axis=0,return_inverse=True)
        parent=list(range(int(inverse.max())+1))
        def find(i):
            while parent[i]!=i:
                parent[i]=parent[parent[i]];i=parent[i]
            return i
        for a,b,c in inverse.reshape(-1,3):
            a=find(int(a));parent[find(int(b))]=a;parent[find(int(c))]=a
        groups={}
        for i,vertex in enumerate(inverse.reshape(-1,3)[:,0]):groups.setdefault(find(int(vertex)),[]).append(i)
        for index,ids in enumerate(groups.values()):yield path.stem+'_'+str(index),tri[ids],material((1,1,1))
        return
    root = ET.parse(path).getroot()
    effects = {e.attrib['id']: material(list(map(float,e.findtext('.//c:diffuse/c:color',namespaces=NS).split())))
               for e in root.findall('c:library_effects/c:effect',NS)}
    mats = {m.attrib['id']: effects[m.find('c:instance_effect',NS).attrib['url'][1:]]
            for m in root.findall('c:library_materials/c:material',NS)}
    bindings = {}
    for node in root.findall('c:library_visual_scenes/c:visual_scene/c:node',NS):
        assert all(c.tag.rsplit('}',1)[-1] in ('instance_geometry','extra') for c in node), 'Unexpected source transform'
        inst = node.find('c:instance_geometry',NS)
        bindings[inst.attrib['url'][1:]] = {m.attrib['symbol']: mats[m.attrib['target'][1:]]
                                          for m in inst.findall('.//c:instance_material',NS)}
    for geo in root.findall('c:library_geometries/c:geometry',NS):
        mesh = geo.find('c:mesh',NS)
        arrays = {s.attrib['id']: np.fromstring(s.find('c:float_array',NS).text,sep=' ').reshape(-1,3)
                  for s in mesh.findall('c:source',NS)}
        sources = {s.attrib['id']: s.find('c:input',NS).attrib['source'][1:] for s in mesh.findall('c:vertices',NS)}
        for ts in mesh.findall('c:triangles',NS):
            inputs = ts.findall('c:input',NS)
            stride = max(int(i.attrib['offset']) for i in inputs)+1
            vertex = next(i for i in inputs if i.attrib['semantic']=='VERTEX')
            indices = np.fromstring(ts.find('c:p',NS).text,sep=' ',dtype=int).reshape(-1,stride)[:,int(vertex.attrib['offset'])]
            tri = arrays[sources[vertex.attrib['source'][1:]]][indices].reshape(-1,3,3)
            yield geo.attrib['id'], tri, bindings[geo.attrib['id']][ts.attrib['material']]

def clean(tri):
    area = np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)*.5
    # The payload contains a thin stray component extending >3 m from this <0.7 m vehicle.
    valid = (area > 1e-12) & (np.abs(tri).max(axis=(1,2)) < .7)
    dropped = int((~valid).sum())
    seen, result = set(), []
    for t in tri[valid]:
        key = tuple(sorted(tuple(v) for v in np.round(t,7)))
        if key in seen:
            dropped += 1
        else:
            seen.add(key)
            result.append(t)
    return np.asarray(result), dropped

def mesh_object(name, tri, mat):
    vertices, inverse = np.unique(tri.reshape(-1,3), axis=0, return_inverse=True)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices.tolist(),[],inverse.reshape(-1,3).tolist())
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name,mesh)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=1e-8)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(.1), verts=list(bm.verts),
                             edges=list(bm.edges), delimit={'NORMAL'})
    bm.to_mesh(mesh); bm.free()
    return obj

def triangle_data(objects):
    result = []
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        for tri in mesh.loop_triangles:
            vertices = [mesh.vertices[v].co.copy() for v in tri.vertices]
            if (vertices[1]-vertices[0]).cross(vertices[2]-vertices[0]).length < 1e-12:
                continue
            normals = [mesh.corner_normals[i].vector.copy() for i in tri.loops]
            result.append((obj.data.materials[tri.material_index].name,vertices,normals))
    return result

def surface_deviation(original, reduced, sample_limit=12000):
    # Deterministic vertex samples in both directions; reported as sampled, not a Hausdorff bound.
    def bvh(tri):
        return BVHTree.FromPolygons([Vector(v) for v in tri.reshape(-1,3)],
                [tuple(range(i,i+3)) for i in range(0,len(tri)*3,3)],all_triangles=True)
    first, second = bvh(original), bvh(reduced)
    distances = []
    for source, target in ((original,second),(reduced,first)):
        vertices = source.reshape(-1,3)
        for v in vertices[::max(1,len(vertices)//sample_limit)]:
            hit = target.find_nearest(Vector(v))
            if hit[0] is not None: distances.append(hit[3])
    return {'samples':len(distances),'max_m':max(distances),'p99_m':float(np.percentile(distances,99))}

def numbers(values): return ' '.join(f'{v:.9g}' for v in values)
def sub(parent,tag,text=None,**attrib):
    e=ET.SubElement(parent,tag,attrib)
    if text is not None:e.text=str(text)
    return e

def export_dae(path, data):
    root=ET.Element('COLLADA',xmlns=NS['c'],version='1.4.1')
    asset=sub(root,'asset');sub(asset,'created','2026-09-14T00:00:00Z');sub(asset,'modified','2026-09-14T00:00:00Z')
    sub(asset,'unit',name='metre',meter='1');sub(asset,'up_axis','Z_UP')
    effectlib=sub(root,'library_effects');matlib=sub(root,'library_materials')
    used=sorted({m for m,_,_ in data})
    for name in used:
        rgb=materials[name][1];phong=sub(sub(sub(sub(effectlib,'effect',id=name+'_effect'),'profile_COMMON'),'technique',sid='common'),'phong')
        for tag,color in [('emission',(0,0,0,1)),('ambient',(*[v*.5 for v in rgb],1)),('diffuse',(*rgb,1)),('specular',(.035,.035,.035,1))]:
            sub(sub(phong,tag),'color',numbers(color))
        sub(sub(phong,'shininess'),'float','24')
        sub(sub(matlib,'material',id=name,name=name),'instance_effect',url='#'+name+'_effect')
    mesh=sub(sub(sub(root,'library_geometries'),'geometry',id='geometry',name=path.stem),'mesh')
    indices_by_attribute={}
    for label,part in [('positions',1),('normals',2)]:
        values, lookup, indices = [], {}, []
        for item in data:
            for value in item[part]:
                key=tuple(value)
                if key not in lookup:
                    lookup[key]=len(values);values.append(key)
                indices.append(lookup[key])
        indices_by_attribute[label]=indices
        source=sub(mesh,'source',id=label);sub(source,'float_array',numbers(c for v in values for c in v),id=label+'_array',count=str(len(values)*3))
        accessor=sub(sub(source,'technique_common'),'accessor',source='#'+label+'_array',count=str(len(values)),stride='3')
        for name in 'XYZ':sub(accessor,'param',name=name,type='float')
    sub(sub(mesh,'vertices',id='vertices'),'input',semantic='POSITION',source='#positions')
    for name in used:
        indices=[i for i,t in enumerate(data) if t[0]==name]
        ts=sub(mesh,'triangles',material=name,count=str(len(indices)))
        sub(ts,'input',semantic='VERTEX',source='#vertices',offset='0');sub(ts,'input',semantic='NORMAL',source='#normals',offset='1')
        sub(ts,'p',' '.join(str(indices_by_attribute[attr][i*3+j]) for i in indices for j in range(3) for attr in ('positions','normals')))
    scene=sub(sub(root,'library_visual_scenes'),'visual_scene',id='scene');node=sub(scene,'node',id=path.stem)
    common=sub(sub(sub(node,'instance_geometry',url='#geometry'),'bind_material'),'technique_common')
    for name in used:sub(common,'instance_material',symbol=name,target='#'+name)
    sub(sub(root,'scene'),'instance_visual_scene',url='#scene')
    ET.indent(root);ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)

# Component indices are stable only for these retained upstream files.
SOURCE_HASHES = {
    'body': '3db98aba69d8ba26e1c2177646ba2a12c6725ff9dc99efe06cf4d2be87f23204', 'wheel': 'c64ae34e44118f07d718d54199107ce430a006d1cd9fd96bb80968954b5a8ce7', 'payload': '033cd0ce9f4661576e3ba42fdabb3fd2d630c472d6057ae421793090638b6ec3',
}
PALETTE = {
    'shell': (.86,.87,.83), 'alloy': (.72,.73,.71),
    'dark': (.10,.12,.13), 'glass': (.065,.08,.105),
    'rubber': (.22,.23,.23), 'red': (.69,.08,.14),
}
SOURCE_PALETTE = {
    'scout_ffffff': 'shell', 'scout_000000': 'dark', 'scout_696969': 'dark',
    'scout_cccccc': 'alloy', 'scout_e5eaed': 'alloy',
    'scout_4b4b4b': 'rubber', 'scout_ff0f0f': 'red',
    'scout_ff0d12': 'red', 'scout_ffb20f': 'red', 'scout_ffb22e': 'red',
}
# Equipment enclosed by the lower cover; no exterior mounting structure is removed.
PAYLOAD_OMIT = {8,9,14,16,18,19,20,21,22,23,24,25,1324,1325,1326,1327}
PAYLOAD_BOXES = {0,5,6,7,10,13,15,1316,1319}
ERROR_LIMIT = {'body': .0025, 'wheel': .002, 'payload': .0015}

def finish(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    for face in bm.faces:face.smooth=True
    for edge in bm.edges:
        if edge.is_manifold and edge.calc_face_angle(0)>math.radians(35):edge.smooth=False
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    return obj

def simple_box(name, tri, mat):
    lo=tri.min(axis=(0,1));hi=tri.max(axis=(0,1));center=(lo+hi)/2;size=hi-lo
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj=bpy.context.object;obj.name=name
    for v in obj.data.vertices:v.co=Vector(center)+Vector([v.co[i]*size[i] for i in range(3)])
    obj.data.materials.append(mat)
    # Rounded equipment covers retain readable edges without modelling PCB internals.
    bevel=obj.modifiers.new('Equipment cover edges','BEVEL')
    bevel.width=min(.001,float(size.min())*.12);bevel.segments=1
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    return finish(obj)

def lathe(name, rings, center, mats, slots, segments=64):
    n=segments
    vertices=[(center[0]+r*math.cos(i*2*math.pi/n),center[1]+r*math.sin(i*2*math.pi/n),z)
              for z,r in rings for i in range(n)]
    faces=[tuple(reversed(range(n)))];indices=[0]
    for ring in range(len(rings)-1):
        for i in range(n):
            faces.append((ring*n+i,ring*n+(i+1)%n,(ring+1)*n+(i+1)%n,(ring+1)*n+i))
            indices.append(slots[ring])
    faces.append(tuple(range((len(rings)-1)*n,len(rings)*n)));indices.append(0)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces)
    for mat in mats:mesh.materials.append(mat)
    for face,index in zip(mesh.polygons,indices):face.material_index=index
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    return finish(obj)

def lidar():
    # One contiguous scan housing, with the original CAD axis and 100 mm envelope.
    rings=[(.2008,.048),(.203,.05),(.218,.05),(.221,.0495),
           (.284,.0495),(.285,.0495),(.2978,.0495),(.3008,.047)]
    return lathe('lidar_housing',rings,(.00984364,-.0012552),
                 [material(PALETTE['alloy']),material(PALETTE['glass'])], [0,0,0,1,1,0,0])

def wheel_hub(tri, mat):
    lo=tri.min(axis=(0,1));hi=tri.max(axis=(0,1))
    # Wide flange stays inside the tire; only the axle-sized cap reaches the outer rim.
    rings=[(float(lo[2]),.012),(.025,.012),(.027,.054),(.051,.054),(.053,.012),(float(hi[2]),.012)]
    return lathe('internal_wheel_hub',rings,(0,-.001),[mat],[0]*5,48)

def camera_materials(obj):
    obj.data.materials.append(material(PALETTE['glass']))
    # Colour existing front faces, avoiding a coplanar decal / duplicate surface.
    for face in obj.data.polygons:
        if face.center.x>.202 and face.normal.x>.3:face.material_index=1

for part,(filename,ratio) in SOURCES.items():
    source=PKG/'meshes'/filename
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    if sha!=SOURCE_HASHES[part]:raise RuntimeError('Upstream mesh changed; review semantic component map: '+filename)
    report['source_assets'][filename]={'sha256':sha,'bytes':source.stat().st_size}
    objects, retained, original, component_report = [], [], [], []
    input_count=removed=omitted_count=omitted_triangles=0
    for name,tri,mat in source_parts(source):
        input_count+=len(tri);tri,dropped=clean(tri);removed+=dropped
        if not len(tri):continue
        if mat.name in SOURCE_PALETTE:mat=material(PALETTE[SOURCE_PALETTE[mat.name]])
        action='retained';index=None
        if part=='payload':
            index=int(name.rsplit('_',1)[1])
            if (27<=index<=1318 and index!=1316) or index in PAYLOAD_OMIT:
                omitted_count+=1;omitted_triangles+=len(tri);continue
            mat=material(PALETTE['alloy'])
            if index in PAYLOAD_BOXES or index in (1331,1332,1333):mat=material(PALETTE['dark'])
            if index in (1,2):mat=material(PALETTE['shell'])
            if index==17:obj=lidar();action='scan_housing'
            elif index in PAYLOAD_BOXES:obj=simple_box(name,tri,mat);action='equipment_cover'
        if part=='wheel' and name=='geometry6':obj=wheel_hub(tri,mat);action='internal_hub'
        if action=='retained':
            original.append(tri)
            obj=mesh_object(part+'_'+name,tri,mat)
            bpy.context.view_layer.objects.active=obj
            original_mesh=obj.data.copy()
            candidate_ratio=min(1,max(ratio,12/max(1,len(tri))))
            while True:
                mod=obj.modifiers.new('Reduce component tessellation','DECIMATE')
                mod.ratio=candidate_ratio;mod.use_collapse_triangulate=True
                bpy.ops.object.modifier_apply(modifier=mod.name)
                obj.data.calc_loop_triangles()
                candidate=np.array([[tuple(obj.data.vertices[v].co) for v in t.vertices] for t in obj.data.loop_triangles])
                if candidate_ratio>=1 or surface_deviation(tri,candidate,2000)['max_m']<=ERROR_LIMIT[part]:break
                discarded=obj.data;obj.data=original_mesh.copy();bpy.data.meshes.remove(discarded)
                candidate_ratio=min(1,candidate_ratio*2)
            bpy.data.meshes.remove(original_mesh)
            finish(obj)
            if part=='payload' and index==2:camera_materials(obj)
            retained.append(obj)
        objects.append(obj)
        component_report.append({'source':name,'action':action,'source_triangles':len(tri),
                                 'triangles':len(triangle_data([obj]))})
    data=triangle_data(objects)
    reduced=np.array([[tuple(v) for v in t[1]] for t in data])
    retained_data=np.array([[tuple(v) for v in t[1]] for t in triangle_data(retained)])
    deviation=surface_deviation(np.concatenate(original),retained_data)
    if deviation['max_m']>.003:raise RuntimeError('Retained surface exceeds 3 mm sampled deviation: '+part)
    export_dae(OUT/(part+'.dae'),data)
    report['parts'][part]={'source_triangles':input_count,'removed_duplicate_degenerate_or_stray_triangles':removed,
        'omitted_internal_components':omitted_count,'omitted_internal_triangles':omitted_triangles,
        'triangles':len(data),'materials':len({m for m,_,_ in data}),
        'bounds_m':[reduced.min(axis=(0,1)).tolist(),reduced.max(axis=(0,1)).tolist()],
        'retained_sampled_surface_deviation':deviation,'components':component_report}
    print('SCOUT_PART',part,len(data),'retained sampled max m',deviation['max_m'],flush=True)
report['vehicle_triangles']=report['parts']['body']['triangles']+report['parts']['payload']['triangles']+4*report['parts']['wheel']['triangles']
report['source_vehicle_triangles']=747538
report['deviation_scope']='Retained CAD surfaces only; semantic equipment covers, axle and lidar replacements are recorded separately.'
assert report['vehicle_triangles']<50000,report['vehicle_triangles']
(PKG/'modeling/geometry_report.json').write_text(json.dumps(report,indent=2)+'\n')
print('SCOUT_OPTIMIZED',report['vehicle_triangles'],flush=True)
