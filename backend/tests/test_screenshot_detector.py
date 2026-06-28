"""Screenshot detection — pure logic, no heavy deps required."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.screenshot_detector import detect_screenshot


def test_iphone_screen_dimensions_flagged():
    # iPhone 13/14 portrait resolution
    assert detect_screenshot(1170, 2532, None, "IMG_0001.PNG") is True


def test_landscape_screen_dimensions_flagged():
    # Same size rotated
    assert detect_screenshot(2532, 1170, None, "IMG_0001.PNG") is True


def test_filename_keyword_flagged():
    assert detect_screenshot(4032, 3024, "Apple", "Screenshot 2024-01-01.png") is True
    assert detect_screenshot(800, 600, None, "screen shot at 10am.jpg") is True


def test_normal_camera_photo_not_flagged():
    # Typical iPhone camera capture size, no keyword
    assert detect_screenshot(4032, 3024, "Apple", "IMG_4242.HEIC") is False


def test_missing_dimensions_falls_back_to_name():
    assert detect_screenshot(None, None, None, "IMG_0001.HEIC") is False
    assert detect_screenshot(None, None, None, "Screenshot.png") is True
