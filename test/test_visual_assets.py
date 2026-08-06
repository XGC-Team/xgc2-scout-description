#!/usr/bin/env python3
"""Enforce the Scout description package's visual-only contract."""

import hashlib
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
COLLADA = {"c": "http://www.collada.org/2005/11/COLLADASchema"}
VIEWER_VISUAL_ASSET_SHA256 = {
    "box_link.STL": "033cd0ce9f4661576e3ba42fdabb3fd2d630c472d6057ae421793090638b6ec3",
    "scout_mini_base_link.STL": "13a164aadf1b0a2c20327941fd31db091f30d16ca1b50aa74a41e3d35f8417a9",
    "scout_mini_base_link2.dae": "3db98aba69d8ba26e1c2177646ba2a12c6725ff9dc99efe06cf4d2be87f23204",
    "wheel.dae": "c64ae34e44118f07d718d54199107ce430a006d1cd9fd96bb80968954b5a8ce7",
}


class ScoutVisualAssetsTest(unittest.TestCase):
    def test_repository_boundary_is_visual_only(self) -> None:
        self.assertFalse((PACKAGE / "launch").exists())
        self.assertFalse((PACKAGE / "rviz").exists())
        self.assertEqual(
            [path.name for path in sorted((PACKAGE / "urdf").iterdir())],
            ["scout_visual.urdf"],
        )

    def test_visual_urdf_has_no_simulation_or_physics_elements(self) -> None:
        path = PACKAGE / "urdf" / "scout_visual.urdf"
        root = ET.parse(path).getroot()
        forbidden_tags = {
            "collision",
            "gazebo",
            "inertial",
            "plugin",
            "sensor",
            "transmission",
        }
        present = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
        self.assertTrue(forbidden_tags.isdisjoint(present), sorted(forbidden_tags & present))
        self.assertTrue(root.findall(".//visual"))
        self.assertTrue(root.findall(".//mesh"))

        for mesh in root.findall(".//mesh"):
            uri = mesh.attrib["filename"]
            prefix = "package://scout_description/meshes/"
            self.assertTrue(uri.startswith(prefix), uri)
            self.assertTrue((PACKAGE / "meshes" / uri[len(prefix) :]).is_file(), uri)

    def test_manifest_has_no_simulation_or_runtime_bringup_dependencies(self) -> None:
        text = (PACKAGE / "package.xml").read_text()
        for dependency in (
            "gazebo_ros",
            "lms1xx",
            "robot_state_publisher",
            "roslaunch",
            "rviz",
            "xacro",
        ):
            self.assertNotIn(f">{dependency}<", text)

    def test_visual_assets_are_the_expected_full_detail_assets(self) -> None:
        for filename, expected_digest in VIEWER_VISUAL_ASSET_SHA256.items():
            path = PACKAGE / "meshes" / filename
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected_digest, filename)

    def test_dae_keeps_all_faces_materials_and_frame(self) -> None:
        expectations = {
            "scout_mini_base_link2.dae": {
                "triangles": 193_648,
                "materials": 54,
                "required_diffuse": {
                    "0.0 0.0 0.0 1.0",
                    "1.0 1.0 1.0 1.0",
                    "1.0 0.05000000074505806 0.07000000029802322 1.0",
                    "1.0 0.699999988079071 0.18000000715255737 1.0",
                },
            },
            "wheel.dae": {
                "triangles": 38_882,
                "materials": 7,
                "required_diffuse": {
                    "1.0 0.05882352963089943 0.05882352963089943 1.0",
                    "0.8980392217636108 0.9176470637321472 0.929411768913269 1.0",
                    "0.29411765933036804 0.29411765933036804 0.29411765933036804 1.0",
                },
            },
        }
        for filename, expected in expectations.items():
            root = ET.parse(PACKAGE / "meshes" / filename).getroot()
            self.assertEqual(root.findtext("c:asset/c:up_axis", namespaces=COLLADA), "Z_UP")
            self.assertEqual(
                sum(int(element.attrib["count"]) for element in root.findall(".//c:triangles", COLLADA)),
                expected["triangles"],
            )
            self.assertEqual(
                len(root.findall(".//c:library_materials/c:material", COLLADA)),
                expected["materials"],
            )
            diffuse = {
                (element.text or "").strip()
                for element in root.findall(".//c:library_effects/c:effect//c:diffuse/c:color", COLLADA)
            }
            self.assertTrue(expected["required_diffuse"].issubset(diffuse), filename)

    def test_dae_has_no_specular_reflections(self) -> None:
        for filename, expected_effects in {
            "scout_mini_base_link2.dae": 54,
            "wheel.dae": 7,
        }.items():
            root = ET.parse(PACKAGE / "meshes" / filename).getroot()
            effects = root.findall(".//c:library_effects/c:effect", COLLADA)
            self.assertEqual(len(effects), expected_effects, filename)
            for effect in effects:
                self.assertEqual(
                    (effect.findtext(".//c:specular/c:color", namespaces=COLLADA) or "").strip(),
                    "0 0 0 1.0",
                    filename,
                )
                self.assertEqual(
                    (effect.findtext(".//c:shininess/c:float", namespaces=COLLADA) or "").strip(),
                    "0.0",
                    filename,
                )


if __name__ == "__main__":
    unittest.main()
