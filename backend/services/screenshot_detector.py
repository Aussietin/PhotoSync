"""
Screenshot detection heuristics.

Primary signal: exact pixel dimensions matching a known iOS/iPadOS screen resolution.
Secondary signal: filename contains "screenshot" / "screen shot".
Tertiary signal: no camera EXIF (supports primary but is not sufficient alone).
"""

# Portrait (w, h) for every iPhone / iPad released through 2025
_PORTRAIT: set[tuple[int, int]] = {
    # iPhone SE gen 1/2/3, 6, 7, 8
    (750, 1334),
    # iPhone 6+, 7+, 8+  (rendered resolution)
    (1242, 2208),
    # iPhone X, XS, 11 Pro
    (1125, 2436),
    # iPhone XR, 11
    (828, 1792),
    # iPhone XS Max, 11 Pro Max
    (1242, 2688),
    # iPhone 12 mini, 13 mini
    (1080, 2340),
    # iPhone 12, 12 Pro, 13, 13 Pro, 14
    (1170, 2532),
    # iPhone 12 Pro Max, 13 Pro Max
    (1284, 2778),
    # iPhone 14 Pro, 15, 15 Pro
    (1179, 2556),
    # iPhone 14 Pro Max, 15 Plus, 15 Pro Max
    (1290, 2796),
    # iPhone 16, 16 Pro (same as 15 family)
    (1206, 2622),
    (1320, 2868),
    # iPad mini 6
    (1488, 2266),
    # iPad 9th/10th gen
    (1620, 2160),
    (1640, 2360),
    # iPad Air 4/5
    (1640, 2360),
    # iPad Pro 11"
    (1668, 2388),
    # iPad Pro 12.9"
    (2048, 2732),
    # iPad Pro 13" M4
    (2064, 2752),
}

# Include landscape orientations too
SCREEN_SIZES: set[tuple[int, int]] = _PORTRAIT | {(h, w) for w, h in _PORTRAIT}

_SCREENSHOT_KEYWORDS = ("screenshot", "screen shot", "screen_shot", "bildschirmfoto")


def detect_screenshot(
    width: int | None,
    height: int | None,
    camera_make: str | None,
    original_filename: str,
) -> bool:
    """Return True if the image is almost certainly a screenshot."""
    if width and height and (width, height) in SCREEN_SIZES:
        return True

    name_lower = original_filename.lower()
    if any(kw in name_lower for kw in _SCREENSHOT_KEYWORDS):
        return True

    return False
