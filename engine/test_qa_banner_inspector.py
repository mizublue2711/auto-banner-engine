#!/usr/bin/env python3
"""
Unit & CLI tests for engine/qa_banner_inspector.py (DIR-MASTER-BANNER-PREFLIGHT-022).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "engine"))

import apply_remediation_hints as patcher  # noqa: E402
import qa_banner_inspector as inspector  # noqa: E402


def _make_clean_master_png(path: Path, size: tuple[int, int] = (1080, 1080), bg=(15, 76, 129)) -> None:
    arr = np.full((size[1], size[0], 3), bg, dtype=np.uint8)
    Image.fromarray(arr, mode="RGB").save(path, format="PNG")


def _make_valid_manifest(overrides: dict | None = None) -> dict:
    manifest = {
        "banner_id": "gsshop_master_1080x1080",
        "dimensions": {"width": 1080, "height": 1080},
        "texts": {
            "logo": "MOBILE LIVE",
            "badge": "LIVE",
            "sub_copy": "단 60분! 할인쿠폰 + 추가혜택이 펑펑",
            "headline": "GS SHOP 라이브특가",
            "cta": "라이브 혜택 받고 쇼핑하기 >",
        },
        "elements": [
            {
                "id": "logo",
                "role": "logo",
                "text": "MOBILE LIVE",
                "bbox": {"x": 50, "y": 45, "width": 220, "height": 34},
            },
            {
                "id": "headline",
                "role": "headline",
                "text": "GS SHOP 라이브특가",
                "bbox": {"x": 140, "y": 180, "width": 800, "height": 96},
                "fg_hex": "#FFFFFF",
                "bg_hex": "#0F4C81",
            },
            {
                "id": "cta",
                "role": "cta",
                "text": "라이브 혜택 받고 쇼핑하기 >",
                "bbox": {"x": 240, "y": 910, "width": 600, "height": 84},
            },
            {
                "id": "ui_sub_copy",
                "role": "sub_copy",
                "text": "단 60분! 할인쿠폰 + 추가혜택이 펑펑",
                "bbox": {"x": 250, "y": 100, "width": 580, "height": 54},
            },
        ],
        "assets": [
            {"id": "decor_snowflake", "path": "assets/brands/gsshop/layers/10_decor_snowflake.png", "loaded": True, "natural_width": 512},
            {"id": "decor_candy_cane", "path": "assets/brands/gsshop/layers/10_decor_candy_cane.png", "loaded": True, "natural_width": 512},
            {"id": "decor_bauble", "path": "assets/brands/gsshop/layers/10_decor_bauble.png", "loaded": True, "natural_width": 512},
            {"id": "decor_box_front_rim", "path": "assets/brands/gsshop/layers/07_decor_box_front_rim.png", "loaded": True, "natural_width": 1024},
            {"id": "decor_box_lid_flying", "path": "assets/brands/gsshop/layers/09_decor_box_lid_flying.png", "loaded": True, "natural_width": 1024},
            {"id": "knit_sweater", "path": "assets/brands/gsshop/layers/08_hero_knit_sweater.png", "loaded": True, "natural_width": 935},
            {"id": "puffer_jacket", "path": "assets/brands/gsshop/layers/08_hero_puffer_jacket.png", "loaded": True, "natural_width": 1120},
            {"id": "tangerine_cluster", "path": "assets/brands/gsshop/layers/06_hero_tangerines_cluster.png", "loaded": True, "natural_width": 1024},
            {"id": "toilet_paper", "path": "assets/brands/gsshop/layers/06_hero_toilet_paper.png", "loaded": True, "natural_width": 1200},
        ],
        "fonts": [
            {"family": "Pretendard", "weight": "800", "status": "loaded"},
        ],
        "glyph_check": {"tofu_detected": False},
    }
    if overrides:
        manifest.update(overrides)
    return manifest


class TestMasterBannerPreflightInspector(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self._tmp.name)
        self.img_path = self.tmp_dir / "gsshop_master_1080x1080.png"
        self.meta_path = self.tmp_dir / "gsshop_master_1080x1080.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_manifest(self, data: dict) -> None:
        self.meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_valid_master_banner_passes(self) -> None:
        _make_clean_master_png(self.img_path)
        self._write_manifest(_make_valid_manifest())

        report = inspector.audit_master_banner(str(self.img_path), str(self.meta_path))
        self.assertEqual(report["status"], "PASS", msg=f"Unexpected issues: {report['issues']}")
        self.assertEqual(report["metrics"]["dimensions"], "1080x1080")
        self.assertGreaterEqual(report["metrics"]["headline_contrast_ratio"], 4.5)

    def test_dimension_mismatch_fails(self) -> None:
        _make_clean_master_png(self.img_path, size=(1080, 1079))
        self._write_manifest(_make_valid_manifest())

        report = inspector.audit_master_banner(str(self.img_path), str(self.meta_path))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("Dimension Mismatch" in i for i in report["issues"]))

    def test_oversized_file_fails(self) -> None:
        # Random high-entropy RGB noise PNG exceeds 2048 KB at 1080x1080
        rng = np.random.default_rng(42)
        arr = rng.integers(0, 256, size=(1080, 1080, 3), dtype=np.uint8)
        # Keep outer 40px calm so only file size triggers
        arr[:40, :] = (15, 76, 129)
        arr[-40:, :] = (15, 76, 129)
        arr[:, :40] = (15, 76, 129)
        arr[:, -40:] = (15, 76, 129)
        Image.fromarray(arr, mode="RGB").save(self.img_path, format="PNG", compress_level=0)
        self._write_manifest(_make_valid_manifest())

        report = inspector.audit_master_banner(str(self.img_path), str(self.meta_path))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("File size too large" in i for i in report["issues"]))

    def test_safe_zone_pixel_border_violation_fails(self) -> None:
        arr = np.full((1080, 1080, 3), (15, 76, 129), dtype=np.uint8)
        # High-contrast alternating black/white bars in top 40px border
        arr[:40, ::2] = (255, 255, 255)
        arr[:40, 1::2] = (0, 0, 0)
        Image.fromarray(arr, mode="RGB").save(self.img_path, format="PNG")
        self._write_manifest(_make_valid_manifest())

        report = inspector.audit_master_banner(str(self.img_path), str(self.meta_path))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("Top border" in i for i in report["issues"]))

    def test_safe_zone_bbox_intrusion_fails(self) -> None:
        _make_clean_master_png(self.img_path)
        manifest = _make_valid_manifest()
        # Intrude inside 54px left margin from config/media_safe_zones_2026.json
        manifest["elements"][0]["bbox"]["x"] = 20
        self._write_manifest(manifest)

        report = inspector.audit_master_banner(str(self.img_path), str(self.meta_path))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("Safe Zone Intrusion (logo)" in i for i in report["issues"]))

    def test_missing_manifest_fails_closed(self) -> None:
        _make_clean_master_png(self.img_path)

        report = inspector.audit_master_banner(str(self.img_path), str(self.meta_path))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("Missing Layout Manifest" in i for i in report["issues"]))

    def test_missing_required_copy_and_decor_fails(self) -> None:
        _make_clean_master_png(self.img_path)
        manifest = _make_valid_manifest()
        manifest["texts"]["cta"] = "쇼핑하기"
        manifest["elements"][2]["text"] = "쇼핑하기"
        manifest["assets"] = [a for a in manifest["assets"] if a["id"] != "decor_candy_cane"]
        self._write_manifest(manifest)

        report = inspector.audit_master_banner(str(self.img_path), str(self.meta_path))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("라이브 혜택 받고 쇼핑하기" in i and "decor_candy_cane" in i for i in report["issues"]))

    def test_low_wcag_contrast_fails(self) -> None:
        _make_clean_master_png(self.img_path, bg=(235, 240, 245))
        manifest = _make_valid_manifest()
        # White text on near-white snow background -> contrast ~ 1.1:1 < 4.5:1
        manifest["elements"][1]["fg_hex"] = "#FFFFFF"
        manifest["elements"][1].pop("bg_hex", None)
        self._write_manifest(manifest)

        report = inspector.audit_master_banner(str(self.img_path), str(self.meta_path))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("WCAG Contrast Failure" in i for i in report["issues"]))

    def test_broken_asset_and_tofu_glyph_fail(self) -> None:
        _make_clean_master_png(self.img_path)
        manifest = _make_valid_manifest()
        manifest["assets"][0]["loaded"] = False
        manifest["assets"][0]["natural_width"] = 0
        manifest["glyph_check"] = {"tofu_detected": True}
        self._write_manifest(manifest)

        report = inspector.audit_master_banner(str(self.img_path), str(self.meta_path))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("Broken Asset" in i for i in report["issues"]))
        self.assertTrue(any("Tofu" in i for i in report["issues"]))

    def test_cli_exit_codes(self) -> None:
        _make_clean_master_png(self.img_path)
        self._write_manifest(_make_valid_manifest())
        script = str(ROOT_DIR / "engine" / "qa_banner_inspector.py")

        pass_proc = subprocess.run(
            [sys.executable, script, str(self.img_path), str(self.meta_path), "--no-remediation-out"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(pass_proc.returncode, 0, msg=pass_proc.stdout + pass_proc.stderr)
        self.assertIn("PASS", pass_proc.stdout)

        # Now fail with missing manifest
        self.meta_path.unlink()
        fail_proc = subprocess.run(
            [sys.executable, script, str(self.img_path), str(self.meta_path), "--no-remediation-out"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(fail_proc.returncode, 1)
        self.assertIn("FAIL", fail_proc.stdout)

    def test_prescriptive_remediation_hints_and_html_patcher(self) -> None:
        _make_clean_master_png(self.img_path)
        sample_html = self.tmp_dir / "sample.html"
        sample_html.write_text(
            "<style>\n"
            "  .z13-logo-live-group {\n    top: 45px;\n    left: 50px;\n    width: 980px;\n  }\n"
            "  .mobile-live-logo-wrap {\n    width: 258px;\n    height: 34px;\n  }\n"
            "  .z8-knit-sweater {\n    top: 270px;\n    left: 188px;\n  }\n"
            "</style>\n"
            '<div class="layer z8-knit-sweater" data-layer-id="z8_knit_sweater"></div>\n',
            encoding="utf-8",
        )
        manifest = _make_valid_manifest(
            {
                "template": str(sample_html),
                "layers": [
                    {
                        "layer_id": "z13_logo_live_group",
                        "layer_name": "Z13_UI_LOCKUP",
                        "motion_role": "ui_header_lock",
                        "bbox": {"x": 50, "y": 45, "width": 980, "height": 73},
                    },
                    {
                        "layer_id": "z8_knit_sweater",
                        "layer_name": "Z8_BURST_HEROES",
                        "motion_role": "burst_hero_left",
                        "bbox": {"x": 188, "y": 220, "width": 400, "height": 400},
                    },
                ],
            }
        )
        # Trigger both logo top-left violation and headline occlusion
        manifest["elements"][0]["bbox"]["x"] = 360.0
        self._write_manifest(manifest)

        hints_out = self.tmp_dir / "remediation_hints.json"
        report = inspector.audit_master_banner(
            str(self.img_path),
            str(self.meta_path),
            remediation_out_path=str(hints_out),
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(hints_out.exists())
        hints_json = json.loads(hints_out.read_text(encoding="utf-8"))
        self.assertEqual(hints_json["total_hints"], 2)

        applied = patcher.apply_remediation_to_html(sample_html, hints_json)
        self.assertGreaterEqual(len(applied), 2)
        patched_css = sample_html.read_text(encoding="utf-8")
        self.assertIn("position: absolute;", patched_css)
        self.assertIn("left: 50px;", patched_css)
        # Headline bottom is 180 + 96 = 276; object top is 220 -> penetration 56 + 8 buffer = +64px -> 270 + 64 = 334px
        self.assertIn("top: 334px;", patched_css)


if __name__ == "__main__":
    unittest.main()