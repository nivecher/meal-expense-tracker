import os

from PIL import Image, ImageDraw, ImageFont


def create_icon(size, text, output_path):
    # Create a new image with white background
    img = Image.new("RGB", (size, size), color="#4a90e2")
    d = ImageDraw.Draw(img)

    # Add text to the image
    try:
        # Try to load a font
        font_size = size // 4
        font = ImageFont.truetype("Arial", font_size)
    except IOError:
        # Fall back to default font if Arial is not available
        font = ImageFont.load_default()

    # Calculate text position (centered)
    # Using textbbox to get text dimensions (replaces deprecated textsize)
    bbox = d.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((size - text_width) // 2, (size - text_height) // 2)

    # Draw the text
    d.text(position, text, fill="white", font=font)

    # Save the image
    img.save(output_path, "PNG")
    print(f"Created icon: {output_path}")


# Create output directory if it doesn't exist
os.makedirs("app/static", exist_ok=True)

# Generate icons
create_icon(192, "192x192", "app/static/icon-192x192.png")
create_icon(512, "512x512", "app/static/icon-512x512.png")

print("Icons generated successfully!")
