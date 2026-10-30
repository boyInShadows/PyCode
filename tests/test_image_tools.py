import contextlib
import importlib.util
import os
from pathlib import Path
import runpy
import tempfile
import unittest

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("square_splitter", ROOT / "SplitingImages/split_square_images.py")
splitter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(splitter)


class ImageToolTests(unittest.TestCase):
    def test_odd_width_keeps_every_column(self):
        with tempfile.TemporaryDirectory() as temporary, contextlib.chdir(temporary):
            folder = Path("splitingImages/images")
            folder.mkdir(parents=True)
            Image.new("RGB", (101, 80), "white").save(folder / "sucket.jpg")
            runpy.run_path(str(ROOT / "SplitingImages/split_image.py"))
            with Image.open(folder / "output/left_half.jpg") as left, Image.open(folder / "output/right_half.jpg") as right:
                self.assertEqual(left.size, (50, 80))
                self.assertEqual(right.size, (51, 80))

    def test_blue_square_passes_but_small_and_wide_regions_do_not(self):
        with tempfile.TemporaryDirectory() as temporary, contextlib.chdir(temporary):
            image = np.full((220, 400, 3), 255, dtype=np.uint8)
            cv2.rectangle(image, (20, 20), (100, 100), (255, 0, 0), 5)
            cv2.rectangle(image, (140, 20), (170, 50), (255, 0, 0), 5)
            cv2.rectangle(image, (200, 20), (360, 80), (255, 0, 0), 5)
            cv2.imwrite("fixture.png", image)
            splitter.detect_and_split_images("fixture.png")
            outputs = list(Path("splitingImages/images/output").glob("image_*.jpg"))
            self.assertEqual(len(outputs), 1)
            result = cv2.imread(str(outputs[0]))
            self.assertEqual(result.shape[:2], (97, 97))
            self.assertTrue(Path("splitingImages/images/output/detected_boxes.jpg").exists())

    def test_missing_image_returns_without_crops(self):
        with tempfile.TemporaryDirectory() as temporary, contextlib.chdir(temporary):
            self.assertIsNone(splitter.detect_and_split_images("missing.png"))
            self.assertEqual(list(Path("splitingImages/images/output").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
