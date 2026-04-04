#!/usr/bin/env python3
"""
Generate bunny emoji images for BunnyScriber.

Creates simple, cute bunny illustrations in pastel pink style
for each emotional state used in the GUI.
"""

import os

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow is required: pip install Pillow")
    exit(1)

PICS_DIR = os.path.join(os.path.dirname(__file__), "pics")
os.makedirs(PICS_DIR, exist_ok=True)

SIZE = 200
BG = (255, 245, 245, 0)  # transparent
PINK = (249, 168, 212)
DARK_PINK = (236, 72, 153)
WHITE = (255, 255, 255)
BLACK = (60, 20, 40)
BLUSH = (253, 164, 175, 180)
LIGHT_PINK = (255, 228, 230)

STATES = {
    "basebun": {"eyes": "open", "mouth": "smile", "ears": "up"},
    "workbun": {"eyes": "focused", "mouth": "chomp", "ears": "up"},
    "winbun": {"eyes": "happy", "mouth": "big_smile", "ears": "up"},
    "chompbun": {"eyes": "open", "mouth": "chomp", "ears": "back"},
    "madbun": {"eyes": "angry", "mouth": "frown", "ears": "back"},
    "shockbun": {"eyes": "wide", "mouth": "open", "ears": "up"},
    "sleepbun": {"eyes": "closed", "mouth": "sleep", "ears": "down"},
    "listenbun": {"eyes": "open", "mouth": "smile", "ears": "perked"},
}


