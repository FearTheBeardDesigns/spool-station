"""CIEDE2000-approximation color distance for filament matching.

Uses a simplified Lab-based Euclidean distance that's perceptually reasonable
without requiring the colormath dependency.
"""

from __future__ import annotations

import math


def hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color string to (R, G, B) in 0-255 range."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    h = h[:6]
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _srgb_to_linear(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert sRGB to CIE Lab (D65 illuminant)."""
    # sRGB to linear
    rl = _srgb_to_linear(r)
    gl = _srgb_to_linear(g)
    bl = _srgb_to_linear(b)

    # Linear RGB to XYZ (D65)
    x = 0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl
    y = 0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl
    z = 0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl

    # Normalize to D65 white point
    x /= 0.95047
    y /= 1.00000
    z /= 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)

    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b_val = 200.0 * (fy - fz)

    return (L, a, b_val)


def delta_e_lab(
    lab1: tuple[float, float, float], lab2: tuple[float, float, float]
) -> float:
    """CIE76 delta-E (Euclidean distance in Lab space)."""
    return math.sqrt(
        (lab1[0] - lab2[0]) ** 2
        + (lab1[1] - lab2[1]) ** 2
        + (lab1[2] - lab2[2]) ** 2
    )


def color_distance(hex1: str, hex2: str) -> float:
    """Compute perceptual color distance between two hex colors.

    Returns delta-E (CIE76). Lower = more similar.
    Rough guide: <5 = excellent match, <15 = good, <30 = noticeable, >30 = different.
    """
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    lab1 = rgb_to_lab(r1, g1, b1)
    lab2 = rgb_to_lab(r2, g2, b2)
    return delta_e_lab(lab1, lab2)
