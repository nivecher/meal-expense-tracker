#!/usr/bin/env python3
"""
Generate a simple default avatar image.
"""

import os
from typing import Union

from PIL import Image, ImageDraw, ImageFont


def generate_avatar() -> Image.Image:
    # Create a 200x200 image with a light gray background
    size = 200
    img = Image.new("RGBA", (size, size), (240, 240, 240, 255))
    draw = ImageDraw.Draw(img)

    # Draw a circle
    circle_margin = 10
    circle_bbox = [circle_margin, circle_margin, size - circle_margin, size - circle_margin]
    draw.ellipse(circle_bbox, fill=(200, 200, 200, 255), outline=(180, 180, 180, 255))

    # Draw a simple user icon
    try:
        # Try to use a font if available
        font: Union[ImageFont.FreeTypeFont, ImageFont.ImageFont] = ImageFont.truetype("DejaVuSans-Bold.ttf", 100)
    except OSError:
        # Fall back to default font
        font = ImageFont.load_default()

    # Draw a simple "U" for user
    text = "U"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    position = ((size - text_width) // 2, (size - text_height) // 2 - 10)
    draw.text(position, text, fill=(120, 120, 120, 255), font=font)

    return img


if __name__ == "__main__":
    # Create output directory if it doesn't exist
    output_dir = os.path.join("app", "static", "img")
    os.makedirs(output_dir, exist_ok=True)

    # Generate and save the avatar
    avatar = generate_avatar()
    output_path = os.path.join(output_dir, "default-avatar.png")
    avatar.save(output_path, "PNG")
    print(f"Generated default avatar at: {output_path}")
