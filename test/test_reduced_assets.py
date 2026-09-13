#!/usr/bin/env python3
"""Reduced visuals retain material regions and the Scout's external scale."""
import hashlib
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

PKG=Path(__file__).resolve().parents[1]
NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}

class ReducedAssetsTest(unittest.TestCase):
    def test_default_description_uses_shared_reduced_assets(self):
        robot=ET.parse(PKG/'urdf/scout_visual.urdf').getroot()
        paths=[m.get('filename') for m in robot.findall('.//visual/geometry/mesh')]
        self.assertEqual(len(paths),6)
        self.assertEqual(set(paths),{'package://scout_description/meshes/lod10k/'+p+'.dae' for p in ('body','wheel','payload')})

    def test_upstream_sources_are_retained_and_semantic_replacements_are_explicit(self):
        report=json.loads((PKG/'modeling/geometry_report.json').read_text())
        for filename, source in report['source_assets'].items():
            self.assertEqual(hashlib.sha256((PKG/'meshes'/filename).read_bytes()).hexdigest(),source['sha256'])
        payload=report['parts']['payload']
        self.assertGreater(payload['omitted_internal_components'],1200)
        actions={c['source']:c['action'] for c in payload['components']}
        self.assertEqual(actions['box_link_17'],'scan_housing')
        for exterior in ('box_link_2','box_link_3','box_link_1330','box_link_1331','box_link_1334'):
            self.assertEqual(actions[exterior],'retained')
        self.assertNotIn('box_link_18',actions)
        self.assertNotIn('box_link_1307',actions)

    def test_payload_materials_are_embedded_and_separate_glass_metal_and_shell(self):
        robot=ET.parse(PKG/'urdf/scout_visual.urdf').getroot()
        self.assertIsNone(robot.find("link[@name='box_link']/visual/material"))
        root=ET.parse(PKG/'meshes/visual/payload.dae').getroot()
        colors={tuple(map(float,c.text.split())) for c in root.findall('.//c:diffuse/c:color',NS)}
        self.assertGreaterEqual(len(colors),4)
        self.assertIn((.065,.08,.105,1),colors)
        self.assertIn((.72,.73,.71,1),colors)

    def test_budget_scale_materials_and_surface_error(self):
        report=json.loads((PKG/'modeling/geometry_report.json').read_text())
        self.assertLess(report['vehicle_triangles'],50000)
        draw_calls=0
        for part in ('body','wheel','payload'):
            path=PKG/f'meshes/visual/{part}.dae';root=ET.parse(path).getroot()
            self.assertEqual(root.findtext('c:asset/c:up_axis',namespaces=NS),'Z_UP')
            self.assertEqual(float(root.find('c:asset/c:unit',NS).get('meter')),1)
            mesh=root.find('.//c:geometry/c:mesh',NS)
            sources={s.get('id'):list(map(float,s.find('c:float_array',NS).text.split())) for s in mesh.findall('c:source',NS)}
            positions=sources['positions'];vertices=list(zip(positions[::3],positions[1::3],positions[2::3]))
            self.assertLess(max(abs(v) for v in positions),.5)
            count=0
            for triangles in mesh.findall('c:triangles',NS):
                indices=list(map(int,triangles.find('c:p',NS).text.split()))
                self.assertEqual(len(indices),int(triangles.get('count'))*6)
                count+=int(triangles.get('count'))
                for i in range(0,len(indices),6):
                    a,b,c=(vertices[indices[i+j]] for j in (0,2,4))
                    u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
                    cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                    self.assertGreater(sum(x*x for x in cross),1e-24)
            self.assertEqual(count,report['parts'][part]['triangles'])
            self.assertLess(report['parts'][part]['retained_sampled_surface_deviation']['max_m'],.003)
            effects=root.findall('.//c:effect',NS)
            draw_calls+=len(effects)*(4 if part=='wheel' else 1)
            self.assertTrue(effects)
            self.assertEqual(root.findall('.//c:image',NS),[])
        self.assertEqual(report['vehicle_triangles'],report['parts']['body']['triangles']+4*report['parts']['wheel']['triangles']+report['parts']['payload']['triangles'])
        self.assertLess(draw_calls,25)

if __name__=='__main__':unittest.main()
