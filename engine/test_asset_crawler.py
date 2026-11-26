import unittest

from PIL import Image, ImageDraw

from engine.asset_crawler import _append_single_product_term, _packshot_rejection_reason


class AssetCrawlerPackshotTests(unittest.TestCase):
    def test_appends_single_product_term_once(self) -> None:
        self.assertEqual(_append_single_product_term("제주 감귤 박스"), "제주 감귤 박스 단품")
        self.assertEqual(_append_single_product_term("니트 단품 정면"), "니트 단품 정면")

    def test_accepts_centered_product_on_white_studio_background(self) -> None:
        image = Image.new("RGB", (200, 200), "white")
        ImageDraw.Draw(image).rectangle((50, 40, 150, 160), fill=(40, 70, 120))

        self.assertIsNone(_packshot_rejection_reason(image))

    def test_rejects_lifestyle_background_off_center_and_multiple_products(self) -> None:
        scene = Image.new("RGB", (200, 200), (90, 70, 50))
        ImageDraw.Draw(scene).rectangle((50, 40, 150, 160), fill=(40, 70, 120))
        off_center = Image.new("RGB", (200, 200), "white")
        ImageDraw.Draw(off_center).rectangle((20, 40, 100, 160), fill=(40, 70, 120))
        multiple_products = Image.new("RGB", (200, 200), "white")
        draw = ImageDraw.Draw(multiple_products)
        draw.rectangle((25, 45, 80, 155), fill=(40, 70, 120))
        draw.rectangle((120, 45, 175, 155), fill=(120, 50, 30))

        self.assertIsNotNone(_packshot_rejection_reason(scene))
        self.assertIsNotNone(_packshot_rejection_reason(off_center))
        self.assertIsNotNone(_packshot_rejection_reason(multiple_products))


if __name__ == "__main__":
    unittest.main()
