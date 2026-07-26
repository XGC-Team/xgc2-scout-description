#!/usr/bin/env python3
"""Guard the Scout viewer model against drifting from the Gazebo model."""

from __future__ import annotations

import hashlib
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
COLLADA = {"c": "http://www.collada.org/2005/11/COLLADASchema"}
VISUAL_LINKS = (
    "base_link",
    "box_link",
    "front_left_wheel_link",
    "front_right_wheel_link",
    "rear_left_wheel_link",
    "rear_right_wheel_link",
)
JOINTS = (
    "box_joint",
    "front_left_wheel",
    "front_right_wheel",
    "rear_left_wheel",
    "rear_right_wheel",
)
VIEWER_VISUAL_ASSET_SHA256 = {
    "box_link.STL": "033cd0ce9f4661576e3ba42fdabb3fd2d630c472d6057ae421793090638b6ec3",
    "scout_mini_base_link.STL": "13a164aadf1b0a2c20327941fd31db091f30d16ca1b50aa74a41e3d35f8417a9",
    # Gazebo geometry and diffuse materials, with only white specular highlights disabled.
    "scout_mini_base_link2.dae": "3db98aba69d8ba26e1c2177646ba2a12c6725ff9dc99efe06cf4d2be87f23204",
    "wheel.dae": "c64ae34e44118f07d718d54199107ce430a006d1cd9fd96bb80968954b5a8ce7",
}


def element_by_name(root: ET.Element, tag: str, name: str) -> ET.Element:
    element = root.find(f"./{tag}[@name='{name}']")
    if element is None:
        raise AssertionError(f"missing {tag} {name}")
    return element


def attributes(element: ET.Element, path: str) -> dict[str, str]:
    child = element.find(path)
    if child is None:
        raise AssertionError(f"missing {path} below {element.tag} {element.attrib}")
    return child.attrib


class ScoutVisualAssetsTest(unittest.TestCase):
    def test_viewer_visuals_and_origins_match_gazebo_urdf(self) -> None:
        gazebo = ET.parse(PACKAGE / "urdf" / "scout_mini.urdf").getroot()
        viewer = ET.parse(PACKAGE / "urdf" / "scout_visual.urdf").getroot()

        for name in VISUAL_LINKS:
            expected = element_by_name(gazebo, "link", name)
            actual = element_by_name(viewer, "link", name)
            self.assertEqual(
                attributes(actual, "./visual/origin"),
                attributes(expected, "./visual/origin"),
                name,
            )
            self.assertEqual(
                attributes(actual, "./visual/geometry/mesh"),
                attributes(expected, "./visual/geometry/mesh"),
                name,
            )

        for name in JOINTS:
            expected = element_by_name(gazebo, "joint", name)
            actual = element_by_name(viewer, "joint", name)
            self.assertEqual(attributes(actual, "./origin"), attributes(expected, "./origin"), name)
            self.assertEqual(attributes(actual, "./parent"), attributes(expected, "./parent"), name)
            self.assertEqual(attributes(actual, "./child"), attributes(expected, "./child"), name)

        self.assertFalse(viewer.findall(".//visual/geometry/box"))
        self.assertFalse(viewer.findall(".//visual/geometry/cylinder"))

    def test_visual_assets_are_the_expected_full_detail_viewer_assets(self) -> None:
        for filename, expected_digest in VIEWER_VISUAL_ASSET_SHA256.items():
            path = PACKAGE / "meshes" / filename
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                expected_digest,
                filename,
            )

    def test_dae_keeps_all_gazebo_faces_materials_and_frame(self) -> None:
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
            path = PACKAGE / "meshes" / filename
            root = ET.parse(path).getroot()
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

    def test_dae_keeps_diffuse_colors_without_specular_reflections(self) -> None:
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
                self.assertEqual(
                    (effect.findtext(".//c:reflective/c:color", namespaces=COLLADA) or "").strip(),
                    "0.0 0.0 0.0 1.0",
                    filename,
                )
                self.assertEqual(
                    (effect.findtext(".//c:reflectivity/c:float", namespaces=COLLADA) or "").strip(),
                    "0.0",
                    filename,
                )


if __name__ == "__main__":
    unittest.main()
