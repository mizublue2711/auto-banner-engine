#!/usr/bin/env python3
"""Unit tests for engine/forge_3d_liquid_headline.py (DIR-AN-FORGE-3D-LIQUID-CHROME-RIPPLES-102-REV2)."""

import math
import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forge_3d_liquid_headline as mod


class TestForge3DLiquidHeadline(unittest.TestCase):
    def test_rev2_locked_parameters(self):
        self.assertEqual(mod.EXTRUDE_DEPTH, 48.0)
        self.assertEqual(mod.ROUND_R, 9.0)
        self.assertEqual(mod.SMIN_K, 16.0)
        self.assertEqual(mod.FBM_OCTAVES, 3)
        self.assertAlmostEqual(mod.FBM_GAIN, 0.32, places=5)
        self.assertAlmostEqual(mod.FBM_LACUNARITY, 1.85, places=5)
        self.assertAlmostEqual(mod.NORMAL_PERTURB_SCALE, 1.3, places=5)
        self.assertEqual(mod.SHADER_UNIFORMS["specular_power"], 80.0)
        self.assertAlmostEqual(mod.SHADER_UNIFORMS["clearcoat_roughness"], 0.03, places=5)
        self.assertEqual(mod.CAMERA_YAW_DEG, -8.0)
        self.assertEqual(mod.CAMERA_PITCH_DEG, 10.0)

    def test_smin_poly_properties(self):
        a = np.array([1.0, 10.0, 0.0, -2.0], dtype=np.float32)
        b = np.array([2.0, 10.0, 20.0, -2.0], dtype=np.float32)
        k = 16.0
        res = mod.smin_poly(a, b, k)
        self.assertTrue(np.all(res <= np.minimum(a, b) + 1e-6))
        self.assertAlmostEqual(float(res[2]), 0.0, places=5)
        self.assertAlmostEqual(float(res[1]), 10.0 - k * 0.25, places=5)

    def test_sd_extrude_round_signs_and_surface(self):
        d_front = mod.sd_extrude_round(np.array([-20.0]), np.array([24.0]), half_depth=24.0, r=9.0)
        self.assertAlmostEqual(float(d_front[0]), 0.0, places=5)
        d_in = mod.sd_extrude_round(np.array([-20.0]), np.array([0.0]), half_depth=24.0, r=9.0)
        self.assertLess(float(d_in[0]), 0.0)
        d_out = mod.sd_extrude_round(np.array([-20.0]), np.array([29.0]), half_depth=24.0, r=9.0)
        self.assertAlmostEqual(float(d_out[0]), 5.0, places=5)

    def test_chrome_ramp_band_centers(self):
        centers = np.array([0.15, 0.43, 0.65, 0.83, 0.96], dtype=np.float32)
        expected_hex = ["#121212", "#7A8288", "#FFFFFF", "#F26B1C", "#FFFFFF"]
        cols = mod.sample_chrome_ramp(centers, smooth_width=0.02, linear=False)
        for i, h in enumerate(expected_hex):
            exp = mod.hex_to_srgb(h)
            np.testing.assert_allclose(cols[i], exp, atol=1e-3)

    def test_specular_bar_peaks_on_axis(self):
        c = np.array([-0.612, 0.612, 0.50], dtype=np.float32)
        c /= np.linalg.norm(c)
        z_hat = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        a = np.cross(c, z_hat)
        a /= np.linalg.norm(a)
        m = np.cross(c, a)
        m /= np.linalg.norm(m)
        sigma = math.sqrt(2.0 / 80.0)

        # Peak on axis (R = c)
        val_peak = float(mod.eval_specular_bar(c[None, :], sigma=sigma)[0])
        self.assertGreater(val_peak, 0.98)

        # Off-axis by 3*sigma along perpendicular m -> near 0 (including REV3 outer tube sheen)
        r_off = c + 3.0 * sigma * m
        r_off /= np.linalg.norm(r_off)
        val_off = float(mod.eval_specular_bar(r_off[None, :], sigma=sigma)[0])
        self.assertLess(val_off, 0.05)

        # Back-facing (R = -c) -> 0
        val_back = float(mod.eval_specular_bar((-c)[None, :], sigma=sigma)[0])
        self.assertAlmostEqual(val_back, 0.0, places=5)

    def test_wrinkle_metric(self):
        yy, xx = np.indices((64, 64), dtype=np.float32)
        alpha = np.ones((64, 64), dtype=np.float32)
        # Smooth low-frequency field -> 0 wrinkle tiles
        smooth_field = 0.5 + 0.2 * np.sin(xx * 0.05) * np.cos(yy * 0.05)
        self.assertEqual(mod.measure_wrinkle_tiles(smooth_field, alpha), 0)

        # Add 4px-wavelength high-frequency wrinkle noise -> >0 wrinkle tiles
        wrinkled = smooth_field + 0.12 * np.sin(xx * (2.0 * math.pi / 4.0))
        self.assertGreater(mod.measure_wrinkle_tiles(wrinkled, alpha), 0)

    def test_fringe_metric(self):
        yy, xx = np.indices((64, 64), dtype=np.float32)
        dist = np.hypot(xx - 32.0, yy - 32.0)
        alpha = np.clip(20.0 - dist, 0.0, 1.0)
        rgba = np.zeros((64, 64, 4), dtype=np.float32)
        rgba[alpha > 0, :3] = 0.85
        rgba[..., 3] = alpha
        self.assertEqual(mod.measure_alpha_fringe_pixels(rgba), 0)

        # Inject dark halo on partial-alpha edge ring
        edge = (alpha > 0.1) & (alpha < 0.9)
        rgba[edge, :3] = 0.05
        self.assertGreater(mod.measure_alpha_fringe_pixels(rgba), 0)

    def test_environment_stage_colors(self):
        empty_rgba = np.zeros((mod.CANVAS_H, mod.CANVAS_W, 4), dtype=np.float32)
        stage_u8, glow_cy = mod.render_environment_stage(empty_rgba, baseline_row=234)
        self.assertEqual(stage_u8.shape, (400, 1200, 3))
        # Corner matches #0B0B0C (11, 11, 12) within +/- 2
        np.testing.assert_allclose(stage_u8[0, 0], [11, 11, 12], atol=2)
        # Center above floor glow matches #222226 (34, 34, 38) within +/- 6
        np.testing.assert_allclose(stage_u8[140, 600], [34, 34, 38], atol=6)
        # Floor glow centroid sits strictly below text baseline
        self.assertGreater(glow_cy, 234.0)

    def test_rev3_locked_parameters(self):
        self.assertAlmostEqual(mod.NORMAL_PERTURB_SCALE_FACE, 0.95, places=5)
        self.assertAlmostEqual(mod.NORMAL_PERTURB_SCALE_EDGE, 1.30, places=5)
        self.assertAlmostEqual(mod.KR_DIAG_DROPLET_OFFSET_X, 4.0, places=5)
        bar_light = next(l for l in mod.LIGHTS if l["type"] == "bar")
        self.assertGreaterEqual(bar_light["bar_half_length"], 0.85)

    def test_specular_bar_continuity(self):
        c = np.array([-0.612, 0.612, 0.50], dtype=np.float32)
        c /= np.linalg.norm(c)
        z_hat = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        a = np.cross(c, z_hat)
        a /= np.linalg.norm(a)
        # Elongated tube maintains strong reflection at |u| = 0.60 along axis (where REV2 dropped to 0)
        r_along = c * math.sqrt(1.0 - 0.60**2) + a * 0.60
        r_along /= np.linalg.norm(r_along)
        val = float(mod.eval_specular_bar(r_along[None, :])[0])
        self.assertGreater(val, 0.70)

    def test_kr_droplet_outward_separation(self):
        _, droplets, _ = mod.build_text_sdf_and_droplets(mod.FONT_PATHS["bold"], seed=102)
        for glyph, min_gap in [("K", 62.0), ("R", 58.0)]:
            xs = sorted(d.cx for d in droplets if d.glyph == glyph)
            self.assertEqual(len(xs), 2)
            self.assertGreaterEqual(xs[1] - xs[0], min_gap)

    def test_foot_detector_glyphs(self):
        mask_a = np.zeros((60, 80), dtype=bool)
        mask_a[40:51, 10:20] = True
        mask_a[40:51, 50:60] = True
        self.assertEqual(len(mod.detect_glyph_feet(mask_a, 0, 80, 50)), 2)

        mask_y = np.zeros((60, 80), dtype=bool)
        mask_y[35:51, 35:45] = True
        self.assertEqual(len(mod.detect_glyph_feet(mask_y, 0, 80, 50)), 1)

        _, droplets, _ = mod.build_text_sdf_and_droplets(mod.FONT_PATHS["bold"], seed=102)
        self.assertGreaterEqual(len(droplets), 8)
        for d in droplets:
            self.assertIn(d.glyph, mod.MELT_GLYPHS)


if __name__ == "__main__":
    unittest.main()