def draw_bunny(state_name, state):
    """Draw a bunny face for the given emotional state."""
    img = Image.new("RGBA", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)

    cx, cy = SIZE // 2, SIZE // 2 + 20

    # ── Ears ──
    ear_w, ear_h = 22, 55
    if state["ears"] == "up":
        # Left ear
        d.ellipse([cx - 40, cy - 90, cx - 40 + ear_w, cy - 90 + ear_h], fill=PINK, outline=DARK_PINK, width=2)
        d.ellipse([cx - 36, cy - 84, cx - 36 + ear_w - 8, cy - 84 + ear_h - 12], fill=LIGHT_PINK)
        # Right ear
        d.ellipse([cx + 18, cy - 90, cx + 18 + ear_w, cy - 90 + ear_h], fill=PINK, outline=DARK_PINK, width=2)
        d.ellipse([cx + 22, cy - 84, cx + 22 + ear_w - 8, cy - 84 + ear_h - 12], fill=LIGHT_PINK)
    elif state["ears"] == "back":
        d.ellipse([cx - 50, cy - 75, cx - 50 + ear_w + 5, cy - 75 + ear_h - 10], fill=PINK, outline=DARK_PINK, width=2)
        d.ellipse([cx + 25, cy - 75, cx + 25 + ear_w + 5, cy - 75 + ear_h - 10], fill=PINK, outline=DARK_PINK, width=2)
    elif state["ears"] == "down":
        d.ellipse([cx - 55, cy - 50, cx - 55 + ear_w, cy - 50 + ear_h - 5], fill=PINK, outline=DARK_PINK, width=2)
        d.ellipse([cx + 35, cy - 50, cx + 35 + ear_w, cy - 50 + ear_h - 5], fill=PINK, outline=DARK_PINK, width=2)
    elif state["ears"] == "perked":
        d.ellipse([cx - 45, cy - 95, cx - 45 + ear_w + 2, cy - 95 + ear_h + 5], fill=PINK, outline=DARK_PINK, width=2)
        d.ellipse([cx - 41, cy - 88, cx - 41 + ear_w - 6, cy - 88 + ear_h - 8], fill=LIGHT_PINK)
        d.ellipse([cx + 23, cy - 95, cx + 23 + ear_w + 2, cy - 95 + ear_h + 5], fill=PINK, outline=DARK_PINK, width=2)
        d.ellipse([cx + 27, cy - 88, cx + 27 + ear_w - 6, cy - 88 + ear_h - 8], fill=LIGHT_PINK)

    # ── Head ──
    head_r = 45
    d.ellipse(
        [cx - head_r, cy - head_r, cx + head_r, cy + head_r],
        fill=WHITE, outline=PINK, width=3,
    )

    # ── Blush cheeks ──
    d.ellipse([cx - 38, cy + 2, cx - 22, cy + 14], fill=BLUSH)
    d.ellipse([cx + 22, cy + 2, cx + 38, cy + 14], fill=BLUSH)

    # ── Eyes ──
    if state["eyes"] == "open":
        d.ellipse([cx - 16, cy - 12, cx - 8, cy - 2], fill=BLACK)
        d.ellipse([cx + 8, cy - 12, cx + 16, cy - 2], fill=BLACK)
        # Shine
        d.ellipse([cx - 13, cy - 10, cx - 11, cy - 8], fill=WHITE)
        d.ellipse([cx + 11, cy - 10, cx + 13, cy - 8], fill=WHITE)
    elif state["eyes"] == "happy":
        d.arc([cx - 18, cy - 16, cx - 6, cy - 4], 200, 340, fill=BLACK, width=2)
        d.arc([cx + 6, cy - 16, cx + 18, cy - 4], 200, 340, fill=BLACK, width=2)
    elif state["eyes"] == "closed":
        d.arc([cx - 18, cy - 12, cx - 6, cy], 0, 180, fill=BLACK, width=2)
        d.arc([cx + 6, cy - 12, cx + 18, cy], 0, 180, fill=BLACK, width=2)
    elif state["eyes"] == "focused":
        d.ellipse([cx - 14, cy - 10, cx - 8, cy - 4], fill=BLACK)
        d.ellipse([cx + 8, cy - 10, cx + 14, cy - 4], fill=BLACK)
    elif state["eyes"] == "angry":
        d.ellipse([cx - 15, cy - 10, cx - 7, cy - 2], fill=BLACK)
        d.ellipse([cx + 7, cy - 10, cx + 15, cy - 2], fill=BLACK)
        d.line([cx - 20, cy - 18, cx - 6, cy - 13], fill=BLACK, width=2)
        d.line([cx + 6, cy - 13, cx + 20, cy - 18], fill=BLACK, width=2)
    elif state["eyes"] == "wide":
        d.ellipse([cx - 18, cy - 15, cx - 6, cy], fill=BLACK)
        d.ellipse([cx + 6, cy - 15, cx + 18, cy], fill=BLACK)
        d.ellipse([cx - 14, cy - 12, cx - 10, cy - 8], fill=WHITE)
        d.ellipse([cx + 10, cy - 12, cx + 14, cy - 8], fill=WHITE)

    # ── Nose ──
    d.ellipse([cx - 4, cy + 4, cx + 4, cy + 10], fill=PINK)

    # ── Mouth ──
    if state["mouth"] == "smile":
        d.arc([cx - 10, cy + 6, cx + 10, cy + 22], 10, 170, fill=BLACK, width=2)
    elif state["mouth"] == "big_smile":
        d.arc([cx - 14, cy + 4, cx + 14, cy + 24], 10, 170, fill=BLACK, width=2)
    elif state["mouth"] == "chomp":
        d.ellipse([cx - 6, cy + 12, cx + 6, cy + 22], fill=BLACK)
    elif state["mouth"] == "frown":
        d.arc([cx - 10, cy + 14, cx + 10, cy + 28], 190, 350, fill=BLACK, width=2)
    elif state["mouth"] == "open":
        d.ellipse([cx - 8, cy + 10, cx + 8, cy + 24], fill=BLACK)
        d.ellipse([cx - 5, cy + 12, cx + 5, cy + 18], fill=DARK_PINK)
    elif state["mouth"] == "sleep":
        d.arc([cx - 8, cy + 8, cx + 8, cy + 18], 10, 170, fill=BLACK, width=1)

    # ── Whiskers ──
    d.line([cx - 40, cy + 4, cx - 20, cy + 8], fill=PINK, width=1)
    d.line([cx - 38, cy + 12, cx - 20, cy + 10], fill=PINK, width=1)
    d.line([cx + 20, cy + 8, cx + 40, cy + 4], fill=PINK, width=1)
    d.line([cx + 20, cy + 10, cx + 38, cy + 12], fill=PINK, width=1)

    # ── Save ──
    path = os.path.join(PICS_DIR, f"{state_name}.png")
    img.save(path, "PNG")
    print(f"  Created {state_name}.png")


if __name__ == "__main__":
    print("Generating bunny images...")
    for name, state in STATES.items():
        draw_bunny(name, state)
    print(f"Done! {len(STATES)} images saved to {PICS_DIR}/")
